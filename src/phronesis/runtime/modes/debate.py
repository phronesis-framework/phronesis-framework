"""Debate: participants exchange arguments over N rounds.

Each round invokes every participant with the running transcript. An
optional moderator runs once at the end to produce the final synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.obs import RUNTIME_ITERATION, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Debate:
    """Participants debate for ``rounds``; optional moderator synthesises.

    Attributes:
        participants: Tuple of participant executables. Each receives a
            dict ``{"topic": input, "transcript": [...]}``.
        rounds: Number of full passes over the participants.
        moderator: Optional executable run once at the end with the full
            transcript.
    """

    participants: tuple[Executable, ...]
    rounds: int = 3
    moderator: Executable | None = None

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("debate", run_id=ctx.run_id.canonical):
            transcript: list[Any] = []
            children: list[RunOutcome] = []

            for round_idx in range(1, self.rounds + 1):
                for idx, participant in enumerate(self.participants):
                    payload = {
                        "topic": input,
                        "transcript": tuple(transcript),
                        "round": round_idx,
                        "participant": idx,
                    }
                    outcome = await participant(
                        ctx.child(metadata={RUNTIME_ITERATION: round_idx}),
                        payload,
                    )
                    children.append(outcome)

                    if not outcome.success:
                        return RunOutcome.fail(
                            error=outcome.error or Exception("participant failed"),
                            children=tuple(children),
                        ).merge_children()

                    transcript.append({"participant": idx, "output": outcome.output})

            if self.moderator is None:
                return RunOutcome.ok(
                    output=tuple(transcript),
                    children=tuple(children),
                ).merge_children()

            final_payload = {"topic": input, "transcript": tuple(transcript)}
            mod_outcome = await self.moderator(ctx.child(), final_payload)
            children.append(mod_outcome)

            if not mod_outcome.success:
                return RunOutcome.fail(
                    error=mod_outcome.error or Exception("moderator failed"),
                    children=tuple(children),
                ).merge_children()

            return RunOutcome.ok(
                output=mod_outcome.output,
                children=tuple(children),
            ).merge_children()
