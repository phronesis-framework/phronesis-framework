"""Tests for the obs error hierarchy."""

from __future__ import annotations

import pytest

from phronesis.obs.errors import ObsError, ObsNotAvailableError


class TestObsError:
    def test_is_subclass_of_exception(self) -> None:
        assert issubclass(ObsError, Exception)

    def test_can_be_raised_with_message(self) -> None:
        with pytest.raises(ObsError, match="boom"):
            raise ObsError("boom")


class TestObsNotAvailableError:
    def test_is_subclass_of_obs_error(self) -> None:
        assert issubclass(ObsNotAvailableError, ObsError)

    def test_can_be_caught_as_obs_error(self) -> None:
        with pytest.raises(ObsError):
            raise ObsNotAvailableError("extra missing")
