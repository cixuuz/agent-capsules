"""Hermes Agent adapter — registers as a plugin via entry-point."""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

from agent_capsules.extract import extract_capsules
from agent_capsules.store import CapsuleStore

logger = logging.getLogger(__name__)

MIN_TOOL_CALLS = 5
STATE_DB = Path.home() / ".hermes" / "state.db"


def _get_session_tool_count(session_id: str) -> int:
    """Check tool call count from Hermes state.db."""
    if not STATE_DB.exists():
        return 0
    try:
        conn = sqlite3.connect(str(STATE_DB), timeout=3)
        row = conn.execute(
            "SELECT tool_call_count FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        logger.debug("agent-capsules hermes: db query failed: %s", e)
        return 0


def _get_messages(session_id: str) -> list[dict[str, Any]]:
    """Read messages from Hermes state.db."""
    if not STATE_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(STATE_DB), timeout=3)
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        conn.close()
        return [{"role": r[0], "content": r[1]} for r in rows if r[1]]
    except Exception as e:
        logger.debug("agent-capsules hermes: message read failed: %s", e)
        return []


def _do_extract(session_id: str) -> None:
    """Run extraction in background thread."""
    messages = _get_messages(session_id)
    if not messages:
        return

    store = CapsuleStore()
    capsules = extract_capsules(messages, session_id=session_id, extractor="heuristic")
    for c in capsules:
        if store.append(c):
            logger.info("agent-capsules: extracted capsule for session %s", session_id)


def _on_session_end(session_id: str = "", **kwargs) -> None:
    """Hermes on_session_end hook."""
    if not session_id or session_id.startswith("cron_"):
        return

    tool_count = _get_session_tool_count(session_id)
    if tool_count < MIN_TOOL_CALLS:
        return

    store = CapsuleStore()
    if store.has(session_id):
        return

    # Non-blocking extraction
    threading.Thread(target=_do_extract, args=(session_id,), daemon=True).start()


def register(ctx) -> None:
    """Hermes plugin registration entry point."""
    ctx.register_hook("on_session_end", _on_session_end)
    logger.info("agent-capsules plugin registered (hermes adapter)")
