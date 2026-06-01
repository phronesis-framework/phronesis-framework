"""Tool-calling loop that drives an agent run.

The loop is the heart of the agents module. Its responsibilities:

* Build the initial message history from ``spec.system_prompt`` and
  ``request.input``, or continue from a provided ``initial_history``
  when a :class:`Session` is driving the call.
* On each turn, translate the history into provider messages and ask
  ``spec.model`` for a completion.
* If the model emits no tool calls the loop returns a :class:`Result`.
* Otherwise it executes every requested tool call in parallel via
  :func:`asyncio.gather`. A :class:`ToolError` is serialised back to
  the model as a ``ToolResultBlock`` with ``is_error=True``; any other
  exception is wrapped in :class:`AgentExecutionError` and aborts the
  run.
* The number of iterations is capped by
  ``request.max_iterations`` (or ``spec.max_iterations``) so a
  misbehaving model cannot loop forever; exceeding the cap raises
  :class:`AgentMaxIterationsError`.

OpenTelemetry instrumentation is woven into the loop:

* The run is wrapped in a ``phronesis.agents.run`` span.
* Each iteration is wrapped in a ``phronesis.agents.step`` span.
* Each tool invocation is wrapped in a
  ``phronesis.agents.tool_call`` span.
* Metrics emitted on every run: ``agent_runs``,
  ``agent_run_duration`` and ``agent_tool_calls_per_run``.

When the ``obs`` extra is not installed, the spans and metrics become
no-ops with no performance cost beyond the wrapper calls.
"""

from __future__ import annotations

import asyncio
import difflib
import inspect
import logging
import time
import uuid
from collections.abc import AsyncIterator, Mapping
from typing import Any

from phronesis.agents.errors import (
    AgentBudgetExceededError,
    AgentError,
    AgentExecutionError,
    AgentMaxIterationsError,
    AgentTimeoutError,
)
from phronesis.agents.events import (
    AgentEvent,
    RunCompleted,
    RunFailed,
    RunStarted,
    TextDelta,
    ToolCallCompleted,
    ToolCallStarted,
)
from phronesis.agents.run import (
    Result,
    RunId,
    RunRequest,
    TokenUsage,
    run_id_generator,
)
from phronesis.agents.spec import AgentSpec
from phronesis.context.context import Context
from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    AssistantMessage,
    CompactionSummaryBlock,
    ContentBlock,
    Message,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from phronesis.obs import attributes as obs_attrs
from phronesis.obs import metrics as obs_metrics
from phronesis.obs.spans import start_span_async
from phronesis.providers.types import LLMRequest
from phronesis.providers.types import Message as ProviderMessage
from phronesis.providers.types import Role as ProviderRole
from phronesis.providers.types import ToolCall as ProviderToolCall
from phronesis.tools.errors import ToolError, ToolNotFoundError
from phronesis.tools.tool import Tool

_logger = logging.getLogger(__name__)


async def run_loop(
    spec: AgentSpec,
    request: RunRequest,
    *,
    initial_history: tuple[Message, ...] | None = None,
) -> Result:
    """Execute the tool-calling loop for ``spec`` against ``request``.

    When ``initial_history`` is provided, the loop appends a new
    :class:`UserMessage` for ``request.input`` to it instead of
    seeding a fresh ``system + user`` history. This is the entry
    point used by :class:`phronesis.agents.session.Session` to
    continue a conversation.

    The loop always emits the ``agent_runs`` counter, then records
    ``agent_run_duration`` and ``agent_tool_calls_per_run`` in a
    ``finally`` clause so metrics are still emitted when the run
    raises.

    Args:
        spec: The :class:`AgentSpec` to execute.
        request: The :class:`RunRequest` describing this call.
        initial_history: Optional pre-existing message history. When
            provided, used as the conversation baseline; the
            ``request.input`` is appended as a user turn.

    Returns:
        A :class:`Result` with ``success=True`` and the final messages
        when the model produces a tool-free completion.

    Raises:
        AgentMaxIterationsError: if the loop hits
            ``request.max_iterations or spec.max_iterations`` without
            terminating.
        AgentBudgetExceededError: if the run exceeds
            ``request.max_tokens`` or ``request.max_cost_usd``.
        AgentTimeoutError: if the run exceeds
            ``request.timeout_seconds``.
        AgentExecutionError: if a tool or provider call raises an
            exception that is not a :class:`ToolError`.
    """
    if request.timeout_seconds is None:
        return await _run_loop_inner(spec, request, initial_history=initial_history)

    try:
        return await asyncio.wait_for(
            _run_loop_inner(spec, request, initial_history=initial_history),
            timeout=request.timeout_seconds,
        )
    except TimeoutError as exc:
        raise AgentTimeoutError(
            (f"Agent {spec.id.canonical!r} timed out after {request.timeout_seconds}s."),
            details={
                "agent_id": spec.id.canonical,
                "limit": "timeout_seconds",
                "threshold": request.timeout_seconds,
            },
        ) from exc


