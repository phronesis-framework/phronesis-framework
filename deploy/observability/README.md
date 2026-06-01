# Phronesis - Observability stack

Stack OTLP estandar para consumir lo que `phronesis.obs` emite: traces (Tempo), metricas (Prometheus) y logs (Loki), visualizados en Grafana con dashboards pre-construidos.

## Perfiles

### Dev (all-in-one)

Imagen unica `grafana/otel-lgtm` para iteracion local rapida. Sin persistencia.

```bash
cd deploy/observability
docker compose -f docker-compose.dev.yml up -d
```

Servicios expuestos:

- Grafana UI: http://localhost:3000 (sin auth)
- OTLP HTTP: http://localhost:4318
- OTLP gRPC: localhost:4317
- Prometheus: http://localhost:9090

### Prod (stack separado)

Containers separados con volumenes persistentes, healthchecks y networks aisladas.

```bash
cd deploy/observability
export GRAFANA_ADMIN_PASSWORD=<secret>
docker compose -f docker-compose.prod.yml up -d
```

Servicios:

- `otel-collector` - recibe OTLP HTTP/gRPC y multiplexa a backends
- `tempo` - traces (filesystem block storage)
- `loki` - logs (boltdb-shipper + filesystem)
- `prometheus` - metricas (OTLP write receiver activado)
- `grafana` - UI + datasources + dashboards auto-provisionados

## Configurar phronesis

```python
from phronesis.obs import configure_obs

configure_obs(
    exporter="otlp",
    endpoint="http://localhost:4318",
    service_name="my-app",
)
```

## Validar end-to-end

```bash
uv run python deploy/observability/scripts/obs_demo.py
```

Genera trafico sintetico (agent runs, tool invocations, provider requests) e imprime el `trace_id` raiz y la URL de Grafana.

## Dashboards

Siete dashboards pre-construidos en `grafana/dashboards/`:

- `phronesis-overview` - health agregado
- `phronesis-providers` - LLM perf/cost
- `phronesis-tools` - tool performance
- `phronesis-agents` - agent execution
- `phronesis-pipelines` - pipeline orchestration
- `phronesis-retries` - resilience
- `phronesis-traces-explorer` - navegacion Tempo

Detalle en `docs/obs/dashboards.md`.

## Documentacion

- `docs/obs/stack.md` - arquitectura, troubleshooting, retention
- `docs/obs/dashboards.md` - catalogo panel-a-panel
