# agent-capsules

A universal learning extraction library for AI coding agents. Automatically captures lessons from agent sessions and distills them into reusable knowledge.

## What It Does

```
Session → Capsule (structured lesson) → Gene (distilled skill/rule)
```

Every time an AI agent session ends, `agent-capsules` extracts **what went wrong, what was tried, and what was learned** into a structured capsule (SHAO format: Signal → Hypothesis → Attempt → Outcome). Over time, capsules accumulate and get distilled into reusable rules/skills ("genes").

## Format

Capsules are stored as append-only JSONL — one line per lesson:

```json
{"session_id": "abc123", "date": "2025-05-10", "signal": "pip install failed with metadata error", "hypothesis": "numpy>=2 incompatible", "attempt": "pinned numpy<2 before install", "outcome": "resolved", "lesson": "Always pin numpy<2 before yfinance", "tags": ["pip", "numpy"], "confidence": "high"}
```

## Installation

```bash
pip install agent-capsules
```

## Quick Start

```python
from agent_capsules import CapsuleStore, extract_capsules

# Initialize store (default: ~/.agent-capsules/index.jsonl)
store = CapsuleStore()

# Extract from a conversation
messages = [
    {"role": "user", "content": "install yfinance"},
    {"role": "assistant", "content": "running pip install..."},
    {"role": "tool", "content": "ERROR: metadata generation failed"},
    {"role": "assistant", "content": "numpy version conflict, pinning numpy<2..."},
    {"role": "tool", "content": "Successfully installed yfinance-0.2.40"},
]

capsules = extract_capsules(messages)
for c in capsules:
    store.append(c)
```

## Integrations

### Hermes Agent (plugin)

```bash
pip install agent-capsules[hermes]
```

Registers as a Hermes plugin automatically via entry-point. No config needed.

### Claude Code (hooks)

```bash
# In your .claude/hooks.json
{
  "session_end": "agent-capsules extract --format claude"
}
```

### Cursor / Windsurf / Generic

```python
# In your post-session script
from agent_capsules import CapsuleStore, extract_capsules

store = CapsuleStore(path="./capsules.jsonl")
capsules = extract_capsules(messages, extractor="heuristic")
store.append_many(capsules)
```

## Extractors

| Extractor | Speed | Quality | Cost |
|-----------|-------|---------|------|
| `heuristic` | Instant | Medium | Free |
| `llm` | ~5s | High | 1 LLM call/session |

```python
# Heuristic (default): regex pattern matching, zero LLM cost
capsules = extract_capsules(messages, extractor="heuristic")

# LLM: uses your configured provider for deeper analysis
capsules = extract_capsules(messages, extractor="llm", llm_config={...})
```

## Gene Distillation

When enough capsules accumulate on a topic, distill them into a "gene" — a reusable rule or skill:

```python
from agent_capsules import GeneDistiller

distiller = GeneDistiller(store)
genes = distiller.distill(min_cluster_size=3)

for gene in genes:
    print(f"Proposed skill: {gene.name}")
    print(f"  Based on {len(gene.source_capsules)} capsules")
    print(f"  Rule: {gene.content}")
```

## CLI

```bash
# Extract from a session transcript
agent-capsules extract session.json

# Show capsule stats
agent-capsules stats

# Run distillation
agent-capsules distill

# Export as markdown (for humans who want to review)
agent-capsules export --format markdown
```

## Configuration

```yaml
# ~/.agent-capsules/config.yaml
store:
  path: ~/.agent-capsules/index.jsonl
  
extraction:
  extractor: heuristic        # or "llm"
  min_tool_calls: 5           # skip simple sessions
  skip_patterns:              # session titles to ignore
    - "^(what|how|why) "      # skip Q&A sessions

distillation:
  min_cluster_size: 3         # capsules needed to form a gene
  output: skills              # "skills", "rules", "markdown"

llm:
  provider: openai            # or anthropic, bedrock, google
  model: gpt-4o-mini          # cheap model for extraction
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              agent-capsules (core)               │
├─────────────┬──────────────┬────────────────────┤
│  Extractors │    Store     │    Distiller       │
│  ─────────  │  ─────────  │  ─────────────     │
│  heuristic  │  JSONL       │  cluster by tag    │
│  llm        │  append-only │  propose genes     │
│  (custom)   │  dedup       │  mark consumed     │
└──────┬──────┴──────┬───────┴────────┬───────────┘
       │             │                │
┌──────┴──────┐ ┌────┴────┐ ┌────────┴────────┐
│  Adapters   │ │   CLI   │ │  Gene Outputs   │
│  ─────────  │ │         │ │  ─────────────  │
│  hermes     │ │ extract │ │  hermes skills  │
│  claude-code│ │ stats   │ │  cursor rules   │
│  cursor     │ │ distill │ │  claude CLAUDE.md│
│  generic    │ │ export  │ │  markdown       │
└─────────────┘ └─────────┘ └─────────────────┘
```

## License

MIT
