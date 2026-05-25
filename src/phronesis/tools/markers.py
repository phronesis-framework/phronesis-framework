"""``Annotated`` markers for parameter constraints.

See ``docs/TOOLS-DECISIONS.md`` (D-21): markers are recognized by Pydantic
v2 when placed inside ``Annotated[...]``. Numeric and length markers come
from the standard ``annotated_types`` library; :func:`Pattern` is a thin
helper around ``pydantic.StringConstraints`` for regex constraints.
"""

from __future__ import annotations

from annotated_types import Ge, Gt, Le, Lt, MaxLen, MinLen
from pydantic import StringConstraints


def Pattern(
    pattern: str,
) -> StringConstraints:  # NOSONAR: PascalCase intentional, used as Annotated marker
    """Match strings against a regular expression."""
    return StringConstraints(pattern=pattern)


__all__ = ["Ge", "Gt", "Le", "Lt", "MaxLen", "MinLen", "Pattern"]
