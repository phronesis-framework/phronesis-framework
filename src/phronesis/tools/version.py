"""Semantic versioning value type for tools.

:class:`ToolVersion` is the strict, comparable representation of a
tool's version. It accepts the ``MAJOR.MINOR.PATCH`` subset of SemVer
that the framework actually needs - no pre-release or build metadata.
Tools continue to declare their version as a plain string via
:attr:`ToolSpec.version`; validation happens at spec construction
time and lifts the string into a :class:`ToolVersion` on demand.

:func:`parse_version` is the only entry point that turns a string into
a :class:`ToolVersion`; it raises :class:`InvalidVersionError` for any
input that does not match the strict ``MAJOR.MINOR.PATCH`` grammar.
"""

from __future__ import annotations

from dataclasses import dataclass

from phronesis.tools.errors import ToolDefinitionError


class InvalidVersionError(ToolDefinitionError):
    """A version string does not match ``MAJOR.MINOR.PATCH``.

    Raised by :func:`parse_version` and indirectly by
    :class:`ToolSpec` when a tool is declared with a malformed
    version. Carries the offending string under ``details['value']``.
    """

    code = "invalid_tool_version"


@dataclass(frozen=True, slots=True, order=True)
class ToolVersion:
    """Strict ``MAJOR.MINOR.PATCH`` version triple.

    Frozen and ordered so versions can be compared, sorted and used
    as dictionary keys. The string representation round-trips with
    :func:`parse_version`.

    Attributes:
        major: Non-negative major component.
        minor: Non-negative minor component.
        patch: Non-negative patch component.
    """

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise InvalidVersionError(
                "version components must be non-negative",
                details={
                    "major": self.major,
                    "minor": self.minor,
                    "patch": self.patch,
                },
            )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_version(value: str) -> ToolVersion:
    """Parse a ``MAJOR.MINOR.PATCH`` string into a :class:`ToolVersion`.

    Args:
        value: The version string to parse. Must be exactly three
            dot-separated non-negative integer components with no
            leading sign, whitespace, pre-release suffix or build
            metadata.

    Returns:
        The corresponding :class:`ToolVersion`.

    Raises:
        InvalidVersionError: If ``value`` is not a string or does not
            match the strict grammar.
    """
    if not isinstance(value, str):
        raise InvalidVersionError(
            "version must be a string",
            details={"value": value},
        )

    parts = value.split(".")

    if len(parts) != 3:
        raise InvalidVersionError(
            "version must have three dot-separated components",
            details={"value": value},
        )

    major, minor, patch = (_parse_component(p, value) for p in parts)

    return ToolVersion(major=major, minor=minor, patch=patch)


def _parse_component(component: str, original: str) -> int:
    if not component or not component.isdigit():
        raise InvalidVersionError(
            "version components must be non-negative integers",
            details={"value": original, "component": component},
        )

    return int(component)
