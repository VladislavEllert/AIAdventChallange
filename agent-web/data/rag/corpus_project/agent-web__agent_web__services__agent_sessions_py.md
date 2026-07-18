<!-- source: agent-web/agent_web/services/agent_sessions.py | title: agent_sessions.py -->

"""
Lightweight mapping: agent_id → [session_ids].
Stored in same SQLite file as agents (SESSIONS_DB).
Sessions not in mapping belong to '__default__' agent.
"""
import sqlite3
from agent_cli.config import SESSIONS_DB

_DB = str(SESSIONS_DB)


def _conn():
    con = sqlite3.connect(_DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""
        CREATE TABLE IF NOT EXISTS agent_sessions (
            session_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL DEFAULT '__default__'
        )
    """)
    return con


def link(session_id: str, agent_id: str) -> None:
    """Link session to agent. Overwrites existing mapping."""
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO agent_sessions (session_id, agent_id) VALUES (?,?)",
            (session_id, agent_id),
        )


def unlink(session_id: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM agent_sessions WHERE session_id=?", (session_id,))


def get_sessions_for_agent(agent_id: str, all_session_ids: list[str]) -> list[str]:
    """
    Returns session_ids belonging to agent.
    Default agent (__default__): sessions explicitly mapped to it + sessions not in mapping at all.
    Custom agent: only sessions explicitly mapped to it.
    """
    with _conn() as con:
        rows = con.execute(
            "SELECT session_id, agent_id FROM agent_sessions"
        ).fetchall()

    mapped: dict[str, str] = {r[0]: r[1] for r in rows}

    if agent_id == "__default__":
        return [sid for sid in all_session_ids if mapped.get(sid, "__default__") == "__default__"]
    else:
        return [sid for sid in all_session_ids if mapped.get(sid) == agent_id]
