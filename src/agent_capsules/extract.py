"""Extraction orchestrator — routes to the right extractor."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_capsules.models import Capsule


def extract_capsules(
    messages: List[Dict[str, Any]],
    *,
    session_id: str = "",
    extractor: str = "heuristic",
    llm_config: Optional[Dict[str, Any]] = None,
) -> List[Capsule]:
    """Extract capsules from a conversation.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        session_id: Session identifier for dedup.
        extractor: "heuristic" (free, fast) or "llm" (better quality, costs tokens).
        llm_config: Config for LLM extractor (provider, model, api_key, etc.)
    
    Returns:
        List of Capsule objects (usually 0 or 1 per session).
    """
    if extractor == "heuristic":
        from agent_capsules.extractors.heuristic import HeuristicExtractor
        ext = HeuristicExtractor()
    elif extractor == "llm":
        from agent_capsules.extractors.llm import LLMExtractor
        ext = LLMExtractor(config=llm_config or {})
    else:
        raise ValueError(f"Unknown extractor: {extractor}. Use 'heuristic' or 'llm'.")

    return ext.extract(messages, session_id=session_id)
