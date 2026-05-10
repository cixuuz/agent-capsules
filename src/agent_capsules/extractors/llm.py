"""LLM-powered capsule extractor — higher quality, costs tokens."""

from __future__ import annotations

import json
from typing import Any

from agent_capsules.models import Capsule


_EXTRACTION_PROMPT = """\
Analyze this AI agent session and extract a learning capsule if one exists.

A learning capsule captures: what went wrong or was discovered, what was tried, and what was learned.

Return JSON (or null if nothing worth capturing):
```json
{{
  "signal": "what was observed (1-2 sentences)",
  "hypothesis": "suspected cause",
  "attempt": "what was tried",
  "outcome": "what happened",
  "lesson": "one-sentence reusable takeaway",
  "tags": ["tag1", "tag2"],
  "confidence": "high|medium|low"
}}
```

Rules:
- Only extract if there's a genuine, non-obvious lesson
- Skip simple Q&A, straightforward tasks with no issues
- "lesson" should be actionable — something useful for future sessions
- Tags: lowercase general categories (git, pip, docker, config, auth, network, testing, deploy, llm, etc.)
- confidence: high = verified fix, medium = worked but uncertain, low = partial

Session transcript:
{transcript}"""


class LLMExtractor:
    """Extract capsules using an LLM for deeper analysis."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def extract(
        self, messages: list[dict[str, Any]], session_id: str = ""
    ) -> list[Capsule]:
        """Use LLM to analyze session and extract capsule."""
        transcript_parts = []
        for msg in messages[-40:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if content:
                transcript_parts.append(f"[{role}] {content[:500]}")

        transcript = "\n".join(transcript_parts)
        if not transcript.strip():
            return []

        prompt = _EXTRACTION_PROMPT.format(transcript=transcript)

        try:
            response = self._call_llm(prompt)
        except Exception:
            return []

        # Parse response
        try:
            text = response
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            data = json.loads(text.strip())
            if not data:
                return []

            return [Capsule.now(
                session_id=session_id or "unknown",
                signal=data.get("signal", ""),
                hypothesis=data.get("hypothesis", ""),
                attempt=data.get("attempt", ""),
                outcome=data.get("outcome", ""),
                lesson=data.get("lesson", ""),
                tags=data.get("tags", []),
                confidence=data.get("confidence", "medium"),
                extraction="llm",
            )]
        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    def _call_llm(self, prompt: str) -> str:
        """Call LLM via litellm (supports all providers)."""
        try:
            import litellm
        except ImportError:
            raise ImportError(
                "LLM extractor requires litellm. Install with: "
                "pip install agent-capsules[llm]"
            )

        model = self.config.get("model", "gpt-4o-mini")
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            api_key=self.config.get("api_key"),
            api_base=self.config.get("api_base"),
        )
        return response.choices[0].message.content or ""
