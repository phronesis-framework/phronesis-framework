"""Shared fixtures for the examples smoke tests.

Each example's ``main`` module reads ``CASSETTE_PATH`` *at import time*
when ``build_provider()`` is evaluated by the ``@agent`` decorator. The
fixtures below make sure the env var is in place before the import and
that any prior copy of the module is purged from ``sys.modules`` so the
decorator re-runs cleanly on every test.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = REPO_ROOT / "examples"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def load_example(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Return a loader that imports a fresh copy of an example's ``main`` module.

    The returned callable accepts the example directory name (e.g.
    ``"ex01_hello_agent"``), wires ``CASSETTE_PATH`` to the cassette
    that ships with that example, evicts any cached copy of the module
    and the example's ``__init__`` from ``sys.modules`` (including the
    shared provider helper, since it caches the provider object only
    via the decorator-bound agents), and finally imports the module.
    """
    imported: list[str] = []

    def _loader(example_dir: str) -> ModuleType:
        cassette = EXAMPLES_ROOT / example_dir / "cassette.jsonl"
        monkeypatch.setenv("CASSETTE_PATH", str(cassette))

        for name in list(sys.modules):
            if name.startswith("examples."):
                del sys.modules[name]
                imported.append(name)

        return importlib.import_module(f"examples.{example_dir}.main")

    yield _loader

    for name in imported:
        sys.modules.pop(name, None)