async def _run_loop_inner(
    spec: AgentSpec,
    request: RunRequest,
    *,
    initial_history: tuple[Message, ...] | None,
) -> Result:
    run_id = _generate_run_id()
    tool_by_name: dict[str, Tool] = {t.spec.name: t for t in spec.tools}
    context = _build_context(spec, request, run_id)
    run_attrs = _run_attributes(spec, request, run_id)

    user_input: Message | None = UserMessage(content=(TextBlock(text=request.input),))

    if initial_history is not None:
        history: tuple[Message, ...] = initial_history
    elif spec.system_prompt:
        history = (SystemMessage(content=(TextBlock(text=spec.system_prompt),)),)
    else:
        history = ()

    aggregated_usage = TokenUsage()
    aggregated_tool_calls: list[ToolUseBlock] = []
    iterations = 0
    max_iterations = request.max_iterations or spec.max_iterations
    started = time.monotonic()
    obs_metrics.agent_runs.add(1, attributes=run_attrs)

    await _run_setup(spec.tools)

    try:
        async with start_span_async("phronesis.agents.run", attributes=run_attrs):
            while iterations < max_iterations:
                iterations += 1
                step_attrs = {**run_attrs, "agent.step": iterations}

                async with start_span_async("phronesis.agents.step", attributes=step_attrs):
                    messages = await _build_messages(spec, history, user_input, run_attrs)

                    if user_input is not None:
                        history = (*history, user_input)
                        user_input = None

                    response = await _complete(spec, messages)
                    aggregated_usage = _merge_usage(aggregated_usage, response.usage)
                    _check_budget(spec, request, aggregated_usage)

                    await _dispatch_hook(spec.hooks.on_iteration, iterations)

                    assistant_message, requested_calls = _assistant_message_from_response(response)
                    history = (*history, assistant_message)
                    aggregated_tool_calls.extend(requested_calls)

                    if not requested_calls:
                        result = Result(
                            run_id=run_id,
                            output=response.text,
                            tokens=aggregated_usage,
                            iterations=iterations,
                            tool_calls=tuple(aggregated_tool_calls),
                            messages=history,
                        )
                        await _dispatch_hook(spec.hooks.on_run_complete, result)

                        return result

                    result_blocks = await _execute_calls(
                        tool_by_name, requested_calls, context, run_attrs
                    )

                    for call, block in zip(requested_calls, result_blocks, strict=True):
                        await _dispatch_hook(spec.hooks.on_tool_call, call, block)

                    history = (*history, ToolMessage(content=tuple(result_blocks)))

            raise AgentMaxIterationsError(
                (
                    f"Agent {spec.id.canonical!r} hit max_iterations={max_iterations} "
                    "without finishing."
                ),
                details={
                    "agent_id": spec.id.canonical,
                    "max_iterations": max_iterations,
                },
            )
    finally:
        elapsed = time.monotonic() - started
        obs_metrics.agent_run_duration.record(elapsed, attributes=run_attrs)
        obs_metrics.agent_tool_calls_per_run.record(
            len(aggregated_tool_calls), attributes=run_attrs
        )
        await _run_teardown(spec.tools)


def _generate_run_id() -> RunId:
    return run_id_generator.from_canonical(f"phronesis.runtime.run.r{uuid.uuid4().hex[:12]}")


