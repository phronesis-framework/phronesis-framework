"""Execution context injected into tools and agents.

Two distinct concerns share this package:

* :class:`Context` and :class:`Budget` - frozen records injected into
  tool callables by the runtime.
* :class:`ContextBuilder` and its reference implementations
  (:class:`DefaultContextBuilder`, :class:`CompactingContextBuilder`)
  - the agent-side abstraction that turns run state into the
  ``list[Message]`` sent to the provider.
"""

from phronesis.context.budget import Budget
from phronesis.context.chain import ChainedContextBuilder, chain
from phronesis.context.compacting import CompactingContextBuilder
from phronesis.context.context import Context
from phronesis.context.default import DefaultContextBuilder
from phronesis.context.dry_run import DryRunReport, dry_run
from phronesis.context.errors import (
    CompactionError,
    ContextBuilderError,
    ContextError,
)
from phronesis.context.input import BuildInput
from phronesis.context.protocol import ContextBuilder

__all__ = [
    "Budget",
    "BuildInput",
    "ChainedContextBuilder",
    "CompactingContextBuilder",
    "CompactionError",
    "Context",
    "ContextBuilder",
    "ContextBuilderError",
    "ContextError",
    "DefaultContextBuilder",
    "DryRunReport",
    "chain",
    "dry_run",
]
