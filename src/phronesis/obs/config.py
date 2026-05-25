"""Configuration entry point for the observability subsystem.

Provides ``configure_obs`` and the immutable ``ObsConfig`` snapshot
that drives tracer provider initialization.

The default configuration sends spans to ``ConsoleSpanExporter`` with
100% sampling and the ``phronesis`` service name, so installing the
``obs`` extra and calling ``configure_obs()`` produces useful output
without any further setup.

``configure_obs`` is idempotent: subsequent calls fully replace the
previous tracer provider rather than stacking processors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phronesis.obs._detect import OBS_AVAILABLE
from phronesis.obs.errors import ObsNotAvailableError

_NOT_AVAILABLE_MESSAGE = (
    "OpenTelemetry is not installed. Install with `pip install phronesis-framework[obs]`."
)


@dataclass(frozen=True, slots=True)
class ObsConfig:
    """Immutable snapshot of an active observability configuration."""

    exporter: str = "console"
    endpoint: str | None = None
    sampling: float = 1.0
    service_name: str = "phronesis"
    exporter_instance: Any = None
    metric_reader_instance: Any = None


@dataclass(slots=True)
class _State:
    configured: bool = False
    config: ObsConfig | None = None
    tracer_provider: Any = None
    meter_provider: Any = None


_state: _State = _State()


def configure_obs(
    *,
    exporter: str = "console",
    endpoint: str | None = None,
    sampling: float = 1.0,
    service_name: str = "phronesis",
    exporter_instance: Any = None,
    metric_reader_instance: Any = None,
) -> ObsConfig:
    """Initialize the global tracer provider.

    Raises:
        ObsNotAvailableError: if the ``obs`` extra is not installed.

    Idempotent: each call fully replaces any prior tracer provider.
    Returns the resulting :class:`ObsConfig` snapshot.
    """
    if not OBS_AVAILABLE:
        raise ObsNotAvailableError(_NOT_AVAILABLE_MESSAGE)

    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.trace.sampling import (
        ALWAYS_OFF,
        ALWAYS_ON,
        TraceIdRatioBased,
    )

    from phronesis.obs import metrics as metrics_module

    config = ObsConfig(
        exporter=exporter,
        endpoint=endpoint,
        sampling=sampling,
        service_name=service_name,
        exporter_instance=exporter_instance,
        metric_reader_instance=metric_reader_instance,
    )

    from opentelemetry.sdk.trace.sampling import Sampler

    sampler: Sampler
    if sampling >= 1.0:
        sampler = ALWAYS_ON
    elif sampling <= 0.0:
        sampler = ALWAYS_OFF
    else:
        sampler = TraceIdRatioBased(sampling)

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource, sampler=sampler)

    if exporter_instance is not None:
        span_exporter: Any = exporter_instance
    else:
        span_exporter = ConsoleSpanExporter()

    provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(provider)

    metric_readers = [metric_reader_instance] if metric_reader_instance is not None else []
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    otel_metrics.set_meter_provider(meter_provider)
    metrics_module._build_registry(meter_provider.get_meter("phronesis"))

    _state.configured = True
    _state.config = config
    _state.tracer_provider = provider
    _state.meter_provider = meter_provider

    return config


def _reset_state() -> None:
    """Reset internal state. Intended for test isolation only.

    Also resets the OpenTelemetry global tracer and meter provider
    latches so a subsequent ``configure_obs`` call can install fresh
    providers, and rebinds the metrics registry to its no-op fallbacks.
    """
    _state.configured = False
    _state.config = None
    _state.tracer_provider = None
    _state.meter_provider = None

    if not OBS_AVAILABLE:
        return

    from opentelemetry import trace
    from opentelemetry.metrics import _internal as metrics_internal
    from opentelemetry.util._once import Once

    from phronesis.obs import metrics as metrics_module

    trace._TRACER_PROVIDER_SET_ONCE = Once()
    trace._TRACER_PROVIDER = None

    metrics_internal._METER_PROVIDER_SET_ONCE = Once()
    metrics_internal._METER_PROVIDER = None

    metrics_module._reset_registry()
