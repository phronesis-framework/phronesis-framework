"""Verify the public API surface of :mod:`phronesis.obs`."""

from __future__ import annotations

import phronesis.obs as obs

_EXPECTED_PUBLIC = {
    "ObsConfig",
    "ObsConfigError",
    "ObsError",
    "ObsNotAvailableError",
    "attributes",
    "configure_obs",
    "metrics",
    "start_span",
    "start_span_async",
    "traced",
}


class TestPublicApiSurface:
    def test_all_lists_expected_symbols(self) -> None:
        assert set(obs.__all__) == _EXPECTED_PUBLIC

    def test_every_symbol_in_all_is_importable(self) -> None:
        for name in obs.__all__:
            assert hasattr(obs, name), name

    def test_no_duplicate_entries_in_all(self) -> None:
        assert len(obs.__all__) == len(set(obs.__all__))


class TestPublicApiBindings:
    def test_configure_obs_is_callable(self) -> None:
        assert callable(obs.configure_obs)

    def test_traced_is_callable(self) -> None:
        assert callable(obs.traced)

    def test_start_span_is_callable(self) -> None:
        assert callable(obs.start_span)

    def test_start_span_async_is_callable(self) -> None:
        assert callable(obs.start_span_async)

    def test_obs_config_is_class(self) -> None:
        assert isinstance(obs.ObsConfig, type)

    def test_error_classes_are_exception_subclasses(self) -> None:
        assert issubclass(obs.ObsError, Exception)
        assert issubclass(obs.ObsNotAvailableError, obs.ObsError)
        assert issubclass(obs.ObsConfigError, obs.ObsError)

    def test_attributes_module_is_exposed(self) -> None:
        from phronesis.obs import attributes as attributes_module

        assert obs.attributes is attributes_module

    def test_metrics_module_is_exposed(self) -> None:
        from phronesis.obs import metrics as metrics_module

        assert obs.metrics is metrics_module
