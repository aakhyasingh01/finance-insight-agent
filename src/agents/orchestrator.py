"""Orchestrator: wires the agents into a LangGraph multi-agent workflow.

Flow:

    extract -> validate -> (retry? ) -> analyze -> guardrail -> END
                     |                                    |
                     +--- on failure, retry extract <-----+
                          up to MAX_RETRIES, then flag for
                          human review.

The graph encodes a *self-correcting* loop: if validation or the guardrail
fails, control routes back to re-extraction (a cheap retry) before giving up and
handing off to a human. This mirrors the "autonomous, self-correcting agentic
systems ... with clear human-in-the-loop interfaces" described in the role.

If langgraph is not installed, a pure-Python fallback executor runs the same
nodes with the same routing logic, so the project always runs.
"""
from __future__ import annotations

from functools import partial

from ..guardrails.checks import guardrail_check
from ..llm import LLMClient
from ..state import FinanceState
from .analyst import analyst_agent
from .extractor import extractor_agent
from .validator import validator_agent

MAX_RETRIES = 2


def _route_after_validation(state: FinanceState) -> str:
    if state.get("validation", {}).get("passed"):
        return "analyze"
    if state.get("retries", 0) < MAX_RETRIES:
        return "retry"
    return "analyze"  # proceed; guardrail + human review will catch it


def _route_after_guardrail(state: FinanceState) -> str:
    if state.get("guardrail", {}).get("passed"):
        return "end"
    if state.get("retries", 0) < MAX_RETRIES:
        return "retry"
    return "end"  # exhausted retries -> ends flagged for human review


def _bump_retry(state: FinanceState) -> FinanceState:
    n = state.get("retries", 0) + 1
    return {"retries": n, "audit_log": [f"orchestrator: retry #{n}"]}


def build_graph(llm: LLMClient | None = None):
    """Build and compile the LangGraph graph. Falls back if langgraph absent."""
    llm = llm or LLMClient()
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return _FallbackGraph(llm)

    g = StateGraph(FinanceState)
    g.add_node("extract", partial(extractor_agent, llm=llm))
    g.add_node("validate", validator_agent)
    g.add_node("retry", _bump_retry)
    g.add_node("analyze", partial(analyst_agent, llm=llm))
    g.add_node("guardrail", guardrail_check)

    g.add_edge(START, "extract")
    g.add_edge("extract", "validate")
    g.add_conditional_edges(
        "validate", _route_after_validation,
        {"analyze": "analyze", "retry": "retry"},
    )
    g.add_edge("retry", "extract")
    g.add_edge("analyze", "guardrail")
    g.add_conditional_edges(
        "guardrail", _route_after_guardrail,
        {"end": END, "retry": "retry"},
    )
    return g.compile()


class _FallbackGraph:
    """Pure-Python executor mirroring the LangGraph routing (no dependency)."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def invoke(self, state: FinanceState) -> FinanceState:
        s: FinanceState = {**state, "retries": 0, "audit_log": []}

        def apply(update: FinanceState) -> None:
            """Merge a node's output, appending to the audit log like LangGraph."""
            nonlocal s
            log = s.get("audit_log", []) + update.get("audit_log", [])
            s = {**s, **update, "audit_log": log}

        while True:
            apply(extractor_agent(s, llm=self.llm))
            apply(validator_agent(s))
            if (not s.get("validation", {}).get("passed")
                    and s.get("retries", 0) < MAX_RETRIES):
                apply(_bump_retry(s))
                continue
            apply(analyst_agent(s, llm=self.llm))
            apply(guardrail_check(s))
            if (not s.get("guardrail", {}).get("passed")
                    and s.get("retries", 0) < MAX_RETRIES):
                apply(_bump_retry(s))
                continue
            return s
