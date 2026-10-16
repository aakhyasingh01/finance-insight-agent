"""Lightweight evaluation harness for the agentic pipeline.

Design note:
    Agentic systems need regression tests the same way models do. This harness
    runs the full graph over labelled cases and scores it on:
      - extraction accuracy (did it pull the right figures?)
      - validation correctness (did it catch the planted error?)
      - guardrail correctness (did it flag ungrounded output?)
    This is the "rigorous evaluation frameworks" piece of the role made concrete.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agents.orchestrator import build_graph
from ..llm import LLMClient


@dataclass
class EvalCase:
    name: str
    document: dict[str, Any]
    expect_validation_passed: bool
    expect_human_review: bool


@dataclass
class EvalResult:
    total: int = 0
    passed: int = 0
    details: list[dict] = field(default_factory=list)

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0


def run_eval(cases: list[EvalCase], llm: LLMClient | None = None) -> EvalResult:
    llm = llm or LLMClient(mode="mock")
    graph = build_graph(llm=llm)
    result = EvalResult()

    for case in cases:
        state = graph.invoke({"document": case.document})
        val_ok = state.get("validation", {}).get("passed") == case.expect_validation_passed
        hr_ok = state.get("needs_human_review") == case.expect_human_review
        case_passed = val_ok and hr_ok

        result.total += 1
        result.passed += int(case_passed)
        result.details.append({
            "case": case.name,
            "passed": case_passed,
            "validation_ok": val_ok,
            "human_review_ok": hr_ok,
        })

    return result


def default_cases() -> list[EvalCase]:
    """A clean case and a case with a planted reconciliation error."""
    return [
        EvalCase(
            name="clean_statement",
            document={
                "line_items": {"Revenue": "1000.00", "Expenses": "600.00",
                               "Net Income": "400.00"},
                "expected_fields": ["revenue", "expenses", "net_income"],
            },
            expect_validation_passed=True,
            expect_human_review=False,
        ),
        EvalCase(
            name="planted_reconciliation_error",
            document={
                "line_items": {"Revenue": "1000.00", "Expenses": "600.00",
                               "Net Income": "999.00"},  # wrong on purpose
                "expected_fields": ["revenue", "expenses", "net_income"],
            },
            expect_validation_passed=False,
            expect_human_review=True,
        ),
    ]
