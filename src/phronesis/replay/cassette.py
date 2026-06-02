"""JSONL cassette format for recording and replaying provider responses.

A cassette is a newline-delimited JSON file where each line encodes a
single :class:`LLMResponse`. The recorder appends one entry per
provider call; the replayer reads entries in order.

The encoding is intentionally minimal: only fields that survive the
provider boundary are preserved (``text``, ``tool_calls``,
``finish_reason``, ``usage``). Streaming chunks are out of scope for
the MVP.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phronesis.providers.types import LLMResponse, ToolCall
from phronesis.providers.usage import TokenUsage
from phronesis.replay.errors import CassetteFormatError


def encode_response(response: LLMResponse) -> dict[str, Any]:
    """Convert ``response`` to a JSON-serialisable mapping."""
    return {
        "text": response.text,
        "tool_calls": [_encode_tool_call(c) for c in response.tool_calls],
        "finish_reason": response.finish_reason,
        "usage": _encode_usage(response.usage),
    }


def decode_response(payload: dict[str, Any]) -> LLMResponse:
    """Build an :class:`LLMResponse` from a previously encoded mapping.

    Raises:
        CassetteFormatError: when ``payload`` is missing required
            fields or is otherwise malformed.
    """
    try:
        return LLMResponse(
            text=payload.get("text", ""),
            tool_calls=tuple(_decode_tool_call(c) for c in payload.get("tool_calls", [])),
            finish_reason=payload.get("finish_reason", ""),
            usage=_decode_usage(payload.get("usage")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CassetteFormatError(
            f"Malformed cassette entry: {exc}.",
            details={"payload": payload},
        ) from exc


def write_cassette(path: Path, responses: list[LLMResponse]) -> None:
    """Write ``responses`` to ``path`` as JSONL, one per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(encode_response(r), ensure_ascii=False) for r in responses]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def append_cassette(path: Path, response: LLMResponse) -> None:
    """Append a single ``response`` to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(encode_response(response), ensure_ascii=False))
        fh.write("\n")


def read_cassette(path: Path) -> list[LLMResponse]:
    """Read every entry in ``path`` in order.

    Raises:
        CassetteFormatError: when ``path`` contains a line that is not
            valid JSON or a JSON value that is not a mapping.
    """
    if not path.exists():
        raise CassetteFormatError(
            f"Cassette file not found: {path!s}.",
            details={"path": str(path)},
        )

    responses: list[LLMResponse] = []

    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()

        if not stripped:
            continue

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise CassetteFormatError(
                f"Invalid JSON on line {line_no} of {path!s}: {exc.msg}.",
                details={"path": str(path), "line": line_no},
            ) from exc

        if not isinstance(payload, dict):
            raise CassetteFormatError(
                f"Cassette line {line_no} is not a JSON object.",
                details={"path": str(path), "line": line_no},
            )

        responses.append(decode_response(payload))

    return responses


def _encode_tool_call(call: ToolCall) -> dict[str, Any]:
    return {
        "call_id": call.call_id,
        "tool_name": call.tool_name,
        "arguments": dict(call.arguments),
    }


def _decode_tool_call(payload: dict[str, Any]) -> ToolCall:
    return ToolCall(
        call_id=payload["call_id"],
        tool_name=payload["tool_name"],
        arguments=dict(payload.get("arguments", {})),
    )


def _encode_usage(usage: TokenUsage | None) -> dict[str, Any] | None:
    if usage is None:
        return None

    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": usage.cache_read_tokens,
        "cache_creation_tokens": usage.cache_creation_tokens,
    }


def _decode_usage(payload: dict[str, Any] | None) -> TokenUsage | None:
    if payload is None:
        return None

    return TokenUsage(
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        cache_read_tokens=payload.get("cache_read_tokens"),
        cache_creation_tokens=payload.get("cache_creation_tokens"),
    )
