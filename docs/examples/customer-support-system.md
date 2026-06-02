#

<div align="center">

# Phronesis Framework - Example: Customer Support System

</div>

<div align="center">
  End-to-end example of how a complete agent system could be declared using Phronesis once the full runtime layer is in place. Shows the philosophy: decorators for atoms, combinators for composition, a single uniform interface for everything.
</div>

<div align="center">
  <a href="../index.md">docs</a>
</div>

<div align="center">

[![Status](https://img.shields.io/badge/status-vision-orange)]()
[![Mix](https://img.shields.io/badge/scope-implemented%20%2B%20future-blue)]()

</div>

---

<div align="center">

## 🎯 Purpose

</div>

This document shows what defining a complete, production-grade agent system would look like in Phronesis. It mixes the surface that exists today (`@agent`, `@tool`, `ContextBuilder`, `Session`, streaming events) with the proposed runtime combinators (`sequence`, `router`, `reflexion`, `approval`, ...) that will live in `phronesis/runtime/` once the placeholder is filled.

The point is not the scenario - it is the **shape of the code**. Read it as if it were a final API and ask:

- Does it read declaratively?
- Does each layer do one thing?
- Could you add a new execution mode without touching anything else?

Markers used inline:

- `[IMPL]` - already implemented on the `main`/`feats/context/init-context` branch.
- `[FUT]` - proposed addition that follows the same design philosophy.

<div align="center">

## 🏗️ Design philosophy in three lines

</div>

1. **Decorators declare atoms** - `@agent`, `@tool`. Frozen specs, no behavior coupling.
2. **Functions compose** - `sequence(a, b)`, `router(triage, {...})`. Combinators take agents and return agents.
3. **One uniform interface** - every leaf and every composite has `.run()`, `.stream()`, `.session()`.

<div align="center">

## 📋 Full example

</div>

```python
"""Customer support system - Phronesis full-stack example.

Markers:
  [IMPL] - works today on the current main branch.
  [FUT]  - proposed combinator that follows the same philosophy and
           would live in phronesis.runtime once implemented.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

# ────────────────────────────────────────────────────────────────────
# Imports
# ────────────────────────────────────────────────────────────────────

# [IMPL]
from phronesis import agent, tool, Context
from phronesis.tools import ToolEffect
from phronesis.tools.markers import Pattern
from phronesis.context import CompactingContextBuilder
from phronesis.providers import anthropic, openai
from phronesis.providers.errors import ProviderError
from phronesis.agents import RunRequest, TextDelta, ToolCallStarted

# [FUT] runtime combinators - same philosophy: frozen specs,
# protocol-driven, registry-aware.
from phronesis.runtime import (
    # composition
    sequence, parallel, race, loop_, map_, map_reduce,
    # control flow
    conditional, router,
    # iteration / refinement
    react_loop, plan_and_execute, reflexion, tree_search,
    # coordination
    supervisor, handoff_chain,
    # aggregation
    consensus, debate,
    # robustness
    retry, fallback,
    # human-in-the-loop
    approval,
)
from phronesis.runtime.events import (
    AgentTransition, ApprovalRequested, BranchTaken,
)


# ────────────────────────────────────────────────────────────────────
# Providers [IMPL]
# ────────────────────────────────────────────────────────────────────

fast = openai(model="gpt-4o-mini")
strong = anthropic(model="claude-opus-4-5-20251101")
cheap_compactor = openai(model="gpt-4o-mini")


# ────────────────────────────────────────────────────────────────────
# Tools [IMPL]
# ────────────────────────────────────────────────────────────────────

@tool(effects=(ToolEffect.FILESYSTEM_READ,))
async def search_kb(
    ctx: Context,
    query: Annotated[str, "Semantic search query"],
) -> list[dict]:
    """Search the technical knowledge base."""
    return await kb.search(query, k=5)


@tool(effects=(ToolEffect.NETWORK,))
async def lookup_account(
    ctx: Context,
    customer_id: Annotated[str, Pattern(r"^CUS-\d{6}$")],
) -> dict:
    """Fetch CRM record for the customer."""
    return await crm.get(customer_id)


@tool(effects=(
    ToolEffect.SIDE_EFFECT,
    ToolEffect.REQUIRES_CONFIRMATION,
))
async def issue_refund(
    ctx: Context,
    customer_id: str,
    amount_usd: float,
    reason: str,
) -> dict:
    """Issue a refund. Gated by approval() in the runtime layer."""
    return await billing_api.refund(customer_id, amount_usd, reason)


# ────────────────────────────────────────────────────────────────────
# Output types [IMPL]
# ────────────────────────────────────────────────────────────────────

class Category(StrEnum):
    TECHNICAL = "technical"
    BILLING = "billing"
    SALES = "sales"


# ────────────────────────────────────────────────────────────────────
# Leaf agents [IMPL]
# ────────────────────────────────────────────────────────────────────

@agent(model=fast, output_type=Category, system_prompt="""
You are a triage classifier. Read the ticket and return one of:
technical | billing | sales.
""")
def triage() -> None: ...


@agent(
    model=strong,
    tools=[search_kb],
    context_builder=CompactingContextBuilder(
        threshold_ratio=0.7,
        compactor_provider=cheap_compactor,
    ),
    system_prompt="You are a senior technical support engineer.",
    max_iterations=15,
)
def tech_support() -> None: ...


@agent(
    model=strong,
    tools=[lookup_account, issue_refund],
    system_prompt="You are a billing specialist.",
)
def billing_agent() -> None: ...


@agent(model=strong, system_prompt="Qualify the lead. Output BANT score.")
def qualify_lead() -> None: ...


@agent(model=strong, system_prompt="Propose tailored solution.")
def propose_solution() -> None: ...


@agent(model=strong, system_prompt="Schedule the followup meeting.")
def schedule_followup() -> None: ...


@agent(model=strong, system_prompt="Critique the draft for accuracy.")
def critic() -> None: ...


@agent(model=strong, system_prompt="Escalate to human operator.")
def human_handoff() -> None: ...


# ────────────────────────────────────────────────────────────────────
# Composition: sales pipeline [FUT]
# ────────────────────────────────────────────────────────────────────

sales = sequence(
    qualify_lead,
    propose_solution,
    schedule_followup,
    name="sales_pipeline",
)


# ────────────────────────────────────────────────────────────────────
# Composition: billing with approval gate [FUT]
# ────────────────────────────────────────────────────────────────────

gated_billing = approval(
    billing_agent,
    when=lambda r: r.metadata.get("refund_usd", 0) > 100,
    prompt="Refund > $100 requested. Approve? [y/n]",
    on_reject=human_handoff,
)


# ────────────────────────────────────────────────────────────────────
# Composition: resilience wrapper [FUT]
# ────────────────────────────────────────────────────────────────────

resilient_billing = fallback(
    retry(gated_billing, max_attempts=3, backoff="exponential"),
    on=ProviderError,
    handler=human_handoff,
)


# ────────────────────────────────────────────────────────────────────
# Composition: tech support with self-critique [FUT]
# ────────────────────────────────────────────────────────────────────

quality_tech_support = reflexion(
    base=tech_support,
    critic=critic,
    max_iterations=2,
    stop_when=lambda score: score >= 0.85,
)


# ────────────────────────────────────────────────────────────────────
# Root system: router over triage → specialists [FUT]
# ────────────────────────────────────────────────────────────────────

support_system = router(
    classifier=triage,
    routes={
        Category.TECHNICAL: quality_tech_support,
        Category.BILLING:   resilient_billing,
        Category.SALES:     sales,
    },
    default=human_handoff,
    name="customer_support",
)


# ────────────────────────────────────────────────────────────────────
# Usage - one-shot [IMPL for Agent, FUT for composites]
# ────────────────────────────────────────────────────────────────────

async def handle_ticket(text: str) -> str:
    result = await support_system.run(RunRequest(input=text))
    return result.output


# ────────────────────────────────────────────────────────────────────
# Usage - streaming
# ────────────────────────────────────────────────────────────────────

async def stream_ticket(text: str) -> None:
    """Streaming with typed events - runtime events extend the union."""
    async for event in support_system.stream(RunRequest(input=text)):
        match event:
            case TextDelta(text=chunk):
                print(chunk, end="", flush=True)

            case ToolCallStarted(tool_name=name, args=args):
                print(f"\n→ calling {name}({args})")

            # [FUT] runtime events
            case BranchTaken(branch=Category.BILLING):
                print("\n[routed to billing]")

            case AgentTransition(from_=src, to=dst, reason=r):
                print(f"\n[{src} → {dst}: {r}]")

            case ApprovalRequested(prompt=p, event_id=eid):
                ok = input(f"{p} ").lower() == "y"
                await support_system.respond(eid, approved=ok)


# ────────────────────────────────────────────────────────────────────
# Usage - multi-turn session [IMPL]
# ────────────────────────────────────────────────────────────────────

async def chat_loop() -> None:
    session = support_system.session()
    while True:
        user_msg = input("> ")
        if not user_msg:
            break

        result = await session.run(RunRequest(input=user_msg))
        print(result.output)
```

<div align="center">

## 🧩 Showcase of additional combinators

</div>

The same philosophy extended to every execution mode discussed:

```python
# Plan-and-Execute - plan the full roadmap, then execute without
# returning to the LLM between tools.
roadmap_planner = plan_and_execute(
    planner=strategic_planner,
    executor=task_executor,
    max_steps=20,
)

# Debate among specialists adjudicated by a senior.
medical_panel = debate(
    participants=[cardiologist, neurologist, internist],
    judge=chief_physician,
    rounds=3,
)

# Tree search with backtracking.
puzzle_solver = tree_search(
    expander=move_generator,
    evaluator=position_scorer,
    strategy="beam",
    beam_width=4,
    max_depth=8,
)

# MapReduce over a document collection.
doc_digest = map_reduce(
    mapper=chunk_summarizer,
    reducer=summary_merger,
    chunk_by=4000,
)

# Race - first provider to answer wins, the rest are cancelled.
fastest_answer = race(
    tech_support.with_provider(anthropic_provider),
    tech_support.with_provider(openai_provider),
)

# Consensus - N runs in parallel, vote.
robust_classifier = consensus(
    voters=[triage, triage, triage],
    quorum=2,
)

# Hierarchical supervisor with named workers.
research_team = supervisor(
    coordinator=research_lead,
    workers={
        "literature": literature_searcher,
        "data": data_analyst,
        "writing": science_writer,
    },
    max_delegations=10,
)

# Handoff chain - control jumps forward with no return.
onboarding = handoff_chain([
    welcome_agent,
    setup_agent,
    tutorial_agent,
])

# Generic loop with a stop condition.
keep_polishing = loop_(
    body=editor,
    until=lambda result: result.metadata["quality"] >= 0.95,
    max_iterations=10,
)
```

<div align="center">

## 📐 What this proves about the philosophy

</div>

1. **A single uniform interface.** `Agent`, `sequence(...)`, `router(...)`, `reflexion(...)` - every one of them exposes `.run()`, `.stream()`, `.session()`. Composites are not second-class citizens.

2. **Decorators for atoms, functions for composition.** Reads naturally and matches how `@agent` / `@tool` already work today.

3. **Immutability + composability.** Each combinator takes agents and returns an agent. Lego-like.

4. **The streaming event union scales.** New runtime events (`BranchTaken`, `AgentTransition`, `ApprovalRequested`) extend the closed `AgentEvent` union deliberately, as the project conventions demand.

5. **Context builders, tools, and combinators are orthogonal.** `CompactingContextBuilder` lives inside `tech_support`, which lives inside `reflexion(...)`, which lives inside `router(...)`. Each layer is unaware of the others.

6. **Declarations meet enforcement.** `ToolEffect.REQUIRES_CONFIRMATION` is the declaration; `approval(...)` is the enforcer. Today only the declaration exists; the runtime closes the loop.

<div align="center">

## ⚠️ What to look for when reading this

</div>

If the example **reads naturally** without you having written a line of it, the philosophy is right.

If anything in the example **surprises you**, that is signal to rediscuss before implementing:

- Does the decorator/combinator split feel arbitrary?
- Is the `.run()` / `.stream()` / `.session()` triple too narrow?
- Should `approval(...)` be a method on agents instead of a wrapper?
- Should combinators return `AgentSpec`-like frozen specs that a runtime executes, or should they return live `Agent` instances?

Those are the decisions that lock in or unlock future flexibility.

<div align="center">

## 🔮 Implementation order (if we proceed)

</div>

A sensible order that maximises value per increment:

1. `Agent.stream()` - purely additive, unblocks UX for everything else.
2. `runtime/` skeleton + `sequence`, `parallel`, `conditional` - the bedrock combinators.
3. `retry`, `fallback` - robustness layer.
4. `router`, `supervisor`, `handoff_chain` - single-LLM multi-agent topologies.
5. `reflexion`, `plan_and_execute` - alternative single-agent loops.
6. `approval` + human-in-the-loop runtime events - closes the `REQUIRES_CONFIRMATION` story.
7. `consensus`, `debate`, `tree_search`, `map_reduce` - advanced patterns.
8. `memory/`, `mcp/`, `pipelines/` - fill the remaining placeholders.

Each step is one PR, each step ships its own docs page following the same conventions as `docs/context/index.md`.
