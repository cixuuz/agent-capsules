"""Gene distillation — cluster capsules and propose reusable rules."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from agent_capsules.models import Capsule, Gene
from agent_capsules.store import CapsuleStore


class GeneDistiller:
    """Distill capsules into reusable genes (skills/rules)."""

    def __init__(self, store: CapsuleStore, min_cluster_size: int = 3):
        self.store = store
        self.min_cluster_size = min_cluster_size

    def distill(self) -> list[Gene]:
        """Find clusters of unconsumed capsules and propose genes."""
        capsules = self.store.load_unconsumed()
        if len(capsules) < self.min_cluster_size:
            return []

        # Cluster by tag
        by_tag: dict[str, list[Capsule]] = defaultdict(list)
        for cap in capsules:
            for tag in cap.tags:
                by_tag[tag].append(cap)

        genes: list[Gene] = []
        consumed_sessions: set[str] = set()

        for tag, caps in by_tag.items():
            if len(caps) < self.min_cluster_size:
                continue

            # Skip capsules already consumed in this run
            available = [c for c in caps if c.session_id not in consumed_sessions]
            if len(available) < self.min_cluster_size:
                continue

            # Build a gene from the cluster
            lessons = [c.lesson or c.signal for c in available if c.lesson or c.signal]
            if not lessons:
                continue

            gene = Gene(
                name=f"{tag}-pitfalls",
                content="\n".join(f"- {lesson}" for lesson in lessons),
                tags=[tag],
                source_capsules=[c.session_id for c in available],
                created=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                confidence="medium" if any(c.confidence == "high" for c in available) else "low",
            )
            genes.append(gene)
            consumed_sessions.update(c.session_id for c in available)

        return genes

    def apply(self, genes: list[Gene]) -> None:
        """Mark source capsules as consumed after genes are created."""
        for gene in genes:
            self.store.mark_consumed(gene.source_capsules, gene.name)
