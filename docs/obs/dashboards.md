#

<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis - Dashboards catalog" width="60%" />
</div>

<div align="center">

# Phronesis Framework - Dashboards catalog

</div>

<div align="center">
  Catalogo panel-a-panel de los siete dashboards Grafana pre-construidos en <code>deploy/observability/grafana/dashboards/</code>.
</div>

<div align="center">
  <a href="../index.md">docs</a> ·
  <a href="./stack.md">stack</a> ·
  <a href="../../deploy/observability/grafana/dashboards/">source</a>
</div>

---

<div align="center">

## 🎯 Purpose

</div>

Los dashboards consumen exclusivamente el catalogo cerrado de metricas y atributos definido en `phronesis.obs.metrics` y `phronesis.obs.attributes`. Cada panel filtra por templates Grafana (`$provider`, `$agent`, `$tool`, `$model`) auto-rellenados desde labels Prometheus.

Datasources requeridos (UIDs fijos):

- `phronesis-prom` (Prometheus)
- `phronesis-tempo` (Tempo)
- `phronesis-loki` (Loki)

<div align="center">

## 📋 phronesis-overview

</div>

Health agregado del sistema.

| Panel | Tipo | Query |
|---|---|---|
| Agent runs/min | stat | `sum(rate(phronesis_agent_runs_total[1m])) * 60` |
| Provider req/min | stat | `sum(rate(phronesis_provider_requests_total[1m])) * 60` |
| Tool invocations/min | stat | `sum(rate(phronesis_tool_invocations_total[1m])) * 60` |
| Tool error rate | stat | `sum(rate(phronesis_tool_errors_total[5m])) / clamp_min(sum(rate(phronesis_tool_invocations_total[5m])), 1)` |
| Cost USD (1h) | stat | derivado de `traces_spanmetrics_calls_total` |
| Provider duration P50/P95/P99 | timeseries | `histogram_quantile(q, sum(rate(phronesis_provider_duration_bucket[5m])) by (le))` |
| Agent run duration P50/P95/P99 | timeseries | mismo patron sobre `phronesis_agent_run_duration_bucket` |
| Recent errors | logs (Loki) | `{service_name=~"phronesis.*"} \|= "ERROR"` |

<div align="center">

## 📋 phronesis-providers

</div>

LLM performance y consumo de tokens.

Variables: `$provider`, `$model`.

| Panel | Tipo | Query |
|---|---|---|
| Requests by provider/model | table | `sum by (provider_name, provider_model) (increase(phronesis_provider_requests_total[1h]))` |
| Tokens/sec in/out stacked | timeseries | rates de `phronesis_provider_tokens_input_total` y `_output_total` |
| Provider duration heatmap | heatmap | `sum by (le) (rate(phronesis_provider_duration_bucket[5m]))` |
| Quantiles per provider | timeseries | `histogram_quantile` agrupado por `provider_name` |
| Stream first-chunk | traces | TraceQL `{ name =~ "provider.*" && span.stream.first_chunk_ms > 0 }` |

<div align="center">

## 📋 phronesis-tools

</div>

Performance por tool.

Variables: `$tool`.

| Panel | Tipo | Query |
|---|---|---|
| Top tools (1h) | barchart | `topk(10, sum by (tool_id) (increase(phronesis_tool_invocations_total[1h])))` |
| Error rate per tool | gauge | ratio tool_errors / tool_invocations |
| Tool duration heatmap | heatmap | `phronesis_tool_duration_bucket` |
| Recent failed calls | traces | `{ span.operation.success = false && span.tool.id != "" }` |

<div align="center">

## 📋 phronesis-agents

</div>

Ejecucion de agentes.

Variables: `$agent`.

| Panel | Tipo | Query |
|---|---|---|
| Active runs (5m) | stat | `sum(increase(phronesis_agent_runs_total[5m]))` |
| Runs/min by agent | timeseries | rate por `agent_name` |
| Tool calls per run | histogram | `phronesis_agent_tool_calls_per_run_bucket` |
| Agent run duration heatmap | heatmap | `phronesis_agent_run_duration_bucket` |
| Recent agent runs | traces | `{ span.agent.id != "" }` |

<div align="center">

## 📋 phronesis-pipelines

</div>

Orchestracion de pipelines.

Variables: `$pipeline`.

| Panel | Tipo | Query |
|---|---|---|
| Runs/min by name | timeseries | rate por `pipeline_name` |
| Success vs error | piechart | split por `operation_success` |
| Run duration heatmap | heatmap | `phronesis_pipeline_run_duration_bucket` |

<div align="center">

## 📋 phronesis-retries

</div>

Resiliencia: retries por provider y error.type.

Variables: `$provider`.

| Panel | Tipo | Query |
|---|---|---|
| Retry attempts/min by provider | timeseries | rate por `provider_name` |
| Retries by error type | timeseries | rate por `error_type` |
| Top error types (1h) | table | topk(10) por `(error_type, provider_name)` |

<div align="center">

## 📋 phronesis-traces-explorer

</div>

Navegacion Tempo.

Variables: `$agent_id`, `$session_id`, `$tool_id` (textbox).

| Panel | Tipo | Query |
|---|---|---|
| Service graph | nodeGraph | Tempo built-in `serviceMap` |
| Filtered traces | traces | `{ span.agent.id =~ "$agent_id.*" && span.session.id =~ "$session_id.*" && span.tool.id =~ "$tool_id.*" }` |
| Slow provider calls | traces | `{ span.provider.name != "" && duration > 5s }` |

<div align="center">

## ⚠️ Pitfalls

</div>

- Los nombres de metrica Prometheus tienen sufijos `_total` (counters) y `_bucket`/`_count`/`_sum` (histograms) anadidos por la exportacion OTLP.
- Los puntos en attributes (`provider.name`) se transforman en guiones bajos en labels Prometheus (`provider_name`).
- Para que el panel "Stream first-chunk" muestre datos, los providers deben reportar `stream.first_chunk_ms` como atributo del span (ya esta en el catalogo `attributes.STREAM_FIRST_CHUNK_MS`).
- El panel "Recent errors" del overview asume `service_name` con prefijo `phronesis`; ajustar el matcher si se usa otro `service_name` en `configure_obs`.