async def _build_messages(
    spec: AgentSpec,
    history: tuple[Message, ...],
    new_input: Message | None,
    run_attrs: dict[str, Any],
) -> list[Message]:
    build_input = BuildInput(
        system_prompt=spec.system_prompt,
        history=history,
        new_input=new_input,
        provider=spec.model,
    )
    build_attrs: dict[str, Any] = {
        **run_attrs,
        obs_attrs.CONTEXT_BUILDER: type(spec.context_builder).__name__,
        obs_attrs.CONTEXT_HISTORY_SIZE: len(history),
    }

    async with start_span_async("phronesis.context.build", attributes=build_attrs):
        messages = await spec.context_builder.build(build_input)

    return messages


async def _complete(spec: AgentSpec, messages: list[Message]) -> Any:
    request = LLMRequest(
        model=spec.name,
        messages=_translate_history(tuple(messages)),
        tools=tuple(t.spec for t in spec.tools),
        system=spec.system_prompt or None,
    )

    try:
        return await spec.model.complete(request)
    except ToolError:
        raise
    except Exception as exc:
        raise AgentExecutionError(
            f"Provider call failed for agent {spec.id.canonical!r}.",
            details={"agent_id": spec.id.canonical},
        ) from exc


def _assistant_message_from_response(response: Any) -> tuple[AssistantMessage, list[ToolUseBlock]]:
    blocks: list[ContentBlock] = []
    requested: list[ToolUseBlock] = []

    if response.text:
        blocks.append(TextBlock(text=response.text))

    for call in response.tool_calls:
        block = ToolUseBlock(
            tool_call_id=call.call_id,
            tool_name=call.tool_name,
            args=call.arguments,
        )
        blocks.append(block)
        requested.append(block)

    return AssistantMessage(content=tuple(blocks)), requested


async def _execute_calls(
    tool_by_name: Mapping[str, Tool],
    calls: list[ToolUseBlock],
    context: Context,
    run_attrs: dict[str, Any],
) -> list[ToolResultBlock]:
    tasks = [_invoke_tool(tool_by_name, call, context, run_attrs) for call in calls]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    blocks: list[ToolResultBlock] = []

    for call, outcome in zip(calls, outcomes, strict=True):
        if isinstance(outcome, ToolError):
            blocks.append(
                ToolResultBlock(
                    tool_call_id=call.tool_call_id,
                    output=outcome.to_dict(),
                    is_error=True,
                ),
            )
            continue

        if isinstance(outcome, BaseException):
            raise AgentExecutionError(
                f"Tool {call.tool_name!r} raised a non-tool exception.",
                details={"tool_name": call.tool_name},
            ) from outcome

        blocks.append(
            ToolResultBlock(
                tool_call_id=call.tool_call_id,
                output=outcome,
                is_error=False,
            ),
        )

    return blocks


async def _invoke_tool(
    tool_by_name: Mapping[str, Tool],
    call: ToolUseBlock,
    context: Context,
    run_attrs: dict[str, Any],
) -> Any:
    tool = tool_by_name.get(call.tool_name)

    if tool is None:
        raise _build_tool_not_found(call.tool_name, tool_by_name)

    call_attrs = {
        **run_attrs,
        obs_attrs.TOOL_ID: tool.spec.id.canonical,
        obs_attrs.TOOL_NAME: str(tool.spec.name),
        obs_attrs.TOOL_CALL_ID: call.tool_call_id,
    }

    async with start_span_async("phronesis.agents.tool_call", attributes=call_attrs):
        return await _invoke_with_retry(tool, call, context)


async def _invoke_with_retry(
    tool: Tool,
    call: ToolUseBlock,
    context: Context,
) -> Any:
    """Invoke ``tool`` honouring its :class:`RetryPolicy`.

    Retries up to ``tool.retry.max_attempts`` times when the raised
    exception matches the policy. Sleeps ``tool.retry.backoff_seconds``
    between attempts. The exception raised on the **final** failed
    attempt propagates unchanged.
    """
    policy = tool.retry
    attempt = 0

    while True:
        attempt += 1

        try:
            outcome = tool.invoke(dict(call.args), context=context)

            if inspect.isawaitable(outcome):
                return await outcome

            return outcome
        except Exception as exc:
            if attempt >= policy.max_attempts or not policy.should_retry(exc):
                raise

            if policy.backoff_seconds > 0:
                await asyncio.sleep(policy.backoff_seconds)


