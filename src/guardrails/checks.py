"""Guardrails: catch hallucinations and ungrounded claims in the narrative.

Design note:
    The analyst agent is the only LLM step whose output reaches a human. The
    guardrail cross-checks that narrative against the *validated* figures — any
    number mentioned in prose that does not trace back to an extracted figure is
    flagged as a potential hallucination. This is the "human-in-the-loop" trip
    wire: failed guardrails route the workflow to manual review rather than
    auto-publishing a wrong number.
"""
from __future__ import annotations

import re

from ..state import FinanceState

# Numbers we allow in prose without matching a figure (years, small counts).
_ALLOWLIST_MAX = 12


def _numbers_in(text: str) -> list[float]:
    raw = re.findall(r"\$?([\d,]+(?:\.\d+)?)", text)
    out = []
    for r in raw:
        try:
            out.append(float(r.replace(",", "")))
        except ValueError:
            continue
    return out


def guardrail_check(state: FinanceState) -> FinanceState:
    narrative = state.get("narrative", "")
    figures = set(state.get("figures", {}).values())

    flagged: list[float] = []
    for n in _numbers_in(narrative):
        if n <= _ALLOWLIST_MAX:
            continue  # ignore small integers (years, counts, sentence numbers)
        # A number is grounded if it matches any validated figure within $1.
        grounded = any(abs(n - f) <= 1.0 for f in figures)
        if not grounded:
            flagged.append(n)

    validation_passed = state.get("validation", {}).get("passed", False)
    passed = not flagged and validation_passed

    return {
        "guardrail": {
            "passed": passed,
            "ungrounded_numbers": flagged,
            "validation_passed": validation_passed,
        },
        "needs_human_review": not passed,
        "audit_log": [
            "guardrail: "
            + ("passed" if passed else f"FLAGGED {flagged or 'validation failure'}")
        ],
    }
