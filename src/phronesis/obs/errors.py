"""Error hierarchy for the observability subsystem.

All errors raised by the ``obs`` package derive from ``ObsError`` so
callers can install a single ``except`` block to handle observability
failures without catching unrelated exceptions.
"""

from __future__ import annotations


class ObsError(Exception):
    """Base class for all observability errors raised by Phronesis."""


class ObsNotAvailableError(ObsError):
    """Raised when an obs API is called but the ``obs`` extra is missing.

    The remediation is to reinstall the package with the ``obs`` extra:

        pip install phronesis-framework[obs]
    """


class ObsConfigError(ObsError):
    """Raised when ``configure_obs`` receives an invalid combination of arguments."""
