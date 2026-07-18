<!-- source: agent-cli/agent_cli/core/sessions.py | title: sessions.py -->

"""
SessionStore — персистентное хранилище именованных сессий чата.

SQLite (stdlib sqlite3) без внешних ORM.

Схема:
  sessions     — id, name, created_at, updated_at, profile_name, model, summary
  messages     — id, session_id, role, content, created_at
  session_stats — session_id, prompt_tokens, completion_tokens, cost_rub, calls
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from agent_cli.config import DEFAULT_MODEL, SESSIONS_DB
from agent_cli.core.memory import Memory
from agent_cli.llm.provider import SessionStats


# ── DDL ──────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL DEFAULT '',
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL,
    profile_name TEXT NOT NULL DEFAULT '',
    model        TEXT NOT NULL,
    summary      TEXT NOT NULL DEFAULT '',
    owner        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS session_stats (
    session_id        TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost_rub          REAL    NOT NULL DEFAULT 0.0,
    calls             INTEGER NOT NULL DEFAULT 0
);
"""


# ── dataclass для метаданных сессии ──────────────────────────────────────────

@dataclass
class SessionMeta:
    session_id: str
    name: str
    created_at: float
    updated_at: float
    profile_name: str
    model: str
    msg_count: int = 0
    cost_rub: float = 0.0
    owner: str = ""

    @property
    def display_name(self) -> str:
        return self.name or self.session_id


# ── SessionStore ─────────────────────────────────────────────────────────────

