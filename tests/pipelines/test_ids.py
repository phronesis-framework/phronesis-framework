"""Tests for :class:`PipelineId` and its generator."""

from __future__ import annotations

from phronesis.pipelines import PipelineId, pipeline_id_generator
from phronesis.pipelines.ids import _new_pipeline_id


class TestPipelineId:
    def test_prefix_is_pid(self) -> None:
        pid = pipeline_id_generator.from_canonical("phronesis.pipelines.pipeline.demo")

        assert pid.prefix == "PID"

    def test_short_form_starts_with_prefix(self) -> None:
        pid = pipeline_id_generator.from_canonical("phronesis.pipelines.pipeline.demo")

        assert pid.short.startswith("PID-")

    def test_canonical_is_stable_for_same_name(self) -> None:
        a = _new_pipeline_id("alpha")
        b = _new_pipeline_id("alpha")

        assert a.canonical == b.canonical
        assert a.short == b.short

    def test_canonical_differs_for_different_names(self) -> None:
        a = _new_pipeline_id("alpha")
        b = _new_pipeline_id("beta")

        assert a.canonical != b.canonical

    def test_canonical_follows_namespace_convention(self) -> None:
        pid = _new_pipeline_id("demo")

        assert pid.canonical == "phronesis.pipelines.pipeline.demo"

    def test_canonical_sanitizes_invalid_characters(self) -> None:
        pid = _new_pipeline_id("my-pipeline 01")

        assert pid.canonical == "phronesis.pipelines.pipeline.my_pipeline_01"

    def test_repr_includes_canonical(self) -> None:
        pid = _new_pipeline_id("demo")

        assert "demo" in repr(pid)
        assert isinstance(pid, PipelineId)
