"""Inspect-only invocation of a :class:`ContextBuilder`.

The :func:`dry_run` helper feeds a synthetic :class:`BuildInput`
through a builder and returns the resulting message list plus a
small :class:`DryRunReport` summary. Because every builder in the
framework is stateless, ``dry_run`` carries no side effects.

The helper is primarily a debugging aid: it lets a developer answer
"what messages would my builder send right now?" without spinning up
an agent run or a real provider call.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from phronesis.context.input import BuildInput
from phronesis.context.protocol import ContextBuilder
from phronesis.core.messages import Message
from phronesis.providers.protocol import LLMProvider


@dataclass(frozen=True, slots=True)
class DryRunReport:
    """Summary of a single :func:`dry_run` invocation.

    Attributes:
        messages: The messages the builder produced, exactly as the
            agent loop would send them to the provider.
        message_count: ``len(messages)`` for convenient assertions in
            tests.
        token_estimate: ``provider.count_tokens(messages)`` - a rough
            estimate for budgeting decisions.
        window_size: ``provider.context_window_size()``.
        within_window: ``token_estimate <= window_size``.
    """

    messages: tuple[Message, ...]
    message_count: int
    token_estimate: int
    window_size: int
    within_window: bool


async def dry_run(
    builder: ContextBuilder,
    *,
    provider: LLMProvider,
    system_prompt: str = "",
    history: Sequence[Message] = (),
    new_input: Message | None = None,
) -> DryRunReport:
    """Invoke ``builder`` against a synthetic input and report.

    Args:
        builder: The :class:`ContextBuilder` under inspection.
        provider: The :class:`LLMProvider` used both for the
            ``BuildInput`` and to compute the token estimate.
        system_prompt: System instructions to seed the synthetic
            input. Defaults to ``""``.
        history: Optional prior history to inject. Materialised to a
            tuple before being passed to the builder.
        new_input: Optional pending user input. ``None`` mimics a
            mid-iteration state where the input has already been
            absorbed.

    Returns:
        A :class:`DryRunReport` capturing the produced messages and
        token/window measurements.
    """
    build_input = BuildInput(
        system_prompt=system_prompt,
        history=tuple(history),
        new_input=new_input,
        provider=provider,
    )
    messages = await builder.build(build_input)
    tokens = provider.count_tokens(messages)
    window = provider.context_window_size()

    return DryRunReport(
        messages=tuple(messages),
        message_count=len(messages),
        token_estimate=tokens,
        window_size=window,
        within_window=tokens <= window,
    )
