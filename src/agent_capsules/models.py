"""Data models for capsules and genes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from typing import List, Optional


@dataclass
class Capsule:
    """A structured learning capsule (SHAO format)."""

    session_id: str
    date: str  # ISO date string YYYY-MM-DD
    signal: str  # What was observed
    tags: List[str] = field(default_factory=list)
    hypothesis: str = ""  # Suspected cause
    attempt: str = ""  # What was tried
    outcome: str = ""  # What happened
    lesson: str = ""  # One-sentence takeaway
    confidence: str = "low"  # high, medium, low
    extraction: str = "heuristic"  # heuristic, llm, manual
    title: str = ""
    error_count: int = 0
    correction_count: int = 0
    skill_absorbed: Optional[str] = None  # Set when consumed by distillation

    def to_json(self) -> str:
        d = {k: v for k, v in asdict(self).items() if v}
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "Capsule":
        data = json.loads(line)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def now(cls, session_id: str, **kwargs) -> "Capsule":
        return cls(
            session_id=session_id,
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            **kwargs,
        )


@dataclass
class Gene:
    """A distilled skill/rule derived from multiple capsules."""

    name: str
    content: str  # The rule/skill text
    tags: List[str] = field(default_factory=list)
    source_capsules: List[str] = field(default_factory=list)  # session_ids
    created: str = ""
    confidence: str = "medium"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "Gene":
        data = json.loads(line)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
