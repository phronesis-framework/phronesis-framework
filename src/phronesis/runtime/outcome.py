"""Uniform result type returned by every :class:`Executable`.

Agents return :class:`phronesis.agents.Result`, callables return arbitrary
values, and modes return nested compositions of node outputs. To keep the
public contract narrow, the runtime normalises every result to a single
:class:`RunOutcome` dataclass.

Token and cost accounting flows through ``children``; :meth:`merge_children`
folds the per-child counters into the parent so callers only need to look
at the root outcome.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

from phronesis.providers.usage import TokenUsage

_EMPTY_METADATA: Final[Mapping[str, Any]] = MappingProxyType({})


def _add_optional(a: int | None, b: int | None) -> int | None:
    if a is None and b is None:
        return None

    return (a or 0) + (b or 0)


def _merge_tokens(left: TokenUsage, right: TokenUsage) -> TokenUsage:
    return TokenUsage(
        input_tokens=_add_optional(left.input_tokens, right.input_tokens),
        output_tokens=_add_optional(left.output_tokens, right.output_tokens),
        cache_read_tokens=_add_optional(left.cache_read_tokens, right.cache_read_tokens),
        cache_creation_tokens=_add_optional(
            left.cache_creation_tokens, right.cache_creation_tokens
        ),
    )


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """Normalised result of an :class:`Executable` invocation.

    Attributes:
        output: The value produced by the node. Free-form: a string, a
            structured object, a tuple of child outputs, ...
        success: ``True`` when the node terminated normally, ``False`` when
            it failed and the mode chose to surface the failure rather than
            raise.
        error: Exception that aborted the node when ``success`` is
            ``False``. ``None`` for successful runs.
        tokens: Aggregated :class:`TokenUsage` produced by this node and,
            after :meth:`merge_children`, by its descendants.
        cost_usd: Estimated cost when the caller plugged in pricing,
            otherwise ``None``.
        children: Outcomes of sub-nodes, in deterministic order. Modes like
            :class:`Parallel` and :class:`MapReduce` use this to expose
            their inner runs.
        metadata: Free-form read-only mapping for mode-specific context
            (route taken, iteration count, ...).
    """

    output: Any = None
    success: bool = True
    error: Exception | None = None
    tokens: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float | None = None
    children: tuple[RunOutcome, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def ok(
        cls,
        output: Any = None,
        *,
        tokens: TokenUsage | None = None,
        cost_usd: float | None = None,
        children: tuple[RunOutcome, ...] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> RunOutcome:
        """Build a successful outcome."""
        return cls(
            output=output,
            success=True,
            error=None,
            tokens=tokens or TokenUsage(),
            cost_usd=cost_usd,
            children=children,
            metadata=metadata if metadata is not None else _EMPTY_METADATA,
        )

    @classmethod
    def fail(
        cls,
        error: Exception,
        *,
        output: Any = None,
        tokens: TokenUsage | None = None,
        cost_usd: float | None = None,
        children: tuple[RunOutcome, ...] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> RunOutcome:
        """Build a failed outcome."""
        return cls(
            output=output,
            success=False,
            error=error,
            tokens=tokens or TokenUsage(),
            cost_usd=cost_usd,
            children=children,
            metadata=metadata if metadata is not None else _EMPTY_METADATA,
        )

    def merge_children(self) -> RunOutcome:
        """Return a copy with ``tokens`` and ``cost_usd`` folding ``children``.

        Useful at the root of a composition to expose total token usage
        without forcing callers to walk the tree.
        """
        if not self.children:
            return self

        merged_tokens = self.tokens
        merged_cost: float | None = self.cost_usd

        for child in self.children:
            merged_tokens = _merge_tokens(merged_tokens, child.tokens)

            if child.cost_usd is not None:
                merged_cost = (merged_cost or 0.0) + child.cost_usd

        return RunOutcome(
            output=self.output,
            success=self.success,
            error=self.error,
            tokens=merged_tokens,
            cost_usd=merged_cost,
            children=self.children,
            metadata=self.metadata,
        )
