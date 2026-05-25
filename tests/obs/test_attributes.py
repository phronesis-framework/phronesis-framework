"""Tests for the standard span attribute catalog."""

from __future__ import annotations

import re

from phronesis.obs import attributes

_DOT_SEPARATED = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def _collect_public_constants() -> dict[str, str]:
    return {
        name: getattr(attributes, name)
        for name in dir(attributes)
        if name.isupper() and isinstance(getattr(attributes, name), str)
    }


class TestCatalogValues:
    def test_identifiers_are_dot_separated(self) -> None:
        for value in (
            attributes.TOOL_ID,
            attributes.TOOL_TID,
            attributes.TOOL_NAME,
            attributes.AGENT_ID,
            attributes.AGENT_NAME,
            attributes.PIPELINE_ID,
            attributes.PIPELINE_NAME,
            attributes.RUN_ID,
            attributes.SESSION_ID,
            attributes.TOOL_CALL_ID,
            attributes.MESSAGE_ID,
        ):
            assert _DOT_SEPARATED.match(value), value

    def test_provider_attributes_are_correct(self) -> None:
        assert attributes.PROVIDER_NAME == "provider.name"
        assert attributes.PROVIDER_MODEL == "provider.model"

    def test_operation_attributes_are_correct(self) -> None:
        assert attributes.OPERATION_DURATION_MS == "operation.duration_ms"
        assert attributes.OPERATION_SUCCESS == "operation.success"
        assert attributes.ERROR_TYPE == "error.type"
        assert attributes.ERROR_MESSAGE == "error.message"

    def test_token_attributes_are_correct(self) -> None:
        assert attributes.TOKENS_INPUT == "tokens.input"
        assert attributes.TOKENS_OUTPUT == "tokens.output"
        assert attributes.TOKENS_TOTAL == "tokens.total"
        assert attributes.COST_USD == "cost.usd"

    def test_streaming_attributes_are_correct(self) -> None:
        assert attributes.STREAM_CHUNKS_COUNT == "stream.chunks_count"
        assert attributes.STREAM_FIRST_CHUNK_MS == "stream.first_chunk_ms"


class TestCatalogIntegrity:
    def test_all_constants_are_strings(self) -> None:
        constants = _collect_public_constants()

        assert len(constants) > 0
        for value in constants.values():
            assert isinstance(value, str)

    def test_all_values_follow_dot_separated_convention(self) -> None:
        for name, value in _collect_public_constants().items():
            assert _DOT_SEPARATED.match(value), f"{name}={value!r}"

    def test_no_value_collisions_between_constants(self) -> None:
        constants = _collect_public_constants()
        values = list(constants.values())

        assert len(values) == len(set(values))

    def test_catalog_covers_expected_sections(self) -> None:
        constants = _collect_public_constants()
        prefixes = {value.split(".", 1)[0] for value in constants.values()}

        assert prefixes == {
            "tool",
            "tool_call",
            "agent",
            "pipeline",
            "run",
            "session",
            "message",
            "provider",
            "operation",
            "error",
            "tokens",
            "cost",
            "stream",
        }
