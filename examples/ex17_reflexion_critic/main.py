"""Self-correction loop using ``runtime.Reflexion``.

The actor drafts an answer. The critic accepts only when the answer
contains the word ``because``. Otherwise it returns feedback and the
actor retries.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, Reflexion, ValidationResult, agent_node

provider = build_provider()


@agent(
    model=provider,
    system_prompt="Answer the question. Always justify your answer with 'because'.",
)
def actor() -> str:
    """Draft an answer."""


def critic(candidate: str) -> ValidationResult:
    """Require the word ``because`` in the answer."""
    if "because" in str(candidate).lower():
        return ValidationResult(valid=True)

    return ValidationResult(valid=False, feedback="Missing justification. Use 'because'.")


async def main() -> None:
    """Run the actor/critic loop and print the final accepted answer."""
    reflexion = Reflexion(actor=agent_node(actor), critic=critic, max_iterations=3)

    ctx = ExecutionContext.new()
    outcome = await reflexion(ctx, "Why do leaves change colour in autumn?")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
