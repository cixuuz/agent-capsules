"""Heuristic capsule extractor — zero LLM cost, regex-based."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from agent_capsules.models import Capsule


# Error signal patterns
_ERROR_KEYWORDS = [
    "Error", "Traceback", "FAILED", "failed", "exit_code\": 1",
    "permission denied", "not found", "timeout", "ConnectionError",
    "ModuleNotFoundError", "ImportError", "FileNotFoundError",
    "command not found", "ENOENT", "EACCES", "404", "500",
]

# User correction patterns (English + Chinese)
_CORRECTION_PATTERNS = [
    re.compile(r"\b(no,?\s|not that|wrong|actually|instead|should be|don't|stop)", re.I),
    re.compile(r"(不对|不是|别这样|换一个|不要|错了|重来|改一下|不行)"),
]

# Tag detection keywords
_TAG_KEYWORDS: Dict[str, List[str]] = {
    "git": ["git ", "commit", "branch", "merge", "clone", "push", "pull", "rebase"],
    "pip": ["pip ", "install", "package", "venv", "requirements"],
    "docker": ["docker", "container", "image", "compose"],
    "npm": ["npm ", "node_modules", "package.json", "yarn"],
    "config": ["config", "yaml", "toml", "settings", ".env"],
    "auth": ["token", "credential", "auth", "login", "permission"],
    "network": ["curl", "http", "api", "request", "timeout", "dns"],
    "database": ["sql", "sqlite", "postgres", "mysql", "migration"],
    "testing": ["test", "assert", "pytest", "jest", "spec"],
    "deploy": ["deploy", "ci/cd", "pipeline", "build", "release"],
    "llm": ["openai", "anthropic", "claude", "gpt", "bedrock", "model"],
    "memory": ["memory", "context", "token limit", "truncat"],
}


class HeuristicExtractor:
    """Extract capsules using pattern matching — no LLM needed."""

    def extract(
        self, messages: List[Dict[str, Any]], session_id: str = ""
    ) -> List[Capsule]:
        """Analyze messages for error→fix patterns and user corrections."""
        if not messages:
            return []

        errors: List[str] = []
        corrections: List[str] = []
        title = ""
        all_text_parts: List[str] = []

        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = self._get_text(msg)
            if not content:
                continue

            all_text_parts.append(content[:500])

            # Title from first user message
            if role == "user" and not title:
                title = content[:120]

            # Detect errors
            if any(kw in content for kw in _ERROR_KEYWORDS):
                errors.append(content[:250])

            # Detect user corrections
            if role == "user" and i > 0:
                if any(p.search(content) for p in _CORRECTION_PATTERNS):
                    corrections.append(content[:250])

        # Only create capsule if there's a learning signal
        if not errors and not corrections:
            return []

        # Build signal
        if errors:
            signal = f"Encountered {len(errors)} error(s). First: {errors[0][:150]}"
        else:
            signal = f"User corrected: {corrections[0][:150]}"

        # Detect tags
        all_text = " ".join(all_text_parts).lower()
        tags = [
            tag for tag, keywords in _TAG_KEYWORDS.items()
            if any(kw in all_text for kw in keywords)
        ]

        capsule = Capsule.now(
            session_id=session_id or "unknown",
            signal=signal,
            title=title,
            tags=tags[:5],
            error_count=len(errors),
            correction_count=len(corrections),
            confidence="low",
            extraction="heuristic",
        )
        return [capsule]

    def _get_text(self, msg: Dict[str, Any]) -> str:
        """Extract text from a message (handles string or list content)."""
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return " ".join(parts)
        return ""
