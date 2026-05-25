"""Smoke tests for the obs package skeleton."""

from __future__ import annotations

import importlib


class TestPackageImport:
    def test_package_is_importable(self) -> None:
        module = importlib.import_module("phronesis.obs")

        assert module is not None

    def test_package_exposes_non_empty_all(self) -> None:
        module = importlib.import_module("phronesis.obs")

        assert isinstance(module.__all__, list)
        assert len(module.__all__) > 0


class TestSubmodulesImport:
    def test_detect_is_importable(self) -> None:
        assert importlib.import_module("phronesis.obs._detect") is not None

    def test_noop_is_importable(self) -> None:
        assert importlib.import_module("phronesis.obs._noop") is not None

    def test_attributes_is_importable(self) -> None:
        assert importlib.import_module("phronesis.obs.attributes") is not None

    def test_config_is_importable(self) -> None:
        assert importlib.import_module("phronesis.obs.config") is not None

    def test_spans_is_importable(self) -> None:
        assert importlib.import_module("phronesis.obs.spans") is not None

    def test_metrics_is_importable(self) -> None:
        assert importlib.import_module("phronesis.obs.metrics") is not None

    def test_logging_filter_is_importable(self) -> None:
        assert importlib.import_module("phronesis.obs.logging_filter") is not None
