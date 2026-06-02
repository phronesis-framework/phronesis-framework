"""Tests for ``OpenAIProvider`` response_format wiring."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from phronesis._internal.retry import FixedBackoff
from phronesis.providers.openai.provider import OpenAIProvider
from phronesis.providers.retry_config import RetryConfig
from phronesis.providers.types import LLMRequest, ResponseFormat


def _ok_response() -> dict[str, Any]:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"},
        ],
    }


def _make_provider(captured: dict[str, Any]) -> OpenAIProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.read())
        return httpx.Response(200, json=_ok_response())

    transport = httpx.MockTransport(handler)

    return OpenAIProvider(
        model="gpt-4o",
        api_key="sk-test",
        http_client=httpx.AsyncClient(transport=transport, base_url="https://api.openai.com"),
        retry_config=RetryConfig(backoff=FixedBackoff(0)),
    )


class TestResponseFormatBody:
    @pytest.mark.asyncio
    async def test_omitted_when_request_has_none(self) -> None:
        captured: dict[str, Any] = {}
        provider = _make_provider(captured)

        await provider.complete(LLMRequest(model="gpt-4o", messages=()))

        assert "response_format" not in captured["body"]

    @pytest.mark.asyncio
    async def test_emits_json_schema_block(self) -> None:
        captured: dict[str, Any] = {}
        provider = _make_provider(captured)
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}

        await provider.complete(
            LLMRequest(
                model="gpt-4o",
                messages=(),
                response_format=ResponseFormat(schema=schema, name="answer"),
            ),
        )

        assert captured["body"]["response_format"] == {
            "type": "json_schema",
            "json_schema": {
                "name": "answer",
                "schema": schema,
                "strict": True,
            },
        }

    @pytest.mark.asyncio
    async def test_strict_propagates(self) -> None:
        captured: dict[str, Any] = {}
        provider = _make_provider(captured)

        await provider.complete(
            LLMRequest(
                model="gpt-4o",
                messages=(),
                response_format=ResponseFormat(schema={}, strict=False),
            ),
        )

        assert captured["body"]["response_format"]["json_schema"]["strict"] is False
