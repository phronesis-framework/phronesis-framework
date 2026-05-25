"""Tests for ``ToolEffect`` — closed vocabulary of tool side-effects."""

from __future__ import annotations

import json

import pytest

from phronesis.tools.effects import ToolEffect


class TestToolEffectVocabulary:
    def test_vocabulary_is_exactly_the_documented_set(self) -> None:
        members = {effect.value for effect in ToolEffect}

        assert members == {
            "network",
            "filesystem.read",
            "filesystem.write",
            "side-effect",
            "expensive",
            "long-running",
            "requires-confirmation",
        }

    def test_member_count_matches_documented_size(self) -> None:
        assert len(list(ToolEffect)) == 7

    def test_member_names_follow_python_convention(self) -> None:
        for effect in ToolEffect:
            assert effect.name.isupper()
            assert " " not in effect.name


class TestToolEffectValues:
    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (ToolEffect.NETWORK, "network"),
            (ToolEffect.FILESYSTEM_READ, "filesystem.read"),
            (ToolEffect.FILESYSTEM_WRITE, "filesystem.write"),
            (ToolEffect.SIDE_EFFECT, "side-effect"),
            (ToolEffect.EXPENSIVE, "expensive"),
            (ToolEffect.LONG_RUNNING, "long-running"),
            (ToolEffect.REQUIRES_CONFIRMATION, "requires-confirmation"),
        ],
    )
    def test_each_member_serializes_to_canonical_value(
        self, member: ToolEffect, value: str
    ) -> None:
        assert member.value == value

    def test_members_are_strings(self) -> None:
        for effect in ToolEffect:
            assert isinstance(effect, str)

    def test_string_equality_with_canonical_value(self) -> None:
        assert ToolEffect.NETWORK.value == "network"
        assert ToolEffect.FILESYSTEM_READ.value == "filesystem.read"


class TestToolEffectClosed:
    def test_unknown_string_is_not_a_valid_member(self) -> None:
        with pytest.raises(ValueError):
            ToolEffect("disk-format")

    def test_uppercase_value_is_not_accepted(self) -> None:
        with pytest.raises(ValueError):
            ToolEffect("NETWORK")

    def test_lookup_by_canonical_value_returns_member(self) -> None:
        assert ToolEffect("network") is ToolEffect.NETWORK
        assert ToolEffect("filesystem.read") is ToolEffect.FILESYSTEM_READ


class TestToolEffectSerialization:
    def test_json_dumps_emits_canonical_string(self) -> None:
        payload = {"effects": [ToolEffect.NETWORK, ToolEffect.FILESYSTEM_READ]}

        encoded = json.dumps(payload)

        assert json.loads(encoded) == {
            "effects": ["network", "filesystem.read"],
        }

    def test_round_trip_through_json(self) -> None:
        original = [ToolEffect.EXPENSIVE, ToolEffect.LONG_RUNNING]

        encoded = json.dumps([e.value for e in original])
        decoded = [ToolEffect(v) for v in json.loads(encoded)]

        assert decoded == original
