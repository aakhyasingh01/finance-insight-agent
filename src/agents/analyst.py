"""Analyst agent: turns validated figures into a business-readable narrative."""
from __future__ import annotations

from ..llm import LLMClient
from ..state import FinanceState

_SYSTEM = (
    "You are a finance analyst. Write a concise, factual summary for a "
    "non-technical executive. Only reference figures that were validated. "
    "Do not speculate beyond the data."
)


def analyst_agent(state: FinanceState, llm: LLMClient | None = None) -> FinanceState:
    llm = llm or LLMClient()
    figures = state.get("figures", {})
    validation = state.get("validation", {})

    prompt = (
        "TASK:NARRATE\n"
        f"Validated figures: {figures}\n"
        f"Validation result: {validation.get('passed')}\n"
        "Write a 2-3 sentence executive summary."
    )
    resp = llm.complete(prompt, system=_SYSTEM)
    return {
        "narrative": resp.text,
        "audit_log": ["analyst: narrative generated"],
    }