def _build_context(spec: AgentSpec, request: RunRequest, run_id: RunId) -> Context:
    return Context(
        run_id=run_id,
        agent_id=spec.id,
        session_id=request.session_id,
        metadata=request.metadata,
    )


def _run_attributes(spec: AgentSpec, request: RunRequest, run_id: RunId) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        obs_attrs.AGENT_ID: spec.id.canonical,
        obs_attrs.AGENT_NAME: spec.name,
        obs_attrs.RUN_ID: run_id.canonical,
    }

    if request.session_id is not None:
        attrs[obs_attrs.SESSION_ID] = request.session_id.canonical

    return attrs


def _translate_history(history: tuple[Message, ...]) -> tuple[ProviderMessage, ...]:
    translated: list[ProviderMessage] = []

    for message in history:
        translated.extend(_translate_one(message))

    return tuple(translated)


def _translate_one(message: Message) -> list[ProviderMessage]:
    cache_hint = _has_cache_hint(message.content)

    if isinstance(message, SystemMessage):
        return [
            ProviderMessage(
                role=ProviderRole.SYSTEM,
                content=_concat_text(message.content),
                cache=cache_hint,
            ),
        ]

    if isinstance(message, UserMessage):
        return [
            ProviderMessage(
                role=ProviderRole.USER,
                content=_concat_text(message.content),
                cache=cache_hint,
            ),
        ]

    if isinstance(message, AssistantMessage):
        tool_calls = tuple(
            ProviderToolCall(
                call_id=block.tool_call_id,
                tool_name=block.tool_name,
                arguments=dict(block.args),
            )
            for block in message.content
            if isinstance(block, ToolUseBlock)
        )

        return [
            ProviderMessage(
                role=ProviderRole.ASSISTANT,
                content=_concat_text(message.content),
                tool_calls=tool_calls,
                cache=cache_hint,
            ),
        ]

    # ToolMessage: one provider message per ToolResultBlock.
    return [
        ProviderMessage(
            role=ProviderRole.TOOL,
            content="",
            tool_call_id=block.tool_call_id,
            tool_output=block.output,
        )
        for block in message.content
        if isinstance(block, ToolResultBlock)
    ]


def _has_cache_hint(blocks: tuple[ContentBlock, ...]) -> bool:
    """Return ``True`` if any :class:`TextBlock` in ``blocks`` is cached."""
    return any(isinstance(block, TextBlock) and block.cache for block in blocks)


def _concat_text(blocks: tuple[ContentBlock, ...]) -> str:
    parts: list[str] = []

    for block in blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
            continue

        if isinstance(block, CompactionSummaryBlock):
            parts.append(block.text)

    return "".join(parts)


def _merge_usage(left: TokenUsage, right: TokenUsage | None) -> TokenUsage:
    if right is None:
        return left

    return TokenUsage(
        input_tokens=_add_optional(left.input_tokens, right.input_tokens),
        output_tokens=_add_optional(left.output_tokens, right.output_tokens),
        cache_read_tokens=_add_optional(left.cache_read_tokens, right.cache_read_tokens),
        cache_creation_tokens=_add_optional(
            left.cache_creation_tokens,
            right.cache_creation_tokens,
        ),
    )


def _add_optional(a: int | None, b: int | None) -> int | None:
    if a is None and b is None:
        return None

    return (a or 0) + (b or 0)


def _check_budget(
    spec: AgentSpec,
    request: RunRequest,
    usage: TokenUsage,
) -> None:
    if request.max_tokens is not None:
        total = (usage.input_tokens or 0) + (usage.output_tokens or 0)

        if total > request.max_tokens:
            raise AgentBudgetExceededError(
                (
                    f"Agent {spec.id.canonical!r} consumed {total} tokens, "
                    f"exceeding the cap of {request.max_tokens}."
                ),
                details={
                    "agent_id": spec.id.canonical,
                    "limit": "max_tokens",
                    "threshold": request.max_tokens,
                    "observed": total,
                },
            )

    # Cost enforcement is opt-in: callers wire a cost estimator into
    # their provider; this MVP check only fires when a cost lands on
    # ``usage`` via a future provider extension. Left as a placeholder
    # so the field on ``RunRequest`` is honoured the moment costs land.


