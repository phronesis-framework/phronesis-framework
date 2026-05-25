"""Tests for ``RunId``."""

from __future__ import annotations

import pytest

from phronesis._internal.ids.id import Id
from phronesis.runtime.run_id import RunId, run_id_generator


class TestRunId:
    def test_prefix_is_rid(self) -> None:
        assert RunId.prefix == "RID"

    def test_is_subclass_of_id(self) -> None:
        assert issubclass(RunId, Id)

    def test_accepts_valid_canonical(self) -> None:
        rid = RunId("phronesis.runs.r_001")

        assert rid.canonical == "phronesis.runs.r_001"

    def test_short_has_rid_prefix(self) -> None:
        rid = RunId("phronesis.runs.r_001")

        assert rid.short.startswith("RID-")
        assert len(rid.short) == len("RID-") + 8

    @pytest.mark.parametrize("canonical", ["", "1.bad", "a..b", "X.y"])
    def test_rejects_invalid_canonical(self, canonical: str) -> None:
        with pytest.raises(ValueError):
            RunId(canonical)


class TestRunIdGenerator:
    def test_from_canonical_builds_run_id(self) -> None:
        rid = run_id_generator.from_canonical("phronesis.runs.r_001")

        assert isinstance(rid, RunId)
        assert rid.canonical == "phronesis.runs.r_001"

    def test_from_canonical_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            run_id_generator.from_canonical("1.bad")
