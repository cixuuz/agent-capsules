"""CLI for agent-capsules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_capsules.extract import extract_capsules
from agent_capsules.store import CapsuleStore
from agent_capsules.distill import GeneDistiller


def cmd_extract(args):
    """Extract capsules from a session transcript file."""
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    data = json.loads(path.read_text())

    # Support both raw message list and {messages: [...]} format
    if isinstance(data, list):
        messages = data
    elif isinstance(data, dict) and "messages" in data:
        messages = data["messages"]
    else:
        print("Expected a JSON array of messages or {\"messages\": [...]}", file=sys.stderr)
        return 1

    session_id = data.get("session_id", path.stem) if isinstance(data, dict) else path.stem
    extractor = args.extractor or "heuristic"

    capsules = extract_capsules(messages, session_id=session_id, extractor=extractor)

    if not capsules:
        print("No learning signals found in this session.")
        return 0

    store = CapsuleStore(path=Path(args.store) if args.store else None)
    added = store.append_many(capsules)
    for c in capsules:
        print(c.to_json())
    print(f"\n{added} capsule(s) added to store.", file=sys.stderr)
    return 0


def cmd_stats(args):
    """Show capsule statistics."""
    store = CapsuleStore(path=Path(args.store) if args.store else None)
    capsules = store.load_all()

    if not capsules:
        print("No capsules yet.")
        return 0

    from collections import Counter
    tags = Counter()
    confidence = Counter()
    extraction = Counter()
    for c in capsules:
        for t in c.tags:
            tags[t] += 1
        confidence[c.confidence] += 1
        extraction[c.extraction] += 1

    unconsumed = sum(1 for c in capsules if not c.skill_absorbed)

    print(f"Total capsules: {len(capsules)}")
    print(f"Unconsumed: {unconsumed}")
    print(f"\nBy confidence: {dict(confidence)}")
    print(f"By extraction: {dict(extraction)}")
    print(f"\nTop tags:")
    for tag, count in tags.most_common(10):
        print(f"  {tag}: {count}")
    return 0


def cmd_distill(args):
    """Run gene distillation."""
    store = CapsuleStore(path=Path(args.store) if args.store else None)
    distiller = GeneDistiller(store, min_cluster_size=args.min_cluster)
    genes = distiller.distill()

    if not genes:
        print("Not enough capsules to distill yet.")
        return 0

    print(f"Found {len(genes)} potential gene(s):\n")
    for gene in genes:
        print(f"--- {gene.name} ({len(gene.source_capsules)} capsules) ---")
        print(gene.content)
        print()

    if args.apply:
        distiller.apply(genes)
        print(f"Marked {sum(len(g.source_capsules) for g in genes)} capsules as consumed.")

    # Output genes as JSONL
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a") as f:
            for gene in genes:
                f.write(gene.to_json() + "\n")
        print(f"Genes written to {out}")

    return 0


def cmd_export(args):
    """Export capsules in various formats."""
    store = CapsuleStore(path=Path(args.store) if args.store else None)
    capsules = store.load_all()

    if not capsules:
        print("No capsules to export.")
        return 0

    fmt = args.format or "jsonl"

    if fmt == "jsonl":
        for c in capsules:
            print(c.to_json())
    elif fmt == "markdown":
        print("# Learning Capsules\n")
        for c in capsules:
            print(f"## [{c.date}] {c.title or c.session_id}")
            if c.signal:
                print(f"- **Signal:** {c.signal}")
            if c.hypothesis:
                print(f"- **Hypothesis:** {c.hypothesis}")
            if c.attempt:
                print(f"- **Attempt:** {c.attempt}")
            if c.outcome:
                print(f"- **Outcome:** {c.outcome}")
            if c.lesson:
                print(f"- **Lesson:** {c.lesson}")
            if c.tags:
                print(f"- **Tags:** {', '.join(c.tags)}")
            print()
    elif fmt == "claude":
        # Output as CLAUDE.md rules
        print("# Learned Rules\n")
        for c in capsules:
            if c.lesson:
                print(f"- {c.lesson}")
            elif c.signal:
                print(f"- Avoid: {c.signal}")
    else:
        print(f"Unknown format: {fmt}. Use: jsonl, markdown, claude", file=sys.stderr)
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="agent-capsules",
        description="Universal learning extraction for AI coding agents",
    )
    parser.add_argument("--store", help="Path to capsule store (default: ~/.agent-capsules/index.jsonl)")

    sub = parser.add_subparsers(dest="command")

    # extract
    p_extract = sub.add_parser("extract", help="Extract capsules from a session file")
    p_extract.add_argument("file", help="JSON file with session messages")
    p_extract.add_argument("--extractor", choices=["heuristic", "llm"], default="heuristic")

    # stats
    sub.add_parser("stats", help="Show capsule statistics")

    # distill
    p_distill = sub.add_parser("distill", help="Run gene distillation")
    p_distill.add_argument("--min-cluster", type=int, default=3)
    p_distill.add_argument("--apply", action="store_true", help="Mark capsules as consumed")
    p_distill.add_argument("--output", help="Output file for genes (JSONL)")

    # export
    p_export = sub.add_parser("export", help="Export capsules")
    p_export.add_argument("--format", choices=["jsonl", "markdown", "claude"], default="jsonl")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    cmd_map = {
        "extract": cmd_extract,
        "stats": cmd_stats,
        "distill": cmd_distill,
        "export": cmd_export,
    }
    return cmd_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
