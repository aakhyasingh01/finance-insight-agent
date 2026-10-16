"""LLM client wrapper around Google Gemini.

Design note:
    The client supports a ``mock`` mode so the entire agentic pipeline can run
    end-to-end without an API key. This is deliberate: it lets reviewers,
    recruiters, and CI pipelines execute the project with zero setup, while the
    same code paths run against real Gemini when ``GOOGLE_API_KEY`` is set.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """Normalized response so callers never touch provider-specific types."""
    text: str
    raw: Any = None


class LLMClient:
    """A thin, swappable wrapper over Gemini with a deterministic mock mode."""

    def __init__(self, model: str = "gemini-3.6-flash", mode: str | None = None):
        self.model = model
        # mode resolution order: explicit arg > env > default "mock"
        self.mode = (mode or os.getenv("LLM_MODE", "mock")).lower()
        self._client = None
        if self.mode != "mock":
            self._init_real_client()

    def _init_real_client(self) -> None:
        """Lazily import the real SDK so mock mode has zero heavy deps."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "langchain-google-genai is not installed. Run "
                "`pip install -r requirements.txt`, or set LLM_MODE=mock."
            ) from exc

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Add it to your .env file or set "
                "LLM_MODE=mock to run without an API key."
            )
        self._client = ChatGoogleGenerativeAI(model=self.model, temperature=0)

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResponse:
        """Return a completion for ``prompt``.

        In mock mode we return a deterministic, structured response derived from
        the prompt so downstream agents behave predictably in tests/demos.
        """
        if self.mode == "mock":
            return LLMResponse(text=self._mock_complete(prompt, system))

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        result = self._client.invoke(messages)
        content = result.content
        # Some Gemini models return content as a list of parts rather than a
        # single string; normalize to a plain string so downstream code (regex
        # guardrails, JSON parsing) always receives text.
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
            content = "".join(parts)
        return LLMResponse(text=str(content), raw=result)


    # ------------------------------------------------------------------
    # Mock implementation
    # ------------------------------------------------------------------
    def _mock_complete(self, prompt: str, system: str | None) -> str:
        """Deterministic stand-in for the LLM.

        It inspects the prompt for the task marker injected by each agent and
        returns a plausible, well-formed response. This keeps the agent graph
        exercised without network access.
        """
        if "TASK:EXTRACT" in prompt:
            # Pull any "label: number" pairs out of the document text.
            figures = dict(re.findall(r"([A-Za-z ]+?):\s*\$?([\d,]+(?:\.\d+)?)", prompt))
            cleaned = {
                k.strip().lower().replace(" ", "_"): float(v.replace(",", ""))
                for k, v in figures.items()
            }
            return json.dumps({"figures": cleaned})

        if "TASK:NARRATE" in prompt:
            return (
                "The statement reconciles cleanly. Revenue and expense figures "
                "are internally consistent, and the derived net income matches "
                "the stated total within tolerance. No anomalies were detected "
                "by the deterministic validation layer."
            )

        return "MOCK_RESPONSE"
