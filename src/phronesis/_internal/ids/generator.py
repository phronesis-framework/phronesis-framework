"""Generators for definition-time identifiers.

A generator knows how to construct a specific Id subtype from
different sources (a Python function, an explicit canonical string, etc.).

The IdGenerator Protocol defines the contract; IdGenerator is the
generic implementation parameterized by the target Id type.
"""

from collections.abc import Callable
from typing import Generic, TypeVar

from phronesis._internal.ids.derivation import canonical_from_function
from phronesis._internal.ids.id import Id

IdT = TypeVar("IdT", bound="Id")


class IdGenerator(Generic[IdT]):
    """Generic generator for any Id subtype.

    Instances are typically used as singletons exported from each entity
    module (e.g. `tool_id_generator` from `phronesis.tools.id`).
    """

    def __init__(self, id_type: type[IdT]) -> None:
        self._id_type = id_type

    def from_function(self, fn: Callable[..., object]) -> IdT:
        return self._id_type(canonical_from_function(fn))

    def from_canonical(self, canonical: str) -> IdT:
        return self._id_type(canonical)
