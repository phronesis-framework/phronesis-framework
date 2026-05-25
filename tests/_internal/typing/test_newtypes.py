"""Tests for semantic NewType aliases.

NewTypes are zero-cost at runtime — the constructor is an identity
function. The type-checker uses them to prevent mixing of conceptually
different quantities; the runtime cannot enforce that, so these tests
only assert the constructor passes the value through unchanged.
"""

from phronesis._internal.typing import (
    ByteSize,
    CompletionTokens,
    Cost,
    Milliseconds,
    PromptTokens,
    Seconds,
    TokenCount,
)


class TestTimeNewTypes:
    def test_seconds_passes_value_through(self) -> None:
        assert Seconds(1.5) == 1.5

    def test_milliseconds_passes_value_through(self) -> None:
        assert Milliseconds(250) == 250


class TestTokenNewTypes:
    def test_token_count(self) -> None:
        assert TokenCount(100) == 100

    def test_prompt_tokens(self) -> None:
        assert PromptTokens(50) == 50

    def test_completion_tokens(self) -> None:
        assert CompletionTokens(75) == 75


class TestCostNewType:
    def test_cost(self) -> None:
        assert Cost(0.0123) == 0.0123


class TestSizeNewType:
    def test_byte_size(self) -> None:
        assert ByteSize(1024) == 1024
