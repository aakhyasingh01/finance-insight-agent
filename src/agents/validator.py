"""Validator agent: deterministic reconciliation of extracted figures.

Design note:
    This agent uses **no LLM**. Financial accuracy must be deterministic and
    auditable, so reconciliation is pure Python arithmetic. This directly
    reflects the "deterministic accuracy and auditability are paramount"
    requirement of regulated-finance work — the LLM extracts, but math is
    checked by code the auditor can read.
"""
from __future__ import annotations

from ..state import FinanceState

# Tolerance for floating-point reconciliation (one cent).
TOLERANCE = 0.01


def validator_agent(state: FinanceState) -> FinanceState:
    figures = state.get("figures", {})
    checks: list[dict] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    # Check 1: completeness — did we extract the expected core fields?
    expected = state["document"].get("expected_fields", [])
    missing = [f for f in expected if f not in figures]
    record(
        "completeness",
        not missing,
        "all expected fields present" if not missing else f"missing: {missing}",
    )

    # Check 2: reconciliation — net_income == revenue - expenses (if present)
    if {"revenue", "expenses", "net_income"} <= figures.keys():
        derived = figures["revenue"] - figures["expenses"]
        diff = abs(derived - figures["net_income"])
        record(
            "net_income_reconciliation",
            diff <= TOLERANCE,
            f"revenue - expenses = {derived:.2f} vs stated "
            f"net_income = {figures['net_income']:.2f} (diff {diff:.2f})",
        )

    # Check 3: non-negativity of core magnitudes
    for field in ("revenue", "expenses"):
        if field in figures:
            record(
                f"{field}_non_negative",
                figures[field] >= 0,
                f"{field} = {figures[field]:.2f}",
            )

    passed = all(c["passed"] for c in checks)
    return {
        "validation": {"passed": passed, "checks": checks},
        "audit_log": [
            f"validator: {sum(c['passed'] for c in checks)}/{len(checks)} checks passed"
        ],
    }
