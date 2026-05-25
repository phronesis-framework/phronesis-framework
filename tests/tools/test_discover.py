"""Tests for :func:`discover`."""

from __future__ import annotations

import importlib
import sys
import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest

from phronesis.tools.discover import discover


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def synthetic_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Create a synthetic package on disk and put it on ``sys.path``."""
    name = "phr_discover_synth"
    root = tmp_path / name

    _write(root / "__init__.py", "loaded = True\n")
    _write(root / "alpha.py", "value = 'alpha'\n")
    _write(root / "subpkg" / "__init__.py", "")
    _write(root / "subpkg" / "beta.py", "value = 'beta'\n")

    monkeypatch.syspath_prepend(str(tmp_path))

    yield name

    for mod in list(sys.modules):
        if mod == name or mod.startswith(f"{name}."):
            del sys.modules[mod]


@pytest.fixture()
def broken_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    name = "phr_discover_broken"
    root = tmp_path / name

    _write(root / "__init__.py", "")
    _write(root / "good.py", "ok = True\n")
    _write(root / "bad.py", "raise RuntimeError('boom on import')\n")

    monkeypatch.syspath_prepend(str(tmp_path))

    yield name

    for mod in list(sys.modules):
        if mod == name or mod.startswith(f"{name}."):
            del sys.modules[mod]


class TestDiscoverHappyPath:
    def test_imports_top_level_modules(self, synthetic_package: str) -> None:
        discover(synthetic_package)

        assert f"{synthetic_package}.alpha" in sys.modules

    def test_imports_subpackages_recursively(self, synthetic_package: str) -> None:
        discover(synthetic_package)

        assert f"{synthetic_package}.subpkg" in sys.modules
        assert f"{synthetic_package}.subpkg.beta" in sys.modules

    def test_root_package_is_imported(self, synthetic_package: str) -> None:
        discover(synthetic_package)

        module = importlib.import_module(synthetic_package)

        assert module.loaded is True


class TestDiscoverErrors:
    def test_missing_root_package_raises_module_not_found(self) -> None:
        with pytest.raises(ModuleNotFoundError):
            discover("phr_nonexistent_pkg_xyz")

    def test_broken_submodule_emits_warning(self, broken_package: str) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            discover(broken_package)

        messages = [str(w.message) for w in caught]

        assert any(f"{broken_package}.bad" in m for m in messages)

    def test_broken_submodule_does_not_abort_walk(self, broken_package: str) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            discover(broken_package)

        assert f"{broken_package}.good" in sys.modules


class TestDiscoverSingleFileModule:
    def test_single_file_module_is_no_op(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "phr_single_mod.py"
        path.write_text("value = 1\n", encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))

        try:
            discover("phr_single_mod")

            assert "phr_single_mod" in sys.modules
        finally:
            sys.modules.pop("phr_single_mod", None)
