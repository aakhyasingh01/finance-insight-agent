"""Extractor agent: pulls structured figures out of a financial document."""
from __future__ import annotations

import json

from ..llm import LLMClient
from ..state import FinanceState

_SYSTEM = (
    "You are a meticulous financial data extraction agent. "
    "Extract only figures explicitly present in the document. "
    "Never infer or invent numbers. Respond with strict JSON."
)


def _render_document(document: dict) -> str:
    lines = [f"{k}: {v}" for k, v in document.get("line_items", {}).items()]
    return "\n".join(lines)


def extractor_agent(state: FinanceState, llm: LLMClient | None = None) -> FinanceState:
    llm = llm or LLMClient()
    doc_text = _render_document(state["document"])
    prompt = (
        "TASK:EXTRACT\n"
        "Extract every labelled monetary figure from this statement as JSON "
        'under a top-level key "figures":\n\n'
        f"{doc_text}"
    )
    resp = llm.complete(prompt, system=_SYSTEM)

    try:
        parsed = json.loads(resp.text)
        figures = {k: float(v) for k, v in parsed.get("figures", {}).items()}
    except (json.JSONDecodeError, ValueError, TypeError):
        figures = {}

    return {
        "figures": figures,
        "audit_log": [f"extractor: parsed {len(figures)} figures"],
    }