async def run_loop_stream(
    spec: AgentSpec,
    request: RunRequest,
    *,
    initial_history: tuple[Message, ...] | None = None,
) -> AsyncIterator[AgentEvent]:
    """Yield an :class:`AgentEvent` stream for one execution of ``spec``.

    Equivalent to :func:`run_loop` but exposes the run as a sequence
    of events. Used by :meth:`phronesis.agents.Agent.stream`.

    Events are emitted in the order documented on
    :data:`phronesis.agents.events.AgentEvent`. A successful run ends
    with :class:`RunCompleted`; a run aborted by an :class:`AgentError`
    ends with :class:`RunFailed` and the iterator stops without
    re-raising.

    Args:
        spec: The :class:`AgentSpec` to execute.
        request: The :class:`RunRequest` describing this call.
        initial_history: Optional pre-existing message history,
            matching the semantics of :func:`run_loop`.

    Yields:
        :class:`AgentEvent` instances in arrival order.
    """
    run_id = _generate_run_id()
    yield RunStarted(run_id=run_id, agent_id=spec.id)

    tool_by_name: dict[str, Tool] = {t.spec.name: t for t in spec.tools}
    context = _build_context(spec, request, run_id)
    run_attrs = _run_attributes(spec, request, run_id)

    user_input: Message | None = UserMessage(content=(TextBlock(text=request.input),))

    if initial_history is not None:
        history: tuple[Message, ...] = initial_history
    elif spec.system_prompt:
        history = (SystemMessage(content=(TextBlock(text=spec.system_prompt),)),)
    else:
        history = ()

    aggregated_usage = TokenUsage()
    aggregated_tool_calls: list[ToolUseBlock] = []
    iterations = 0
    max_iterations = request.max_iterations or spec.max_iterations
    started = time.monotonic()
    obs_metrics.agent_runs.add(1, attributes=run_attrs)

    deadline = started + request.timeout_seconds if request.timeout_seconds is not None else None

    await _run_setup(spec.tools)

    try:
        async with start_span_async("phronesis.agents.run", attributes=run_attrs):
            while iterations < max_iterations:
                if deadline is not None and time.monotonic() > deadline:
                    yield RunFailed(
                        error=AgentTimeoutError(
                            (
                                f"Agent {spec.id.canonical!r} timed out after "
                                f"{request.timeout_seconds}s."
                            ),
                            details={
                                "agent_id": spec.id.canonical,
                                "limit": "timeout_seconds",
                                "threshold": request.timeout_seconds,
                            },
                        ),
                    )
                    return

                iterations += 1
                step_attrs = {**run_attrs, "agent.step": iterations}

                try:
                    async with start_span_async("phronesis.agents.step", attributes=step_attrs):
                        messages = await _build_messages(spec, history, user_input, run_attrs)

                        if user_input is not None:
                            history = (*history, user_input)
                            user_input = None

                        response = await _complete(spec, messages)
                        aggregated_usage = _merge_usage(aggregated_usage, response.usage)

                        try:
                            _check_budget(spec, request, aggregated_usage)
                        except AgentBudgetExceededError as exc:
                            yield RunFailed(error=exc)
                            return

                        await _dispatch_hook(spec.hooks.on_iteration, iterations)

                        if response.text:
                            yield TextDelta(text=response.text)

                        assistant_message, requested_calls = _assistant_message_from_response(
                            response
                        )
                        history = (*history, assistant_message)
                        aggregated_tool_calls.extend(requested_calls)

                        if not requested_calls:
                            result = Result(
                                run_id=run_id,
                                output=response.text,
                                tokens=aggregated_usage,
                                iterations=iterations,
                                tool_calls=tuple(aggregated_tool_calls),
                                messages=history,
                            )
                            await _dispatch_hook(spec.hooks.on_run_complete, result)
                            yield RunCompleted(result=result)

                            return

                        for call in requested_calls:
                            tool = tool_by_name.get(call.tool_name)
                            yield ToolCallStarted(
                                tool_call_id=call.tool_call_id,
                                tool_id=tool.spec.id if tool else _missing_tool_id(),
                                tool_name=call.tool_name,
                                args=dict(call.args),
                            )

                        result_blocks = await _execute_calls(
                            tool_by_name, requested_calls, context, run_attrs
                        )

                        for call, block in zip(requested_calls, result_blocks, strict=True):
                            await _dispatch_hook(spec.hooks.on_tool_call, call, block)
                            yield ToolCallCompleted(
                                tool_call_id=block.tool_call_id,
                                result=block.output,
                                is_error=block.is_error,
                            )

                        history = (*history, ToolMessage(content=tuple(result_blocks)))
                except AgentError as exc:
                    yield RunFailed(error=exc)
                    return

            yield RunFailed(
                error=AgentMaxIterationsError(
                    (
                        f"Agent {spec.id.canonical!r} hit max_iterations={max_iterations} "
                        "without finishing."
                    ),
                    details={
                        "agent_id": spec.id.canonical,
                        "max_iterations": max_iterations,
                    },
                ),
            )
    finally:
        elapsed = time.monotonic() - started
        obs_metrics.agent_run_duration.record(elapsed, attributes=run_attrs)
        obs_metrics.agent_tool_calls_per_run.record(
            len(aggregated_tool_calls), attributes=run_attrs
        )
        await _run_teardown(spec.tools)


