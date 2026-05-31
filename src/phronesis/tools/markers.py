"""``Annotated`` markers for parameter constraints.

These markers are recognised by pydantic v2 when placed inside
``Annotated[...]``. Numeric and length markers (:class:`Ge`,
:class:`Gt`, :class:`Le`, :class:`Lt`, :class:`MaxLen`, :class:`MinLen`)
come from the standard ``annotated_types`` library and are re-exported
here so tool authors can import them from a single place.
:func:`Pattern` is a thin helper around
:class:`pydantic.StringConstraints` for regex constraints.
"""

from __future__ import annotations

from annotated_types import Ge as Ge
from annotated_types import Gt as Gt
from annotated_types import Le as Le
from annotated_types import Lt as Lt
from annotated_types import MaxLen as MaxLen
from annotated_types import MinLen as MinLen
from pydantic import StringConstraints


def Pattern(pattern: str) -> StringConstraints:  # NOSONAR(S1542)
    """Build a regex constraint marker for ``Annotated[str, ...]``.

    PascalCase is intentional: the helper is meant to be used in type
    annotations alongside :class:`Ge`, :class:`Le`, etc., where a
    capitalised name reads naturally as a marker.

    Args:
        pattern: Regular expression that the annotated string must
            match. Forwarded verbatim to
            :class:`pydantic.StringConstraints`.

    Returns:
        A :class:`StringConstraints` instance carrying the pattern,
        suitable for use as ``Annotated[str, Pattern(r"...")]``.
    """
    return StringConstraints(pattern=pattern)
