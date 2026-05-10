<div align="center">

# 🧬 agent-capsules

**Your AI agent makes mistakes, learns fixes, then forgets everything next session.**<br>
**This library makes the learning stick.**

[![PyPI](https://img.shields.io/pypi/v/agent-capsules)](https://pypi.org/project/agent-capsules/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## The Problem

Every AI coding agent session is a goldmine of hard-won knowledge:

- That `numpy>=2` breaks `yfinance` metadata generation
- That `git push` fails silently when email privacy is on
- That the user prefers `pytest -x` over full test runs

**But sessions end, context windows reset, and the agent starts from zero.**

Existing solutions are either cloud-dependent (Mem0, Supermemory), game-specific (Voyager), or research-only (Reflexion). None give you a **local-first, structured, universal** learning loop for real coding agents.

## The Solution

```
Session ends → Extract capsule → Accumulate → Distill into reusable rules
```

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Agent Session │     │   Capsule    │     │      Gene       │
│                 │     │              │     │                 │
│  errors hit     │────▶│  signal      │────▶│  reusable rule  │
│  fixes found    │     │  hypothesis  │     │  or skill that  │
│  user corrects  │     │  attempt     │     │  prevents the   │
│                 │     │  outcome     │     │  mistake again   │
└─────────────────┘     │  lesson      │     └─────────────────┘
                        └──────────────┘
                         (SHAO format)        (after 3+ capsules
                                               cluster on a topic)
```

## Install

```bash
pip install agent-capsules
```

## 30-Second Demo

```python
from agent_capsules import CapsuleStore, extract_capsules

messages = [
    {"role": "user", "content": "install yfinance"},
    {"role": "assistant", "content": "running pip install..."},
    {"role": "tool", "content": "ERROR: metadata generation failed for numpy>=2"},
    {"role": "assistant", "content": "numpy conflict — pinning numpy<2..."},
    {"role": "tool", "content": "Successfully installed yfinance-0.2.40"},
]

capsules = extract_capsules(messages, session_id="sess_001")
# → Capsule(signal="Encountered 1 error(s)...", tags=["pip"], confidence="low")

store = CapsuleStore()
store.append(capsules[0])  # Persisted to ~/.agent-capsules/index.jsonl
```

## Works With Any Agent

<table>
<tr>
<td width="33%">

### Hermes Agent
```bash
pip install agent-capsules
# Auto-registers via entry-point
# Zero config needed
```
Hooks into `on_session_end` automatically.

</td>
<td width="33%">

### Claude Code
```jsonc
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [{
      "command": "agent-capsules extract /tmp/session.json"
    }]
  }
}
```

</td>
<td width="33%">

### Any Agent
```python
# In your post-session hook
from agent_capsules import (
    CapsuleStore,
    extract_capsules
)

store = CapsuleStore()
caps = extract_capsules(msgs)
store.append_many(caps)
```

</td>
</tr>
</table>

## Two Extraction Modes

| Mode | Speed | Quality | Cost | Use When |
|------|-------|---------|------|----------|
| **`heuristic`** | Instant | Good | Free | Default. Detects error→fix patterns, user corrections |
| **`llm`** | ~3s | Excellent | 1 cheap LLM call | You want deeper analysis. Uses [litellm](https://github.com/BerriAI/litellm) (any provider) |

```python
# Free — pattern matching
capsules = extract_capsules(messages, extractor="heuristic")

# Better — uses LLM for analysis (requires: pip install agent-capsules[llm])
capsules = extract_capsules(messages, extractor="llm", llm_config={"model": "gpt-4o-mini"})
```

## Gene Distillation

When 3+ capsules cluster on the same topic, distill them into a **gene** — a reusable rule:

```python
from agent_capsules import CapsuleStore, GeneDistiller

store = CapsuleStore()
distiller = GeneDistiller(store, min_cluster_size=3)
genes = distiller.distill()

for gene in genes:
    print(f"{gene.name}: {gene.content}")
    # pip-pitfalls:
    #   - Always pin numpy<2 before installing yfinance
    #   - Use --no-cache-dir when pip metadata fails
    #   - Run ensurepip in fresh venvs before installing