def _missing_tool_id() -> Any:
    from phronesis.tools.tool_id import ToolId

    return ToolId("phronesis.tools.unknown")


def _build_tool_not_found(
    requested: str,
    available: Mapping[str, Tool],
) -> ToolNotFoundError:
    """Build a :class:`ToolNotFoundError` with a "did you mean" hint.

    The hint is computed from the set of bound tool names using
    :func:`difflib.get_close_matches`. When no candidate is close
    enough the message and ``details`` simply list every available
    tool so the model can pick from the legal set.
    """
    names = sorted(available)
    suggestions = difflib.get_close_matches(requested, names, n=3, cutoff=0.6)

    if suggestions:
        hint = "Did you mean: " + ", ".join(repr(s) for s in suggestions) + "?"
    elif names:
        hint = "Available tools: " + ", ".join(repr(n) for n in names) + "."
    else:
        hint = "This agent has no tools bound."

    message = f"Tool {requested!r} is not bound to this agent. {hint}"

    return ToolNotFoundError(
        message,
        details={
            "tool_name": requested,
            "suggestions": suggestions,
            "available": names,
        },
    )


async def _dispatch_hook(hook: Any, *args: Any) -> None:
    """Invoke ``hook`` swallowing exceptions.

    Hooks are observers; their failures must not abort a run. Any
    raised exception is logged at WARNING and discarded.
    """
    if hook is None:
        return

    try:
        outcome = hook(*args)

        if inspect.isawaitable(outcome):
            await outcome
    except Exception:
        _logger.warning("Agent hook raised; ignored.", exc_info=True)


async def _run_setup(tools: tuple[Tool, ...]) -> None:
    """Invoke every tool's ``setup`` callback in declaration order."""
    for tool in tools:
        callback = tool.lifecycle.setup

        if callback is None:
            continue

        outcome = callback()

        if inspect.isawaitable(outcome):
            await outcome


async def _run_teardown(tools: tuple[Tool, ...]) -> None:
    """Invoke every tool's ``teardown`` callback, swallowing exceptions.

    Teardown runs in a ``finally`` clause; raising would mask the
    run's outcome. Errors are logged at WARNING and discarded.
    """
    for tool in tools:
        callback = tool.lifecycle.teardown

        if callback is None:
            continue

        try:
            outcome = callback()

            if inspect.isawaitable(outcome):
                await outcome
        except Exception:
            _logger.warning(
                "Tool %s teardown raised; ignored.",
                tool.spec.id.canonical,
                exc_info=True,
            )
