"""Validators for identifier components.

Each validator groups related validation rules as static methods.
Validators raise on invalid input; they do not return booleans.
"""

import re


class CanonicalIdValidator:
    """Validates canonical identifiers used by definition-time entities.

    A canonical id is a lowercase, dot-separated string where each segment
    starts with a letter or underscore and may contain letters, digits and
    underscores. The leading-underscore allowance preserves Python's
    convention for private modules and functions (e.g. ``_internal``).

    Examples:
        Valid:   "search_web", "my_app.tools.web.search_web",
                 "phronesis._internal.ids._sample"
        Invalid: "Search_Web", "123_tool", "my.app.", "my-app"
    """

    _PATTERN = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")

    @staticmethod
    def validate(value: str) -> None:
        """Raise ValueError if `value` is not a valid canonical id."""

        if not value:
            raise ValueError("Canonical ID cannot be empty.")

        if not CanonicalIdValidator._PATTERN.match(value):
            raise ValueError(
                f"Invalid canonical id: {value!r}. "
                "Must be lowercase, dot-separated, "
                "each segment starting with a letter or underscore."
            )
