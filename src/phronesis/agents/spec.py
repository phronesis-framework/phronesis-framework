"""Pure data spec for a declared agent.

See ``docs/AGENTS-DECISIONS.md`` (D-03, D-09): :class:`AgentSpec` is
frozen, serializable, and contains **no behaviour** — the executable
side lives on the :class:`phronesis.agents.agent.Agent` wrapper. The
spec holds the model reference because providers are typically
long-lived objects shared across agents.
"""

from __future__ import annotations

from dataclasses import dataclass

from phronesis.agents.id import AgentId
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """Static description of an agent.

    Attributes:
        id: Stable internal identifier.
        name: LLM-facing name (also used by multi-agent discovery).
        model: The provider that backs ``run()`` and ``stream()``.
        system_prompt: System instructions sent on every turn.
        tools: Tools the agent may invoke. May be empty.
        description: Human-readable summary (defaults to empty).
        output_type: Expected output type for structured runs. ``None``
            means free-form text output.
        max_iterations: Maximum tool-calling loop iterations before the
            loop aborts with :class:`AgentMaxIterationsError`.
        version: Free-form version string for the spec.
    """

    id: AgentId
    name: str
    model: LLMProvider
    system_prompt: str
    tools: tuple[Tool, ...] = ()
    description: str = ""
    output_type: type | None = None
    max_iterations: int = 20
    version: str = "0.1.0"
