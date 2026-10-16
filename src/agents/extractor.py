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


    # Real LLMs often wrap JSON in markdown code fences (```json ... ```),
    # and may use nested objects like {"revenue": {"amount": 1250000}}.
    # Normalize before parsing.
    text = resp.text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]       # drop opening fence
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]           # drop the 'json' language tag
        text = text.strip()

    def _to_number(value):
        """Coerce a figure to float, handling nested dicts and currency text."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict):
            # e.g. {"amount": 1250000, "currency": "USD"}
            for key in ("amount", "value"):
                if key in value:
                    return _to_number(value[key])
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("$", "").strip()
            return float(cleaned)
        raise ValueError(f"cannot coerce {value!r} to number")

    figures = {}
    try:
        parsed = json.loads(text)
        for k, v in parsed.get("figures", {}).items():
            try:
                figures[k.strip().lower().replace(" ", "_")] = _to_number(v)
            except (ValueError, TypeError):
                continue  # skip any figure we can't parse
    except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
        figures = {}

    return {
        "figures": figures,
        "audit_log": [f"extractor: parsed {len(figures)} figures"],
    }

