"""CLI entry point: run the agentic finance pipeline on a document.

Usage:
    python main.py                      # runs the bundled sample statement
    python main.py path/to/doc.json     # runs your own document
    python main.py --eval               # runs the evaluation harness

Set LLM_MODE=mock (default) to run without an API key, or provide a
GOOGLE_API_KEY in .env and set LLM_MODE=live to use real Gemini.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional; env vars still work without it
    def load_dotenv(*_args, **_kwargs):
        return False

from src.agents.orchestrator import build_graph
from src.eval import default_cases, run_eval
from src.llm import LLMClient

load_dotenv()


def _print_report(state: dict) -> None:
    print("\n=== FINANCE AGENT REPORT ===")
    print("\nExtracted figures:")
    for k, v in state.get("figures", {}).items():
        print(f"  {k:>14}: {v:,.2f}")

    val = state.get("validation", {})
    print(f"\nValidation passed: {val.get('passed')}")
    for c in val.get("checks", []):
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['check']}: {c['detail']}")

    gr = state.get("guardrail", {})
    print(f"\nGuardrail passed: {gr.get('passed')}")
    if gr.get("ungrounded_numbers"):
        print(f"  Ungrounded numbers flagged: {gr['ungrounded_numbers']}")

    print(f"\nNeeds human review: {state.get('needs_human_review')}")
    print("\nExecutive narrative:")
    print(f"  {state.get('narrative')}")

    print("\nAudit trail:")
    for entry in state.get("audit_log", []):
        print(f"  - {entry}")
    print("\n============================\n")


def run_document(path: Path | None) -> None:
    if path is None:
        path = Path(__file__).parent / "examples" / "sample_statement.json"
    document = json.loads(path.read_text())
    graph = build_graph(LLMClient())
    state = graph.invoke({"document": document})
    _print_report(state)


def run_evaluation() -> None:
    result = run_eval(default_cases())
    print("\n=== EVALUATION ===")
    for d in result.details:
        mark = "PASS" if d["passed"] else "FAIL"
        print(f"  [{mark}] {d['case']}")
    print(f"\nScore: {result.passed}/{result.total} ({result.score:.0%})\n")
    sys.exit(0 if result.score == 1.0 else 1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--eval":
        run_evaluation()
    else:
        run_document(Path(args[0]) if args else None)