class SessionStore:
    def __init__(self, db_path: str = SESSIONS_DB) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA foreign_keys = ON")
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.executescript(_DDL)
            # Migration for pre-existing DBs created before the `owner` column
            # (light per-nickname session isolation) was added.
            cols = {row["name"] for row in con.execute("PRAGMA table_info(sessions)")}
            if "owner" not in cols:
                con.execute("ALTER TABLE sessions ADD COLUMN owner TEXT NOT NULL DEFAULT ''")

    # ── создание / получение ─────────────────────────────────────────────────

    def create_session(
        self,
        name: str = "",
        model: str = DEFAULT_MODEL,
        profile_name: str = "",
        owner: str = "",
    ) -> str:
        """Создаёт новую сессию, возвращает session_id."""
        session_id = uuid.uuid4().hex[:8]
        now = time.time()
        with self._connect() as con:
            con.execute(
                "INSERT INTO sessions (id, name, created_at, updated_at, profile_name, model, summary, owner) "
                "VALUES (?, ?, ?, ?, ?, ?, '', ?)",
                (session_id, name, now, now, profile_name, model, owner),
            )
            con.execute(
                "INSERT INTO session_stats (session_id) VALUES (?)",
                (session_id,),
            )
        return session_id

    def last_session_id(self) -> str | None:
        """ID сессии с последним updated_at."""
        with self._connect() as con:
            row = con.execute(
                "SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        return row["id"] if row else None

    def get_meta(self, session_id: str) -> SessionMeta | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT s.*, "
                "  (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS msg_count, "
                "  COALESCE(st.cost_rub, 0.0) AS cost_rub "
                "FROM sessions s "
                "LEFT JOIN session_stats st ON st.session_id = s.id "
                "WHERE s.id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return SessionMeta(
            session_id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            profile_name=row["profile_name"],
            model=row["model"],
            msg_count=row["msg_count"],
            cost_rub=row["cost_rub"],
            owner=row["owner"],
        )

    def list_sessions(self, owner: str | None = None) -> list[SessionMeta]:
        """
        Сессии, отсортированные по updated_at DESC.
        owner=None -> все сессии (сохранена старая behaviour для внутренних вызовов).
        owner="<nickname>" -> только сессии этого owner + "ничьи" (owner='') —
        старые сессии до миграции остаются видны всем, не пропадают молча.
        """
        query = (
            "SELECT s.*, "
            "  (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS msg_count, "
            "  COALESCE(st.cost_rub, 0.0) AS cost_rub "
            "FROM sessions s "
            "LEFT JOIN session_stats st ON st.session_id = s.id "
        )
        params: tuple = ()
        if owner is not None:
            query += "WHERE s.owner = ? OR s.owner = '' "
            params = (owner,)
        query += "ORDER BY s.updated_at DESC"
        with self._connect() as con:
            rows = con.execute(query, params).fetchall()
        return [
            SessionMeta(
                session_id=r["id"],
                name=r["name"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                profile_name=r["profile_name"],
                model=r["model"],
                msg_count=r["msg_count"],
                cost_rub=r["cost_rub"],
                owner=r["owner"],
            )
            for r in rows
        ]

    # ── сохранение / загрузка ─────────────────────────────────────────────────

    def save_session(
        self,
        session_id: str,
        memory: Memory,
        stats: SessionStats,
        model: str = DEFAULT_MODEL,
        profile_name: str = "",
    ) -> None:
        """
        Сохраняет текущее состояние сессии:
        - перезаписывает все messages
        - обновляет summary, stats, updated_at
        """
        now = time.time()
        with self._connect() as con:
            # Обновляем метаданные сессии
            con.execute(
                "UPDATE sessions SET updated_at=?, summary=?, model=?, profile_name=? WHERE id=?",
                (now, memory.summary, model, profile_name, session_id),
            )
            # Перезаписываем сообщения (удалить + вставить)
            con.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            for msg in memory.short_term:
                con.execute(
                    "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (session_id, msg["role"], msg["content"], now),
                )
            # Обновляем статистику
            con.execute(
                "INSERT INTO session_stats (session_id, prompt_tokens, completion_tokens, cost_rub, calls) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "  prompt_tokens=excluded.prompt_tokens, "
                "  completion_tokens=excluded.completion_tokens, "
                "  cost_rub=excluded.cost_rub, "
                "  calls=excluded.calls",
                (
                    session_id,
                    stats.prompt_tokens,
                    stats.completion_tokens,
                    stats.cost_rub,
                    stats.calls,
                ),
            )

    def load_session(self, session_id: str) -> tuple[Memory, SessionStats, str]:
        """
        Загружает сессию из БД.
        Возвращает (memory, stats, model).
        """
        with self._connect() as con:
            sess_row = con.execute(
                "SELECT * FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            if not sess_row:
                raise KeyError(f"Сессия не найдена: {session_id}")

            msg_rows = con.execute(
                "SELECT role, content FROM messages WHERE session_id=? ORDER BY id",
                (session_id,),
            ).fetchall()

            stats_row = con.execute(
                "SELECT * FROM session_stats WHERE session_id=?", (session_id,)
            ).fetchone()

        memory = Memory()
        memory.summary = sess_row["summary"] or ""
        for r in msg_rows:
            memory.add_message(r["role"], r["content"])

        stats = SessionStats()
        if stats_row:
            stats.prompt_tokens = stats_row["prompt_tokens"]
            stats.completion_tokens = stats_row["completion_tokens"]
            stats.cost_rub = stats_row["cost_rub"]
            stats.calls = stats_row["calls"]

        return memory, stats, sess_row["model"]

    # ── управление ───────────────────────────────────────────────────────────

    def rename_session(self, session_id: str, new_name: str) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE sessions SET name=?, updated_at=? WHERE id=?",
                (new_name, time.time(), session_id),
            )

    def delete_session(self, session_id: str) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def find_by_name(self, name: str) -> SessionMeta | None:
        """Ищет сессию по имени (точное совпадение или prefix по id)."""
        sessions = self.list_sessions()
        # Сначала по имени
        for s in sessions:
            if s.name.lower() == name.lower():
                return s
        # Потом по id-prefix
        for s in sessions:
            if s.session_id.startswith(name):
                return s
        return None

    def auto_name(
        self,
        session_id: str,
        provider,  # LLMProvider
        model: str,
    ) -> str:
        """
        Генерирует 2-3 слова заголовок по первым сообщениям сессии через LLM.
        Сохраняет имя в БД. Возвращает имя.
        """
        with self._connect() as con:
            rows = con.execute(
                "SELECT content FROM messages WHERE session_id=? AND role='user' ORDER BY id LIMIT 3",
                (session_id,),
            ).fetchall()
        if not rows:
            return session_id

        snippet = " ".join(r["content"][:200] for r in rows)
        prompt = (
            f"Диалог начинается с:\n{snippet}\n\n"
            "Придумай название этой сессии: 2-3 слова на русском, строчными буквами, "
            "без знаков препинания, только слова через дефис. Только название, ничего больше."
        )
        try:
            name = provider.chat(
                [{"role": "user", "content": prompt}],
                model,
                max_tokens=20,
            ).strip().replace(" ", "-").lower()[:40]
        except Exception:
            name = session_id

        self.rename_session(session_id, name)
        return name
