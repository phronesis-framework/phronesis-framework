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
import inspect
import time
import uuid
from collections.abc import Mapping
from typing import Any

from phronesis.agents.errors import (
    AgentExecutionError,
    AgentMaxIterationsError,
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
from phronesis.core.messages import (
    AssistantMessage,
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
        AgentExecutionError: if a tool or provider call raises an
            exception that is not a :class:`ToolError`.
    """
    run_id = _generate_run_id()
    tool_by_name: dict[str, Tool] = {t.spec.name: t for t in spec.tools}
    context = _build_context(spec, request, run_id)
    run_attrs = _run_attributes(spec, request, run_id)

    if initial_history is None:
        history = _initial_history(spec, request)
    else:
        history = (*initial_history, UserMessage(content=(TextBlock(text=request.input),)))

    aggregated_usage = TokenUsage()
    aggregated_tool_calls: list[ToolUseBlock] = []
    iterations = 0
    max_iterations = request.max_iterations or spec.max_iterations
    started = time.monotonic()
    obs_metrics.agent_runs.add(1, attributes=run_attrs)

    try:
        async with start_span_async("phronesis.agents.run", attributes=run_attrs):
            while iterations < max_iterations:
                iterations += 1
                step_attrs = {**run_attrs, "agent.step": iterations}

                async with start_span_async("phronesis.agents.step", attributes=step_attrs):
                    response = await _complete(spec, history)
                    aggregated_usage = _merge_usage(aggregated_usage, response.usage)

                    assistant_message, requested_calls = _assistant_message_from_response(response)
                    history = (*history, assistant_message)
                    aggregated_tool_calls.extend(requested_calls)

                    if not requested_calls:
                        return Result(
                            run_id=run_id,
                            output=response.text,
                            tokens=aggregated_usage,
                            iterations=iterations,
                            tool_calls=tuple(aggregated_tool_calls),
                            messages=history,
                        )

                    result_blocks = await _execute_calls(
                        tool_by_name, requested_calls, context, run_attrs
                    )
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


def _generate_run_id() -> RunId:
    return run_id_generator.from_canonical(f"phronesis.runtime.run.r{uuid.uuid4().hex[:12]}")


def _initial_history(spec: AgentSpec, request: RunRequest) -> tuple[Message, ...]:
    messages: list[Message] = []

    if spec.system_prompt:
        messages.append(SystemMessage(content=(TextBlock(text=spec.system_prompt),)))

    messages.append(UserMessage(content=(TextBlock(text=request.input),)))

    return tuple(messages)


async def _complete(spec: AgentSpec, history: tuple[Message, ...]) -> Any:
    request = LLMRequest(
        model=spec.name,
        messages=_translate_history(history),
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
        raise ToolNotFoundError(
            f"Tool {call.tool_name!r} is not bound to this agent.",
            details={"tool_name": call.tool_name},
        )

    call_attrs = {
        **run_attrs,
        obs_attrs.TOOL_ID: tool.spec.id.canonical,
        obs_attrs.TOOL_NAME: str(tool.spec.name),
        obs_attrs.TOOL_CALL_ID: call.tool_call_id,
    }

    async with start_span_async("phronesis.agents.tool_call", attributes=call_attrs):
        outcome = tool.invoke(dict(call.args), context=context)

        if inspect.isawaitable(outcome):
            return await outcome

        return outcome


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
    if isinstance(message, SystemMessage):
        return [
            ProviderMessage(role=ProviderRole.SYSTEM, content=_concat_text(message.content)),
        ]

    if isinstance(message, UserMessage):
        return [
            ProviderMessage(role=ProviderRole.USER, content=_concat_text(message.content)),
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


def _concat_text(blocks: tuple[ContentBlock, ...]) -> str:
    return "".join(b.text for b in blocks if isinstance(b, TextBlock))


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