```

Genes can output to different formats depending on your agent:

| Agent | Gene becomes... |
|-------|----------------|
| Hermes | A skill (SKILL.md) |
| Claude Code | Rules in CLAUDE.md |
| Cursor | .cursorrules entries |
| Generic | Markdown or JSONL |

## Capsule Format (SHAO)

Each capsule is one line of JSONL:

```json
{
  "session_id": "20250510_143022_a1b2c3",
  "date": "2025-05-10",
  "signal": "pip install failed with metadata generation error",
  "hypothesis": "numpy>=2 has breaking changes in build system",
  "attempt": "Pinned numpy<2, then installed yfinance",
  "outcome": "Resolved — yfinance installed successfully",
  "lesson": "Always install numpy<2 before yfinance on Python 3.11+",
  "tags": ["pip", "numpy"],
  "confidence": "high",
  "extraction": "llm"
}
```

**SHAO** = **S**ignal → **H**ypothesis → **A**ttempt → **O**utcome

Inspired by [BenjamyClaudeSkills](https://code.amazon.com/packages/BenjamyClaudeSkills)' 6-layer memory architecture.

## CLI

```bash
# Extract from a session transcript
agent-capsules extract session.json

# See what you've learned
agent-capsules stats

# Distill capsules into genes
agent-capsules distill --apply

# Export for humans
agent-capsules export --format markdown

# Export as rules for Claude
agent-capsules export --format claude >> CLAUDE.md
```

## Storage

Everything is local files. No database, no server, no cloud.

```
~/.agent-capsules/
├── index.jsonl          # All capsules (append-only)
├── consumed.jsonl       # Capsules absorbed into genes
└── config.yaml          # Optional configuration
```

## Configuration

```yaml
# ~/.agent-capsules/config.yaml (optional — sane defaults work without it)
store:
  path: ~/.agent-capsules/index.jsonl

extraction:
  extractor: heuristic
  min_tool_calls: 5         # Skip trivial sessions
  skip_patterns:
    - "^(what|how|why) "    # Skip pure Q&A

distillation:
  min_cluster_size: 3
  output: skills            # skills | rules | markdown

llm:
  model: gpt-4o-mini        # Any litellm-supported model
```

## How It Compares

| Project | Auto-extract | Session trigger | Structured format | Local-first | Universal |
|---------|:-:|:-:|:-:|:-:|:-:|
| **agent-capsules** | ✅ | ✅ | ✅ SHAO | ✅ | ✅ |
| [Reflexion](https://github.com/noahshinn/reflexion) | ✅ | ✅ | ❌ free-text | ✅ | ❌ task-loop only |
| [Voyager](https://github.com/MineDojo/Voyager) | ✅ | ✅ | ✅ code | ✅ | ❌ Minecraft |
| [Mem0](https://github.com/mem0ai/mem0) | ✅ | ❌ continuous | ❌ key-value | ❌ cloud | ⚠️ generic |
| [Letta/MemGPT](https://github.com/cpacker/MemGPT) | ⚠️ | ❌ | ❌ | ❌ | ⚠️ |
| [Roo Code](https://github.com/RooVetGit/Roo-Code) | ⚠️ state | ❌ | ⚠️ markdown | ✅ | ❌ Cline only |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│               agent-capsules (core)                 │
├──────────────┬───────────────┬──────────────────────┤
│  Extractors  │     Store     │      Distiller       │
│  ──────────  │  ──────────── │  ──────────────────  │
│  heuristic   │  JSONL        │  cluster by tag      │
│  llm         │  append-only  │  propose genes       │
│  (custom)    │  session dedup│  mark consumed       │
└──────┬───────┴───────┬───────┴──────────┬───────────┘
       │               │                  │
┌──────┴───────┐  ┌────┴─────┐  ┌─────────┴──────────┐
│   Adapters   │  │   CLI    │  │   Gene Outputs     │
│  ──────────  │  │          │  │  ────────────────  │
│  hermes      │  │ extract  │  │  hermes skills     │
│  claude-code │  │ stats    │  │  cursor rules      │
│  cursor      │  │ distill  │  │  CLAUDE.md         │
│  generic     │  │ export   │  │  markdown / JSONL  │
└──────────────┘  └──────────┘  └────────────────────┘
```

## Roadmap

- [x] Core library (store, heuristic extractor, LLM extractor)
- [x] Hermes Agent adapter (entry-point plugin)
- [x] CLI (extract, stats, distill, export)
- [ ] Claude Code adapter (hooks integration)
- [ ] Cursor adapter (.cursorrules writer)
- [ ] Gene → CLAUDE.md / .cursorrules / SKILL.md formatters
- [ ] `agent-capsules watch` — daemon mode for continuous extraction
- [ ] Web UI for browsing capsules (optional, local)
- [ ] PyPI publish

## Contributing

```bash
git clone https://github.com/cixuuz/agent-capsules
cd agent-capsules
pip install -e ".[all]"
```

PRs welcome. Especially interested in:
- New adapters for other agents (Aider, Continue, Cody, etc.)
- Better heuristic patterns for non-English sessions
- Gene output formatters for different agent rule systems

## License

MIT

---

<div align="center">

*Built because agents shouldn't keep making the same mistake twice.*

</div>
