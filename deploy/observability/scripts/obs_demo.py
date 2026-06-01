"""End-to-end validation of the local observability stack.

Emits synthetic agent runs, tool invocations and provider requests
through ``phronesis.obs`` so dashboards can be eyeballed in Grafana.

Usage::

    uv run python deploy/observability/scripts/obs_demo.py

Prerequisites:

- Stack running: ``docker compose -f docker-compose.dev.yml up -d``.
- ``phronesis[obs]`` extra installed.
"""

from __future__ import annotations

import random
import time
from typing import Final

from phronesis.obs import (  # type: ignore[import-untyped]
    attributes,
    configure_obs,
    current_trace_id,
    metrics,
    start_span,
)

OTLP_ENDPOINT: Final[str] = "http://localhost:4318"
GRAFANA_URL: Final[str] = "http://localhost:3000"

TOOLS: Final[tuple[str, ...]] = ("search.web", "fs.read", "fs.write", "shell.run")
PROVIDERS: Final[tuple[tuple[str, str], ...]] = (
    ("anthropic", "claude-opus-4-7"),
    ("openai", "gpt-4o"),
    ("ollama", "llama3.1:8b"),
)
AGENTS: Final[tuple[str, ...]] = ("researcher", "coder", "reviewer")


def _emit_provider_call(provider: str, model: str) -> None:
    duration = random.uniform(0.2, 4.5)
    tokens_in = random.randint(120, 4000)
    tokens_out = random.randint(40, 1500)

    with start_span(
        "provider.complete",
        attrs={
            attributes.PROVIDER_NAME: provider,
            attributes.PROVIDER_MODEL: model,
        },
    ) as span:
        span.set_attribute(attributes.TOKENS_INPUT, tokens_in)
        span.set_attribute(attributes.TOKENS_OUTPUT, tokens_out)
        span.set_attribute(attributes.TOKENS_TOTAL, tokens_in + tokens_out)
        span.set_attribute(attributes.OPERATION_DURATION_MS, duration * 1000)
        span.set_attribute(attributes.OPERATION_SUCCESS, True)

        metrics.provider_requests.add(1, {"provider.name": provider, "provider.model": model})
        metrics.provider_tokens_input.add(tokens_in, {"provider.name": provider})
        metrics.provider_tokens_output.add(tokens_out, {"provider.name": provider})
        metrics.provider_duration.record(duration, {"provider.name": provider})

        time.sleep(min(duration, 0.2))


def _emit_tool_call(tool_id: str) -> None:
    duration = random.uniform(0.05, 1.2)
    failed = random.random() < 0.08

    with start_span("tool.invoke", attrs={attributes.TOOL_ID: tool_id}) as span:
        span.set_attribute(attributes.OPERATION_DURATION_MS, duration * 1000)
        span.set_attribute(attributes.OPERATION_SUCCESS, not failed)

        metrics.tool_invocations.add(1, {"tool.id": tool_id})
        metrics.tool_duration.record(duration, {"tool.id": tool_id})

        if failed:
            span.set_attribute(attributes.ERROR_TYPE, "ToolExecutionError")
            metrics.tool_errors.add(1, {"tool.id": tool_id, "error.type": "ToolExecutionError"})

        time.sleep(min(duration, 0.1))


def _emit_agent_run(agent_name: str) -> str | None:
    run_duration = random.uniform(1.0, 12.0)
    tool_calls = random.randint(1, 8)

    with start_span(
        "agent.run",
        attrs={
            attributes.AGENT_NAME: agent_name,
            attributes.AGENT_ID: f"{agent_name}-{random.randint(1000, 9999)}",
        },
    ) as span:
        trace_id: str | None = current_trace_id()

        for _ in range(tool_calls):
            _emit_tool_call(random.choice(TOOLS))

        provider, model = random.choice(PROVIDERS)
        _emit_provider_call(provider, model)

        span.set_attribute(attributes.OPERATION_DURATION_MS, run_duration * 1000)
        span.set_attribute(attributes.OPERATION_SUCCESS, True)

        metrics.agent_runs.add(1, {"agent.name": agent_name})
        metrics.agent_run_duration.record(run_duration, {"agent.name": agent_name})
        metrics.agent_tool_calls_per_run.record(tool_calls, {"agent.name": agent_name})

        return trace_id


def main() -> None:
    configure_obs(
        exporter="otlp",
        endpoint=OTLP_ENDPOINT,
        service_name="phronesis-demo",
    )

    print(f"[obs_demo] OTLP -> {OTLP_ENDPOINT}")
    print("[obs_demo] emitting synthetic traffic...")

    root_trace_id: str | None = None

    for i in range(5):
        agent = random.choice(AGENTS)
        tid = _emit_agent_run(agent)

        if root_trace_id is None and tid is not None:
            root_trace_id = tid

        print(f"  run {i + 1}/5 - agent={agent} trace_id={tid}")

    print()
    print(f"[obs_demo] root trace_id: {root_trace_id}")
    print(f"[obs_demo] Grafana:     {GRAFANA_URL}")
    print(f"[obs_demo] Overview:    {GRAFANA_URL}/d/phronesis-overview")
    print(f"[obs_demo] Traces:      {GRAFANA_URL}/d/phronesis-traces-explorer")

    time.sleep(2.0)


if __name__ == "__main__":
    main()
