"""Recursive package import helper that triggers ``@tool`` registrations.

Explicit imports remain the primary path. ``discover`` is an opt-in
convenience that walks a package tree, importing every submodule so its
``@tool`` decorations execute and register into the active registry.

Broken submodules emit a :class:`UserWarning` and are skipped; they do
not abort the walk. Missing or non-package targets raise the underlying
import error so the caller learns about the typo.
"""

from __future__ import annotations

import importlib
import pkgutil
import warnings


def discover(package: str) -> None:
    """Recursively import every submodule of ``package``.

    Importing a module evaluates its top-level ``@tool`` decorators,
    which is how registrations land in the active registry. Single-file
    modules are supported too: they are simply imported.

    Raises:
        ModuleNotFoundError: when ``package`` cannot be imported at all.
    """
    root = importlib.import_module(package)
    paths = getattr(root, "__path__", None)

    if paths is None:
        return

    for module_info in pkgutil.walk_packages(paths, prefix=f"{package}."):
        try:
            importlib.import_module(module_info.name)
        except Exception as exc:
            warnings.warn(
                f"discover: failed to import {module_info.name!r}: {exc!r}",
                stacklevel=2,
            )
