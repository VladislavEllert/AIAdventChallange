<!-- source: agent-web/agent_web/routers/agents.py | title: agents.py -->

import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_cli.config import SESSIONS_DB

router = APIRouter(prefix="/agents", tags=["agents"])
_DB = str(SESSIONS_DB)


def _conn():
    con = sqlite3.connect(_DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT NOT NULL DEFAULT '🤖',
            system_prompt TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL
        )
    """)
    return con


class AgentCreate(BaseModel):
    name: str
    emoji: str = "🤖"
    system_prompt: str = ""


class AgentUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    system_prompt: str | None = None


class AgentOut(BaseModel):
    id: str
    name: str
    emoji: str
    system_prompt: str
    created_at: float


@router.get("", response_model=list[AgentOut])
def list_agents():
    with _conn() as con:
        rows = con.execute(
            "SELECT id, name, emoji, system_prompt, created_at FROM agents ORDER BY created_at"
        ).fetchall()
    return [AgentOut(id=r[0], name=r[1], emoji=r[2], system_prompt=r[3], created_at=r[4]) for r in rows]


@router.post("", response_model=AgentOut)
def create_agent(body: AgentCreate):
    aid = uuid.uuid4().hex[:8]
    now = time.time()
    with _conn() as con:
        con.execute(
            "INSERT INTO agents (id, name, emoji, system_prompt, created_at) VALUES (?,?,?,?,?)",
            (aid, body.name.strip(), body.emoji, body.system_prompt, now),
        )
    return AgentOut(id=aid, name=body.name.strip(), emoji=body.emoji, system_prompt=body.system_prompt, created_at=now)


@router.put("/{agent_id}", response_model=AgentOut)
def update_agent(agent_id: str, body: AgentUpdate):
    with _conn() as con:
        row = con.execute(
            "SELECT id, name, emoji, system_prompt, created_at FROM agents WHERE id=?", (agent_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Agent not found")
        name = body.name.strip() if body.name is not None else row[1]
        emoji = body.emoji if body.emoji is not None else row[2]
        sp = body.system_prompt if body.system_prompt is not None else row[3]
        con.execute("UPDATE agents SET name=?, emoji=?, system_prompt=? WHERE id=?", (name, emoji, sp, agent_id))
    return AgentOut(id=agent_id, name=name, emoji=emoji, system_prompt=sp, created_at=row[4])


@router.delete("/{agent_id}")
def delete_agent(agent_id: str):
    with _conn() as con:
        row = con.execute("SELECT id FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Agent not found")
        con.execute("DELETE FROM agents WHERE id=?", (agent_id,))
    return {"ok": True}
