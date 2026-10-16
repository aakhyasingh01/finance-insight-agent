"""Unit tests for the deterministic validator and the guardrail."""
from src.agents.validator import validator_agent
from src.guardrails.checks import guardrail_check


def test_validator_passes_clean_statement():
    state = {
        "document": {"expected_fields": ["revenue", "expenses", "net_income"]},
        "figures": {"revenue": 1000.0, "expenses": 600.0, "net_income": 400.0},
    }
    out = validator_agent(state)
    assert out["validation"]["passed"] is True


def test_validator_catches_reconciliation_error():
    state = {
        "document": {"expected_fields": ["revenue", "expenses", "net_income"]},
        "figures": {"revenue": 1000.0, "expenses": 600.0, "net_income": 999.0},
    }
    out = validator_agent(state)
    assert out["validation"]["passed"] is False
    names = {c["check"]: c["passed"] for c in out["validation"]["checks"]}
    assert names["net_income_reconciliation"] is False


def test_validator_flags_missing_field():
    state = {
        "document": {"expected_fields": ["revenue", "expenses", "net_income"]},
        "figures": {"revenue": 1000.0},
    }
    out = validator_agent(state)
    assert out["validation"]["passed"] is False


def test_guardrail_flags_ungrounded_number():
    state = {
        "narrative": "Revenue grew to 5000000 this quarter.",  # not in figures
        "figures": {"revenue": 1000.0},
        "validation": {"passed": True},
    }
    out = guardrail_check(state)
    assert out["guardrail"]["passed"] is False
    assert 5000000.0 in out["guardrail"]["ungrounded_numbers"]
    assert out["needs_human_review"] is True


def test_guardrail_passes_grounded_narrative():
    state = {
        "narrative": "The statement reconciles cleanly with no anomalies.",
        "figures": {"revenue": 1000.0, "net_income": 400.0},
        "validation": {"passed": True},
    }
    out = guardrail_check(state)
    assert out["guardrail"]["passed"] is True
    assert out["needs_human_review"] is False
