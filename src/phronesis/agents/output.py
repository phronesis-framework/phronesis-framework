"""Structured-output support for the agent loop.

An agent that declares :attr:`AgentSpec.output_type` asks for two
things:

* the provider should be *constrained* to the type's JSON Schema, and
* the final answer should be *validated* against it before it reaches
  the caller.

Only the first is negotiable. Constraining happens over the wire and
is skipped for providers that do not advertise
:attr:`ProviderFeature.STRUCTURED_OUTPUT` (Anthropic today); validation
always runs, so ``Result.output`` is either an instance of the declared
type or the run failed with :class:`AgentOutputValidationError`.

Both the schema and the parsing go through :class:`pydantic.TypeAdapter`,
which covers ``BaseModel`` subclasses, dataclasses, ``TypedDict`` and
plain builtins with one code path.
"""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter, ValidationError

from phronesis.agents.errors import AgentOutputValidationError
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import ResponseFormat


def response_format_for(
    output_type: type | None,
    provider: LLMProvider,
) -> ResponseFormat | None:
    """Build the :class:`ResponseFormat` to send for ``output_type``.

    Args:
        output_type: The agent's declared output type, or ``None``.
        provider: The provider the request is bound for. Probed with
            :meth:`LLMProvider.supports`.

    Returns:
        A :class:`ResponseFormat` carrying the type's JSON Schema, or
        ``None`` when there is no declared type or the provider cannot
        honour one. ``strict`` is left off: pydantic emits schemas that
        vendors' strict modes reject (optional fields absent from
        ``required``), and the loop validates the answer itself anyway.
    """
    if output_type is None:
        return None

    if not provider.supports(ProviderFeature.STRUCTURED_OUTPUT):
        return None

    return ResponseFormat(
        schema=TypeAdapter(output_type).json_schema(),
        name=getattr(output_type, "__name__", "response"),
        strict=False,
    )


def coerce_output(output_type: type | None, text: str, *, agent_id: str) -> Any:
    """Parse ``text`` into ``output_type``, or return it unchanged.

    Args:
        output_type: The agent's declared output type. ``None`` and
            :class:`str` both mean "hand the text back untouched".
        text: The model's final answer.
        agent_id: Canonical agent id, used in the error payload.

    Returns:
        An instance of ``output_type``, or ``text`` when no type was
        declared.

    Raises:
        AgentOutputValidationError: if ``text`` does not parse into
            ``output_type``.
    """
    if output_type is None or output_type is str:
        return text

    try:
        return TypeAdapter(output_type).validate_json(text)
    except ValidationError as exc:
        raise AgentOutputValidationError(
            f"Agent {agent_id!r} returned output that does not match {output_type.__name__!r}.",
            details={
                "agent_id": agent_id,
                "output_type": output_type.__name__,
                "errors": exc.errors(include_url=False),
                "raw_output": text,
            },
        ) from exc
