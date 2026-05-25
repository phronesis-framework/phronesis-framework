"""Tests for ``configure_obs`` and ``ObsConfig``."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from phronesis.obs import config as config_module
from phronesis.obs._detect import OBS_AVAILABLE
from phronesis.obs.config import ObsConfig, _state, configure_obs
from phronesis.obs.errors import ObsConfigError, ObsNotAvailableError


class _SpyExporter:
    """Minimal SpanExporter stand-in for tests."""

    def __init__(self) -> None:
        self.exported: list[Any] = []

    def export(self, spans: Any) -> Any:
        from opentelemetry.sdk.trace.export import SpanExportResult

        self.exported.extend(spans)

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class TestObsConfig:
    def test_defaults_are_sensible(self) -> None:
        cfg = ObsConfig()

        assert cfg.exporter == "console"
        assert cfg.endpoint is None
        assert cfg.sampling == 1.0
        assert cfg.service_name == "phronesis"
        assert cfg.exporter_instance is None

    def test_is_frozen(self) -> None:
        cfg = ObsConfig()

        with pytest.raises(FrozenInstanceError):
            cfg.exporter = "otlp"  # type: ignore[misc]


class TestConfigureObsWithoutExtra:
    def test_raises_when_obs_not_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(config_module, "OBS_AVAILABLE", False)

        with pytest.raises(ObsNotAvailableError, match="phronesis-framework\\[obs\\]"):
            configure_obs()


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestConfigureObsDefault:
    def test_returns_config_snapshot_with_defaults(self) -> None:
        cfg = configure_obs()

        assert isinstance(cfg, ObsConfig)
        assert cfg.exporter == "console"
        assert cfg.sampling == 1.0
        assert cfg.service_name == "phronesis"

    def test_marks_state_as_configured(self) -> None:
        configure_obs()

        assert _state.configured is True
        assert _state.config is not None
        assert _state.tracer_provider is not None

    def test_sets_global_tracer_provider(self) -> None:
        from opentelemetry import trace

        configure_obs()

        assert trace.get_tracer_provider() is _state.tracer_provider


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestConfigureObsCustom:
    def test_passes_service_name_to_resource(self) -> None:
        configure_obs(service_name="my-service")

        resource = _state.tracer_provider.resource

        assert resource.attributes["service.name"] == "my-service"

    def test_uses_exporter_instance_when_provided(self) -> None:
        spy = _SpyExporter()

        configure_obs(exporter_instance=spy)

        assert _state.config is not None
        assert _state.config.exporter_instance is spy

    def test_sampling_below_zero_uses_always_off(self) -> None:
        from opentelemetry.sdk.trace.sampling import ALWAYS_OFF

        configure_obs(sampling=0.0)

        assert _state.tracer_provider.sampler is ALWAYS_OFF

    def test_sampling_above_one_uses_always_on(self) -> None:
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON

        configure_obs(sampling=1.0)

        assert _state.tracer_provider.sampler is ALWAYS_ON

    def test_sampling_between_uses_ratio_based(self) -> None:
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

        configure_obs(sampling=0.5)

        assert isinstance(_state.tracer_provider.sampler, TraceIdRatioBased)


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestConfigureObsIdempotency:
    def test_second_call_replaces_provider(self) -> None:
        configure_obs()
        first_provider = _state.tracer_provider

        configure_obs()
        second_provider = _state.tracer_provider

        assert first_provider is not second_provider

    def test_second_call_overrides_config(self) -> None:
        configure_obs(service_name="first")
        configure_obs(service_name="second")

        assert _state.config is not None
        assert _state.config.service_name == "second"


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestMeterProviderWireUp:
    def test_meter_provider_is_set_globally(self) -> None:
        from opentelemetry import metrics as otel_metrics

        configure_obs()

        assert otel_metrics.get_meter_provider() is _state.meter_provider

    def test_metrics_registry_is_rebound_to_real_instruments(self) -> None:
        from phronesis.obs import metrics as metrics_module
        from phronesis.obs.metrics import _NOOP

        configure_obs()

        assert metrics_module.tool_invocations is not _NOOP
        assert metrics_module.tool_duration is not _NOOP

    def test_metric_reader_instance_captures_recorded_values(self) -> None:
        from opentelemetry.sdk.metrics.export import InMemoryMetricReader

        from phronesis.obs import metrics as metrics_module

        reader = InMemoryMetricReader()
        configure_obs(metric_reader_instance=reader)

        metrics_module.tool_invocations.add(1, attributes={"tool.id": "TID-X"})
        metrics_module.tool_duration.record(0.42, attributes={"tool.id": "TID-X"})

        data = reader.get_metrics_data()
        names = [
            metric.name
            for resource_metrics in data.resource_metrics
            for scope_metrics in resource_metrics.scope_metrics
            for metric in scope_metrics.metrics
        ]

        assert "phronesis.tool.invocations" in names
        assert "phronesis.tool.duration" in names

    def test_reset_state_restores_noop_registry(self) -> None:
        from phronesis.obs import metrics as metrics_module
        from phronesis.obs.config import _reset_state
        from phronesis.obs.metrics import _NOOP

        configure_obs()

        assert metrics_module.tool_invocations is not _NOOP

        _reset_state()

        assert metrics_module.tool_invocations is _NOOP


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestLoggingFilterInstallation:
    def test_configure_installs_logging_factory(self) -> None:
        import logging

        original = logging.getLogRecordFactory()
        configure_obs()

        assert logging.getLogRecordFactory() is not original

    def test_reset_state_uninstalls_logging_factory(self) -> None:
        import logging

        from phronesis.obs.config import _reset_state

        original = logging.getLogRecordFactory()
        configure_obs()
        _reset_state()

        assert logging.getLogRecordFactory() is original

    def test_structured_formatter_includes_trace_id_and_span_id(self) -> None:
        import json
        import logging

        from opentelemetry import trace

        from phronesis._internal.logging.formatters import StructuredFormatter

        configure_obs()

        tracer = trace.get_tracer("phronesis.test")
        with tracer.start_as_current_span("phronesis.test.span"):
            logger = logging.getLogger("phronesis.tools")
            record = logger.makeRecord(
                "phronesis.tools",
                logging.INFO,
                __file__,
                1,
                "tool executed",
                (),
                None,
            )

        formatter = StructuredFormatter()
        payload = json.loads(formatter.format(record))

        assert "trace_id" in payload
        assert "span_id" in payload
        assert len(payload["trace_id"]) == 32
        assert len(payload["span_id"]) == 16


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestExporterSelection:
    def test_console_exporter_is_used_by_default(self) -> None:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        configure_obs()

        processors = list(_state.tracer_provider._active_span_processor._span_processors)
        exporters = [getattr(p, "span_exporter", None) for p in processors]

        assert any(isinstance(e, ConsoleSpanExporter) for e in exporters)

    def test_otlp_exporter_is_used_when_selected(self) -> None:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        configure_obs(exporter="otlp", endpoint="http://localhost:4318/v1/traces")

        processors = list(_state.tracer_provider._active_span_processor._span_processors)
        exporters = [getattr(p, "span_exporter", None) for p in processors]

        assert any(isinstance(e, OTLPSpanExporter) for e in exporters)

    def test_otlp_metric_reader_is_used_when_selected(self) -> None:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        configure_obs(exporter="otlp", endpoint="http://localhost:4318")

        readers = list(_state.meter_provider._sdk_config.metric_readers)

        assert any(isinstance(r, PeriodicExportingMetricReader) for r in readers)
        assert any(isinstance(r._exporter, OTLPMetricExporter) for r in readers)

    def test_exporter_instance_overrides_exporter_string(self) -> None:
        spy = _SpyExporter()

        configure_obs(exporter="otlp", exporter_instance=spy)

        processors = list(_state.tracer_provider._active_span_processor._span_processors)
        exporters = [getattr(p, "span_exporter", None) for p in processors]

        assert spy in exporters


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestExporterValidation:
    def test_unknown_exporter_raises(self) -> None:
        with pytest.raises(ObsConfigError, match="Unknown exporter"):
            configure_obs(exporter="jaeger")

    def test_otlp_without_endpoint_raises(self) -> None:
        with pytest.raises(ObsConfigError, match="requires a non-empty endpoint"):
            configure_obs(exporter="otlp")

    def test_otlp_with_empty_endpoint_raises(self) -> None:
        with pytest.raises(ObsConfigError, match="requires a non-empty endpoint"):
            configure_obs(exporter="otlp", endpoint="")

    def test_exporter_instance_bypasses_validation(self) -> None:
        spy = _SpyExporter()

        configure_obs(exporter="anything-goes", exporter_instance=spy)

        assert _state.config is not None
        assert _state.config.exporter == "anything-goes"


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestSpyExporterIntegration:
    def test_spans_flow_through_exporter_instance(self) -> None:
        from opentelemetry import trace

        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        tracer = trace.get_tracer("phronesis.test")
        with tracer.start_as_current_span("phronesis.test.span"):
            pass

        assert len(spy.exported) == 1
        assert spy.exported[0].name == "phronesis.test.span"
