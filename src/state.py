"""Shared state passed between agents in the LangGraph workflow.

Using a typed state object (rather than an untyped dict) makes the data flow
auditable — every agent declares what it reads and writes, which is exactly the
property the Finance domain demands.
"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict


def _merge(old: list, new: list) -> list:
    """Reducer: append new log entries instead of overwriting."""
    return (old or []) + (new or [])


class FinanceState(TypedDict, total=False):
    # Inputs
    document: dict[str, Any]          # raw financial document
    # Produced by the extractor agent
    figures: dict[str, float]
    # Produced by the validator agent
    validation: dict[str, Any]
    # Produced by the analyst agent
    narrative: str
    # Guardrail outcome
    guardrail: dict[str, Any]
    # Control flow
    retries: int
    needs_human_review: bool
    # Audit trail (append-only)
    audit_log: Annotated[list[str], _merge]
