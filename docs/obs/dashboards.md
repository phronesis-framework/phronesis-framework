#

<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis - Dashboards catalog" width="60%" />
</div>

<div align="center">

# Phronesis Framework - Dashboards catalog

</div>

<div align="center">
  Panel-by-panel catalog of the seven pre-built Grafana dashboards in <code>deploy/observability/grafana/dashboards/</code>.
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

The dashboards consume only the closed catalog of metrics and attributes defined in `phronesis.obs.metrics` and `phronesis.obs.attributes`. Each panel filters by Grafana template variables (`$provider`, `$agent`, `$tool`, `$model`) auto-populated from Prometheus labels.

Required datasources (fixed UIDs):

- `phronesis-prom` (Prometheus)
- `phronesis-tempo` (Tempo)
- `phronesis-loki` (Loki)

<div align="center">

## 📋 phronesis-overview

</div>

Aggregated system health.

| Panel | Type | Query |
|---|---|---|
| Agent runs/min | stat | `sum(rate(phronesis_agent_runs_total[1m])) * 60` |
| Provider req/min | stat | `sum(rate(phronesis_provider_requests_total[1m])) * 60` |
| Tool invocations/min | stat | `sum(rate(phronesis_tool_invocations_total[1m])) * 60` |
| Tool error rate | stat | `sum(rate(phronesis_tool_errors_total[5m])) / clamp_min(sum(rate(phronesis_tool_invocations_total[5m])), 1)` |
| Cost USD (1h) | stat | derived from `traces_spanmetrics_calls_total` |
| Provider duration P50/P95/P99 | timeseries | `histogram_quantile(q, sum(rate(phronesis_provider_duration_bucket[5m])) by (le))` |
| Agent run duration P50/P95/P99 | timeseries | same pattern over `phronesis_agent_run_duration_bucket` |
| Recent errors | logs (Loki) | `{service_name=~"phronesis.*"} \|= "ERROR"` |

<div align="center">

## 📋 phronesis-providers

</div>

LLM performance and token consumption.

Variables: `$provider`, `$model`.

| Panel | Type | Query |
|---|---|---|
| Requests by provider/model | table | `sum by (provider_name, provider_model) (increase(phronesis_provider_requests_total[1h]))` |
| Tokens/sec in/out stacked | timeseries | rates of `phronesis_provider_tokens_input_total` and `_output_total` |
| Provider duration heatmap | heatmap | `sum by (le) (rate(phronesis_provider_duration_bucket[5m]))` |
| Quantiles per provider | timeseries | `histogram_quantile` grouped by `provider_name` |
| Stream first-chunk | traces | TraceQL `{ name =~ "provider.*" && span.stream.first_chunk_ms > 0 }` |

<div align="center">

## 📋 phronesis-tools

</div>

Per-tool performance.

Variables: `$tool`.

| Panel | Type | Query |
|---|---|---|
| Top tools (1h) | barchart | `topk(10, sum by (tool_id) (increase(phronesis_tool_invocations_total[1h])))` |
| Error rate per tool | gauge | ratio tool_errors / tool_invocations |
| Tool duration heatmap | heatmap | `phronesis_tool_duration_bucket` |
| Recent failed calls | traces | `{ span.operation.success = false && span.tool.id != "" }` |

<div align="center">

## 📋 phronesis-agents

</div>

Agent execution.

Variables: `$agent`.

| Panel | Type | Query |
|---|---|---|
| Active runs (5m) | stat | `sum(increase(phronesis_agent_runs_total[5m]))` |
| Runs/min by agent | timeseries | rate by `agent_name` |
| Tool calls per run | histogram | `phronesis_agent_tool_calls_per_run_bucket` |
| Agent run duration heatmap | heatmap | `phronesis_agent_run_duration_bucket` |
| Recent agent runs | traces | `{ span.agent.id != "" }` |

<div align="center">

## 📋 phronesis-pipelines

</div>

Pipeline orchestration.

Variables: `$pipeline`.

| Panel | Type | Query |
|---|---|---|
| Runs/min by name | timeseries | rate by `pipeline_name` |
| Success vs error | piechart | split by `operation_success` |
| Run duration heatmap | heatmap | `phronesis_pipeline_run_duration_bucket` |

<div align="center">

## 📋 phronesis-retries

</div>

Resilience: retries by provider and error.type.

Variables: `$provider`.

| Panel | Type | Query |
|---|---|---|
| Retry attempts/min by provider | timeseries | rate by `provider_name` |
| Retries by error type | timeseries | rate by `error_type` |
| Top error types (1h) | table | topk(10) by `(error_type, provider_name)` |

<div align="center">

## 📋 phronesis-traces-explorer

</div>

Tempo navigation.

Variables: `$agent_id`, `$session_id`, `$tool_id` (textbox).

| Panel | Type | Query |
|---|---|---|
| Service graph | nodeGraph | Tempo built-in `serviceMap` |
| Filtered traces | traces | `{ span.agent.id =~ "$agent_id.*" && span.session.id =~ "$session_id.*" && span.tool.id =~ "$tool_id.*" }` |
| Slow provider calls | traces | `{ span.provider.name != "" && duration > 5s }` |

<div align="center">

## ⚠️ Pitfalls

</div>

- Prometheus metric names carry `_total` (counters) and `_bucket`/`_count`/`_sum` (histograms) suffixes added by the OTLP export.
- Dots in attributes (`provider.name`) become underscores in Prometheus labels (`provider_name`).
- For the "Stream first-chunk" panel to show data, providers must report `stream.first_chunk_ms` as a span attribute (already in the catalog as `attributes.STREAM_FIRST_CHUNK_MS`).
- The overview's "Recent errors" panel assumes a `service_name` prefixed with `phronesis`; adjust the matcher if a different `service_name` is used in `configure_obs`.
