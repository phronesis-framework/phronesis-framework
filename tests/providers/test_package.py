"""Smoke tests for the providers package scaffold."""

from __future__ import annotations

import importlib


class TestProvidersScaffold:
    def test_root_package_imports(self) -> None:
        module = importlib.import_module("phronesis.providers")

        assert module.__all__

    def test_common_subpackage_imports(self) -> None:
        module = importlib.import_module("phronesis.providers._common")

        assert module.__all__ == []

    def test_anthropic_subpackage_exposes_factory(self) -> None:
        module = importlib.import_module("phronesis.providers.anthropic")

        assert module.__all__ == ["anthropic"]
        assert callable(module.anthropic)

    def test_openai_subpackage_exposes_factory(self) -> None:
        module = importlib.import_module("phronesis.providers.openai")

        assert module.__all__ == ["ollama", "openai", "openwebui", "vllm"]
        assert callable(module.openai)
        assert callable(module.ollama)
        assert callable(module.vllm)
        assert callable(module.openwebui)
