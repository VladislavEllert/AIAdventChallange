from fastapi import APIRouter, Depends, HTTPException, Query

from agent_web.dependencies import get_session_store
from agent_web.services import agent_sessions
from agent_cli.core.sessions import SessionStore
from agent_web.schemas.session import (
    SessionCreate,
    SessionRename,
    SessionOut,
    SessionDetail,
    MessageOut,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _meta_to_out(m) -> SessionOut:
    return SessionOut(
        session_id=m.session_id,
        name=m.name,
        display_name=m.display_name,
        created_at=m.created_at,
        updated_at=m.updated_at,
        profile_name=m.profile_name,
        model=m.model,
        msg_count=m.msg_count,
        cost_rub=round(m.cost_rub, 6),
        owner=m.owner,
    )


@router.get("", response_model=list[SessionOut])
def list_sessions(
    agent_id: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    store: SessionStore = Depends(get_session_store),
):
    # owner filters to that nickname's sessions + legacy ownerless ones (light
    # isolation, no auth — see SessionStore.list_sessions docstring).
    all_meta = store.list_sessions(owner=owner)
    if agent_id is not None:
        all_ids = [m.session_id for m in all_meta]
        allowed = set(agent_sessions.get_sessions_for_agent(agent_id, all_ids))
        all_meta = [m for m in all_meta if m.session_id in allowed]
    return [_meta_to_out(m) for m in all_meta]


@router.post("", response_model=SessionOut)
def create_session(body: SessionCreate, store: SessionStore = Depends(get_session_store)):
    sid = store.create_session(name=body.name, owner=body.owner)
    # Link to agent (default if not specified)
    agent_sessions.link(sid, body.agent_id or "__default__")
    meta = store.get_meta(sid)
    return _meta_to_out(meta)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, store: SessionStore = Depends(get_session_store)):
    meta = store.get_meta(session_id)
    if not meta:
        raise HTTPException(404, "Session not found")
    try:
        memory, stats, model = store.load_session(session_id)
    except KeyError:
        raise HTTPException(404, "Session not found")

    return SessionDetail(
        session_id=meta.session_id,
        name=meta.name,
        display_name=meta.display_name,
        model=model,
        profile_name=meta.profile_name,
        summary=memory.summary,
        messages=[MessageOut(role=m["role"], content=m["content"]) for m in memory.get_messages()],
        cost_rub=round(meta.cost_rub, 6),
    )


@router.put("/{session_id}")
def rename_session(session_id: str, body: SessionRename, store: SessionStore = Depends(get_session_store)):
    meta = store.get_meta(session_id)
    if not meta:
        raise HTTPException(404, "Session not found")
    store.rename_session(session_id, body.name)
    return {"ok": True}


@router.delete("/{session_id}")
def delete_session(session_id: str, store: SessionStore = Depends(get_session_store)):
    meta = store.get_meta(session_id)
    if not meta:
        raise HTTPException(404, "Session not found")
    store.delete_session(session_id)
    agent_sessions.unlink(session_id)
    return {"ok": True}
