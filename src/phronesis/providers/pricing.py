"""Caller-supplied pricing used to turn token counts into USD.

The framework ships **no price table**. Vendor rates change, models
multiply, and a stale constant baked into a release is worse than no
number at all. Instead the caller declares the rates it is billed at
and the agent loop applies them, which is what makes
:attr:`phronesis.agents.RunRequest.max_cost_usd` enforceable and
:attr:`phronesis.agents.Result.cost_usd` populated.

Attach a :class:`Pricing` to an agent via
:attr:`phronesis.agents.AgentSpec.pricing`.
"""

from __future__ import annotations

from dataclasses import dataclass

from phronesis.providers.usage import TokenUsage


@dataclass(frozen=True, slots=True)
class Pricing:
    """Per-million-token rates in USD for one model.

    Every counter is priced independently and the results are summed.
    Vendors disagree on whether cached tokens are also counted in
    ``input_tokens``: Anthropic reports them separately, OpenAI folds
    cache reads into the prompt total. Set the rate of a counter to
    ``0.0`` when your vendor already bills it inside another one.

    Attributes:
        input: USD per million prompt tokens.
        output: USD per million generated tokens.
        cache_read: USD per million tokens served from a prompt cache.
        cache_write: USD per million tokens written to a prompt cache.
    """

    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0

    def estimate(self, usage: TokenUsage) -> float:
        """Return the estimated USD cost of ``usage``.

        Counters the provider left as ``None`` contribute nothing.

        Args:
            usage: Token counts to price.

        Returns:
            Cost in USD. ``0.0`` when every rate is zero or every
            counter is absent.
        """
        billed = (
            (usage.input_tokens or 0) * self.input
            + (usage.output_tokens or 0) * self.output
            + (usage.cache_read_tokens or 0) * self.cache_read
            + (usage.cache_creation_tokens or 0) * self.cache_write
        )

        return billed / 1_000_000
