"""Generic factory for :class:`Id` subtypes."""

from collections.abc import Callable
from typing import Generic, TypeVar

from phronesis._internal.ids.derivation import canonical_from_function
from phronesis._internal.ids.id import Id

IdT = TypeVar("IdT", bound="Id")


class IdGenerator(Generic[IdT]):
    """Builds instances of a specific :class:`Id` subtype from various sources."""

    def __init__(self, id_type: type[IdT]) -> None:
        self._id_type = id_type

    def from_function(self, fn: Callable[..., object]) -> IdT:
        """Derive an id from a function's ``module.qualname``."""
        return self._id_type(canonical_from_function(fn))

    def from_canonical(self, canonical: str) -> IdT:
        """Build an id from an already-canonical string."""
        return self._id_type(canonical)
