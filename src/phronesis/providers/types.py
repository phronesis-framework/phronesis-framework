"""Request/response types exchanged with a provider.

Frozen, slotted dataclasses describing the wire-shaped values
exchanged between the framework and each provider adapter. These
types are framework-internal data plumbing; validation of user input
happens at the boundaries (factory functions, HTTP I/O), not on
every transformation, so the dataclasses stay cheap to construct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from phronesis.providers.usage import TokenUsage
from phronesis.tools import ToolSpec


class Role(StrEnum):
    """Conversational role of a message.

    Attributes:
        SYSTEM: A system-level instruction issued by the framework.
        USER: A turn produced by the human (or upstream caller).
        ASSISTANT: A turn produced by the LLM.
        TOOL: The result of executing a tool call.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A tool invocation requested by the assistant.

    Attributes:
        call_id: Provider-assigned identifier echoed back in the
            corresponding :class:`Message` of role
            :attr:`Role.TOOL`. Used to pair calls with results.
        tool_name: LLM-facing tool name to dispatch.
        arguments: Decoded JSON arguments produced by the model.
    """

    call_id: str
    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Message:
    """A single message in the conversation.

    Attributes:
        role: Conversational role.
        content: Free-form text content. Empty for assistant messages
            that contain only tool calls, and for tool messages whose
            payload lives in ``tool_output``.
        tool_calls: Tool invocations attached to an assistant message.
        tool_call_id: For ``Role.TOOL`` messages, the id of the
            originating tool call.
        tool_output: For ``Role.TOOL`` messages, the result the tool
            produced.
        cache: Prompt caching hint. When ``True``, providers that
            support prompt caching mark this message as the end of a
            cacheable prefix; others ignore it.
    """

    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    tool_output: Any = None
    cache: bool = False


@dataclass(frozen=True, slots=True)
class ResponseFormat:
    """Structured-output schema for a request.

    Passed via :attr:`LLMRequest.response_format` to instruct the
    provider to return a value matching ``schema``. Providers that
    advertise :attr:`ProviderFeature.STRUCTURED_OUTPUT` translate the
    object into their native shape; providers that do not advertise
    the capability ignore it.

    Attributes:
        schema: A JSON Schema describing the desired response shape.
        name: Optional name for the schema (e.g. OpenAI's
            ``json_schema.name``). Defaults to ``"response"``.
        strict: When ``True``, request strict schema adherence from
            providers that distinguish it (OpenAI). Defaults to
            ``True``.
    """

    schema: dict[str, Any]
    name: str = "response"
    strict: bool = True


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """A request to a provider's ``complete``/``stream`` operation.

    Attributes:
        model: Vendor-specific model identifier.
        messages: Ordered conversation history. The provider adapter
            translates this into the vendor's wire format.
        tools: Tool definitions the model may call. Empty when tool
            use is not desired for this request.
        system: Optional system prompt. Separate from ``messages``
            so the adapter can place it in the vendor's preferred
            slot.
        temperature: Sampling temperature, ``None`` to defer to the
            vendor default.
        max_tokens: Output token cap, ``None`` for the vendor default.
        response_format: Optional :class:`ResponseFormat` requesting
            structured output. Providers that do not advertise
            :attr:`ProviderFeature.STRUCTURED_OUTPUT` ignore it.
        metadata: Free-form mapping forwarded for telemetry or
            vendor-specific knobs. Mutable for ergonomics; provider
            adapters do not modify it.
    """

    model: str
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...] = ()
    system: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: ResponseFormat | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """A non-streaming response from a provider.

    Attributes:
        text: Final assistant text. Empty when the response is
            tool-calls-only.
        tool_calls: Tool invocations the model produced.
        finish_reason: Vendor-normalised reason the response ended
            (``"stop"``, ``"length"``, ``"tool_use"``, ...).
        usage: Token accounting for the request, or ``None`` when
            the provider did not report it.
    """

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = ""
    usage: TokenUsage | None = None
