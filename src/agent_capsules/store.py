"""Capsule store — append-only JSONL with deduplication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Set

from agent_capsules.models import Capsule


DEFAULT_STORE_PATH = Path.home() / ".agent-capsules" / "index.jsonl"


class CapsuleStore:
    """Append-only JSONL capsule store with session dedup."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_STORE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._session_ids: Optional[Set[str]] = None

    @property
    def session_ids(self) -> Set[str]:
        """Lazily load known session IDs for dedup."""
        if self._session_ids is None:
            self._session_ids = set()
            if self.path.exists():
                for line in self.path.read_text().strip().split("\n"):
                    if line:
                        try:
                            self._session_ids.add(json.loads(line)["session_id"])
                        except (json.JSONDecodeError, KeyError):
                            pass
        return self._session_ids

    def has(self, session_id: str) -> bool:
        """Check if a capsule already exists for this session."""
        return session_id in self.session_ids

    def append(self, capsule: Capsule) -> bool:
        """Append a capsule. Returns False if already exists (dedup)."""
        if self.has(capsule.session_id):
            return False
        with self.path.open("a") as f:
            f.write(capsule.to_json() + "\n")
        self.session_ids.add(capsule.session_id)
        return True

    def append_many(self, capsules: List[Capsule]) -> int:
        """Append multiple capsules. Returns count of new ones added."""
        added = 0
        for c in capsules:
            if self.append(c):
                added += 1
        return added

    def load_all(self) -> List[Capsule]:
        """Load all capsules."""
        if not self.path.exists():
            return []
        capsules = []
        for line in self.path.read_text().strip().split("\n"):
            if line:
                try:
                    capsules.append(Capsule.from_json(line))
                except Exception:
                    pass
        return capsules

    def load_unconsumed(self) -> List[Capsule]:
        """Load capsules not yet absorbed into a gene."""
        return [c for c in self.load_all() if not c.skill_absorbed]

    def mark_consumed(self, session_ids: List[str], gene_name: str) -> None:
        """Mark capsules as consumed by rewriting the store.
        
        Note: This rewrites the full file. For large stores, consider
        using a separate consumed.jsonl index instead.
        """
        if not self.path.exists():
            return
        lines = self.path.read_text().strip().split("\n")
        new_lines = []
        for line in lines:
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("session_id") in session_ids:
                    data["skill_absorbed"] = gene_name
                new_lines.append(json.dumps(data, ensure_ascii=False))
            except Exception:
                new_lines.append(line)
        self.path.write_text("\n".join(new_lines) + "\n" if new_lines else "")

    def count(self) -> int:
        """Total capsule count."""
        if not self.path.exists():
            return 0
        return sum(1 for line in self.path.read_text().strip().split("\n") if line)
