# Interview Study Guide — Finance Insight Agent

A prep doc for talking about this project in interviews. **Read the code
alongside this** — the goal is genuine understanding, not memorized answers. If
an interviewer goes one layer deeper than this guide, you want to be able to
follow, and that only comes from having actually run and modified the code.

> How to describe the project honestly: *"A project I built to demonstrate
> agentic-AI patterns — multi-agent orchestration, guardrails against
> hallucination, and an evaluation harness — applied to a finance document
> use case."* It applies well-established patterns competently; it is not
> novel research, and you should not present it as such.

---

## 30-second summary (your opening line)

> "It's a multi-agent system that reads a financial statement, extracts the
> figures with an LLM, then **deterministically** reconciles them in code, writes
> an executive summary, and runs a guardrail that flags any number in the
> summary not backed by a validated figure. Failed checks trigger a bounded
> retry loop, and anything still failing is routed to a human. It's built with
> LangGraph and Gemini, and runs in a mock mode so it's reproducible without an
> API key."

---

## The core design principle (lead with this)

**"The LLM proposes, deterministic code verifies."**

- LLMs are good at *reading messy input* and *writing prose*, but you cannot
  trust them for arithmetic or as the final authority on a number.
- So the LLM does extraction and narration; **pure Python** does reconciliation
  and the guardrail. That split is the whole point — it's what makes the system
  safe for a regulated finance context where accuracy must be auditable.

---

## Likely questions and how to answer

### "Walk me through the architecture."
Extractor (LLM) → Validator (code) → Analyst (LLM) → Guardrail (code), wired as a
LangGraph `StateGraph`. Conditional edges route failures back to a retry node
(bounded by `MAX_RETRIES`); exhausted retries end flagged for human review. Point
to the diagram in the README.

### "Why LangGraph instead of just chaining function calls?"
LangGraph models the workflow as a graph with explicit **conditional edges and
cycles**. The retry loop is a cycle, and routing-on-validation is a conditional
edge — expressing those as graph constructs makes the control flow explicit and
inspectable rather than buried in `if`/`while`. It also gives a clean place to
add persistence/checkpointing later.

### "How do you prevent hallucinations?"
Two layers. (1) The validator never trusts the LLM's math — it recomputes
`revenue − expenses` and compares to the stated net income within a tolerance.
(2) The guardrail scans the narrative for numbers and flags any that don't trace
back (within $1) to a validated figure. Small integers (years, counts) are
allow-listed so they don't false-positive. See `src/guardrails/checks.py`.

### "What happens when something fails?"
It routes to a retry node that re-runs extraction (a cheap recovery from a bad
parse). After `MAX_RETRIES`, it stops and sets `needs_human_review = True` rather
than publishing a possibly-wrong number — the human-in-the-loop trip wire.

### "How do you know it works? / How would you test an agentic system?"
An eval harness (`src/eval/framework.py`) runs the full graph over labelled cases
and scores it. Crucially it includes a **planted-error case** — a statement with
a deliberately wrong net income — that the system *must* catch and route to
review. A score below 100% exits non-zero, so it doubles as a CI gate. Plus unit
tests on the deterministic pieces.

### "Why a mock mode?"
Reproducibility. Reviewers and CI can run the whole pipeline with zero setup and
no API key, and the *same* graph/routing runs in mock and live mode — only the
LLM call differs. It also makes tests deterministic.

### "How would you take this to production?" (know your limits honestly)
Be candid that it's a demo. Real steps: ingest real PDFs/CSVs (not hand-built
JSON); add richer validation (balance-sheet identity, period-over-period
variance); persist the audit log to a datastore for compliance; add
observability (latency, model-drift, guardrail-hit-rate metrics); handle API
errors/retries/timeouts; and human-review UI. The role's JD literally lists
observability and drift monitoring — name those as the next things you'd add.

### "What were the hard parts / trade-offs?"
- Deciding the LLM/deterministic boundary — pulling *all* trust-sensitive logic
  into code.
- The guardrail's number-matching needs a tolerance and an allow-list, or it
  false-positives on years and sentence numbers.
- Merging unrelated git histories on first push (a real thing that happened) —
  shows you can handle git, not just code.

---

## Things to actually DO before the interview

1. Run `python main.py` and `python main.py --eval` and watch the output.
2. Open `src/agents/orchestrator.py` and trace one full pass by hand.
3. **Break it on purpose:** edit `examples/sample_statement.json` to make net
   income wrong, re-run, and watch the guardrail + human-review flag fire.
4. **Extend it** (optional but powerful): add one new validation rule. Being able
   to say "I added X" is far stronger than describing code someone handed you.

---

## Honesty guardrails for yourself

- Don't claim production experience from this — it's a portfolio project.
- Don't claim the patterns are novel — they're standard and you're applying them.
- Do claim: you designed and built it, you understand every part, and you can
  extend it. That's true, and it's enough.
