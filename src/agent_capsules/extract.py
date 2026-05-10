"""Extraction orchestrator — routes to the right extractor."""

from __future__ import annotations

from typing import Any

from agent_capsules.models import Capsule


def extract_capsules(
    messages: list[dict[str, Any]],
    *,
    session_id: str = "",
    extractor: str = "heuristic",
    llm_config: dict[str, Any] | None = None,
) -> list[Capsule]:
    """Extract capsules from a conversation.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        session_id: Session identifier for dedup.
        extractor: "heuristic" (free, fast) or "llm" (better quality, costs tokens).
        llm_config: Config for LLM extractor (provider, model, api_key, etc.)

    Returns:
        List of Capsule objects (usually 0 or 1 per session).
    """
    match extractor:
        case "heuristic":
            from agent_capsules.extractors.heuristic import HeuristicExtractor
            ext = HeuristicExtractor()
        case "llm":
            from agent_capsules.extractors.llm import LLMExtractor
            ext = LLMExtractor(config=llm_config or {})
        case _:
            raise ValueError(f"Unknown extractor: {extractor!r}. Use 'heuristic' or 'llm'.")

    return ext.extract(messages, session_id=session_id)
