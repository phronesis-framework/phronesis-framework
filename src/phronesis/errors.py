"""Root exception type for the framework.

Cross-cutting framework errors inherit from :class:`PhronesisError`.
Module-specific hierarchies (e.g. ``AgentError``) attach here so a
single ``except PhronesisError`` catches anything raised by the
framework.
"""

from __future__ import annotations

from typing import Any


class PhronesisError(Exception):
    """Base class for every framework-raised error.

    Carries an optional ``details`` mapping so subclasses can attach
    structured context without inventing a new attribute each time.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            message: Human-readable description of the failure.
            details: Optional structured context. Copied defensively
                so caller-side mutations do not leak into the error.
        """
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details) if details else {}
