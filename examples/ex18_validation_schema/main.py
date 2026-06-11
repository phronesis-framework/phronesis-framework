"""Schema enforcement using ``runtime.Validation``.

A JSON-emitting agent is wrapped with a validator that parses the output
and checks that ``score`` is an integer between 0 and 100. The agent is
retried until the validator accepts.
"""

from __future__ import annotations

import asyncio
import json

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, Validation, ValidationResult, agent_node

provider = build_provider()


@agent(
    model=provider,
    system_prompt='Reply with one JSON object: {"score": <int 0-100>, "label": "<word>"}.',
)
def scorer() -> str:
    """Emit a JSON score."""


def validate_json(candidate: str) -> ValidationResult:
    """Accept only well-formed JSON with an integer ``score`` in [0, 100]."""
    try:
        data = json.loads(str(candidate))
    except json.JSONDecodeError as exc:
        return ValidationResult(valid=False, feedback=f"Not JSON: {exc}")

    score = data.get("score")

    if not isinstance(score, int) or not 0 <= score <= 100:
        return ValidationResult(valid=False, feedback="score must be int in [0,100]")

    return ValidationResult(valid=True)


async def main() -> None:
    """Run validation and print the accepted JSON."""
    validation = Validation(
        node=agent_node(scorer),
        validator=validate_json,
        max_attempts=3,
    )

    ctx = ExecutionContext.new()
    outcome = await validation(ctx, "Rate the importance of unit tests.")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
