"""Per-tool retry policy.

A :class:`RetryPolicy` describes how the agent loop should retry an
invocation of a single :class:`Tool` when it raises a retryable
exception. Policies are attached to the :class:`Tool` wrapper (not
the :class:`ToolSpec`, which is purely declarative) because retry is
an operational concern of the runtime.

The default policy attached to every tool is :data:`NO_RETRY` - a
single attempt with no backoff. Override it via the ``retry`` keyword
on the :func:`tool` decorator::

    from phronesis.tools.retry import RetryPolicy

    @tool(retry=RetryPolicy(max_attempts=3, backoff_seconds=0.5))
    def fetch(url: str) -> str:
        ...
"""

from __future__ import annotations

from dataclasses import dataclass

from phronesis.tools.errors import ToolError, ToolValidationError


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry configuration for a single tool.

    Attributes:
        max_attempts: Total number of attempts. ``1`` means "no
            retry"; values below 1 are clamped to 1 by
            :func:`__post_init__`.
        retry_on: Tuple of exception classes that trigger a retry.
            By default a retry is attempted on any :class:`ToolError`
            except :class:`ToolValidationError` (validation failures
            are deterministic and never benefit from a retry).
        backoff_seconds: Constant delay inserted between attempts.
            ``0.0`` means retry immediately.
    """

    max_attempts: int = 1
    retry_on: tuple[type[BaseException], ...] = (ToolError,)
    backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            object.__setattr__(self, "max_attempts", 1)

    def should_retry(self, exc: BaseException) -> bool:
        """Return ``True`` when ``exc`` matches the retryable set.

        :class:`ToolValidationError` is always excluded because the
        argument payload coming from the model is not going to change
        between attempts.
        """
        if isinstance(exc, ToolValidationError):
            return False

        return isinstance(exc, self.retry_on)


NO_RETRY: RetryPolicy = RetryPolicy(max_attempts=1)
"""Singleton policy meaning "one attempt, no retry"."""
