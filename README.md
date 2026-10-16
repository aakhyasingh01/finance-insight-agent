# Finance Insight Agent — a self-correcting multi-agent system for financial documents

A multi-agent AI system that reads a financial statement, extracts the figures,
**deterministically reconciles** them, generates an executive narrative, and runs
a **hallucination guardrail** before any output reaches a human. Built with
**LangGraph** and **Google Gemini**.

It is designed around a principle that matters in regulated finance: **the LLM
proposes, deterministic code verifies.** Numbers are never trusted just because a
model produced them.

---

## Why this design

Financial workflows demand accuracy and auditability — a model that confidently
reports a wrong number is worse than no model at all. This project demonstrates a
pattern for using LLMs in that setting safely:

| Concern | How this system addresses it |
|---|---|
| **Hallucinated numbers** | A guardrail cross-checks every number in the narrative against validated figures and flags anything ungrounded. |
| **Arithmetic trust** | Reconciliation is done in **pure Python**, not by the LLM — it is deterministic and auditable. |
| **Silent failure** | Failed checks route to a **human-in-the-loop** review flag instead of auto-publishing. |
| **Self-correction** | Validation/guardrail failures route back for a bounded number of **retries** before escalating. |
| **Regression safety** | An **evaluation harness** scores the pipeline on labelled cases, including a planted error it must catch. |

---

## Architecture

```
          ┌───────────┐     ┌────────────┐     ┌───────────┐     ┌────────────┐
  doc ──► │ Extractor │ ──► │ Validator  │ ──► │  Analyst  │ ──► │ Guardrail  │ ──► report
          │  (LLM)    │     │ (pure code)│     │   (LLM)   │     │ (pure code)│
          └───────────┘     └─────┬──────┘     └───────────┘     └─────┬──────┘
                                  │ fail                               │ fail
                                  └──────────── retry (bounded) ◄──────┘
                                                 │ exhausted
                                                 ▼
                                        human-in-the-loop review
```

- **Extractor agent (LLM):** pulls labelled figures out of the document as structured JSON.
- **Validator agent (deterministic):** completeness, reconciliation (`revenue − expenses = net income`), and sign checks.
- **Analyst agent (LLM):** writes a concise executive summary grounded in validated figures.
- **Guardrail (deterministic):** flags any number in the narrative that does not trace back to a validated figure.
- **Orchestrator (LangGraph):** conditional routing + bounded self-correcting retry loop.

---

## Quickstart

Runs with **zero setup** in mock mode (no API key, no network):

```bash
git clone https://github.com/aakhyasingh01/finance-insight-agent.git
cd finance-insight-agent
python main.py            # runs the bundled sample statement
python main.py --eval     # runs the evaluation harness
```

Run the tests:

```bash
pip install -r requirements.txt   # optional; tests run without extra deps
python -m pytest -q
```

### Using real Gemini

1. Get a free API key at <https://aistudio.google.com/apikey>.
2. `cp .env.example .env` and set `GOOGLE_API_KEY` and `LLM_MODE=live`.
3. `pip install -r requirements.txt`
4. `python main.py`

> **Mock mode** is the default so the project is reproducible for reviewers and
> CI. The *same* agent graph and routing run in both modes — only the LLM calls
> differ — so behavior you see in mock mode mirrors the live structure.

---

## Project layout

```
finance-insight-agent/
├── main.py                     # CLI entry point
├── requirements.txt
├── .env.example
├── src/
│   ├── state.py                # typed, auditable shared state
│   ├── llm/client.py           # Gemini wrapper + deterministic mock mode
│   ├── agents/
│   │   ├── extractor.py        # LLM extraction
│   │   ├── validator.py        # deterministic reconciliation
│   │   ├── analyst.py          # LLM narrative
│   │   └── orchestrator.py     # LangGraph workflow + retry loop
│   ├── guardrails/checks.py    # hallucination guardrail
│   └── eval/framework.py       # evaluation harness
├── examples/sample_statement.json
└── tests/test_validator.py
```

---

## What the evaluation checks

`python main.py --eval` runs two labelled cases:

1. **clean_statement** — must pass validation and require no human review.
2. **planted_reconciliation_error** — a deliberately wrong `net income`; the
   system must fail validation and route to human review.

A score below 100% exits non-zero, so this doubles as a CI gate.

---

## Possible extensions

- PDF/CSV ingestion before the extractor stage.
- More validation rules (balance-sheet identity, period-over-period variance).
- Persisting the audit log to a store for compliance review.
- Swapping Gemini for another provider via the `LLMClient` interface.

---

## License

MIT — see `LICENSE`.
