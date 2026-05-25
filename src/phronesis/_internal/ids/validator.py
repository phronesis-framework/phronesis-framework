"""Validators for identifier components."""

import re


class CanonicalIdValidator:
    """Validates canonical ids: lowercase, dot-separated, ``[a-z_][a-z0-9_]*`` segments.

    The leading-underscore allowance mirrors Python's convention for private
    modules and functions (e.g. ``_internal``). Raises on invalid input.
    """

    _PATTERN = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")

    @staticmethod
    def validate(value: str) -> None:
        """Raise :class:`ValueError` if ``value`` is not a valid canonical id."""
        if not value:
            raise ValueError("Canonical ID cannot be empty.")

        if not CanonicalIdValidator._PATTERN.match(value):
            raise ValueError(
                f"Invalid canonical id: {value!r}. "
                "Must be lowercase, dot-separated, "
                "each segment starting with a letter or underscore."
            )
