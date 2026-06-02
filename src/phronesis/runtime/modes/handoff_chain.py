"""Handoff chain: the active agent can yield control to another by name."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import HandoffLimitError
from phronesis.runtime.obs import RUNTIME_HANDOFF_FROM, RUNTIME_HANDOFF_TO, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


def default_handoff_extractor(output: Any) -> str | None:
    """Pull a handoff target out of a ``dict`` or attribute on ``output``."""
    if isinstance(output, Mapping):
        target = output.get("handoff_to")

        return str(target) if target is not None else None

    target = getattr(output, "handoff_to", None)

    return str(target) if target is not None else None


@dataclass(frozen=True, slots=True)
class HandoffChain:
    """Agents pass the turn via the ``handoff_to`` field on their output.

    The chain terminates when an agent's output does not contain a handoff
    target. Reaching ``max_handoffs`` raises :class:`HandoffLimitError`.

    Attributes:
        agents: Mapping of agent name to executable.
        initial: Name of the first agent to run.
        max_handoffs: Hard cap on handoff hops.
        handoff_extractor: Callable extracting the target name from an
            agent output. ``None`` signals termination.
    """

    agents: Mapping[str, Executable]
    initial: str
    max_handoffs: int = 5
    handoff_extractor: Callable[[Any], str | None] = field(default=default_handoff_extractor)

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("handoff_chain", run_id=ctx.run_id.canonical):
            children: list[RunOutcome] = []
            current_name = self.initial
            current_input: Any = input

            for _ in range(self.max_handoffs + 1):
                agent = self.agents.get(current_name)

                if agent is None:
                    return RunOutcome.fail(
                        error=KeyError(f"unknown agent {current_name!r}"),
                        children=tuple(children),
                    ).merge_children()

                outcome = await agent(
                    ctx.child(metadata={RUNTIME_HANDOFF_TO: current_name}),
                    current_input,
                )
                children.append(outcome)

                if not outcome.success:
                    return RunOutcome.fail(
                        error=outcome.error or Exception("agent failed"),
                        children=tuple(children),
                    ).merge_children()

                target = self.handoff_extractor(outcome.output)

                if target is None:
                    return RunOutcome.ok(
                        output=outcome.output,
                        children=tuple(children),
                    ).merge_children()

                ctx.logger.debug(
                    "runtime.handoff",
                    extra={
                        RUNTIME_HANDOFF_FROM: current_name,
                        RUNTIME_HANDOFF_TO: target,
                    },
                )

                current_input = outcome.output
                current_name = target

            return RunOutcome.fail(
                error=HandoffLimitError(
                    f"handoff chain exceeded max_handoffs={self.max_handoffs}",
                    details={"max_handoffs": self.max_handoffs},
                ),
                children=tuple(children),
            ).merge_children()
