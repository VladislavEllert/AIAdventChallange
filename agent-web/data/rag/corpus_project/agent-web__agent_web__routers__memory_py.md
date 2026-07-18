<!-- source: agent-web/agent_web/routers/memory.py | title: memory.py -->

from fastapi import APIRouter, Depends, HTTPException

from agent_web.dependencies import get_manager
from agent_web.services.agent_manager import AgentManager
from agent_web.services.settings_store import load_settings

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{session_id}")
def get_memory(session_id: str, manager: AgentManager = Depends(get_manager)):
    """Load session memory state."""
    try:
        agent = manager.get_or_create(session_id)
    except Exception as e:
        raise HTTPException(404, f"Session not found: {e}")

    m = agent.memory
    s = load_settings()
    limit = s.get("short_term_limit", 16)
    keep = s.get("keep_recent", 8)

    return {
        "session_id": session_id,
        "short_term_count": len(m.short_term),
        "short_term_limit": limit,
        "keep_recent": keep,
        "summary": m.summary or "",
        "working": m.working if isinstance(m.working, dict) else {},
        "messages": [
            {"role": msg["role"], "content": msg["content"][:200]}
            for msg in m.short_term[-6:]
        ],
    }


@router.post("/{session_id}/extract-profile")
async def extract_profile_facts(
    session_id: str,
    profile_name: str,
    manager: AgentManager = Depends(get_manager),
):
    """Extract user facts from recent messages and update profile."""
    try:
        agent = manager.get_or_create(session_id)
    except Exception as e:
        raise HTTPException(404, f"Session not found: {e}")

    from agent_cli.profile.extractor import route_fact
    from agent_cli.profile.profile import UserProfile
    from pathlib import Path
    import agent_cli.config as cfg

    profile_path = Path(cfg.PROFILES_DIR) / f"{profile_name}.md"
    if not profile_path.exists():
        raise HTTPException(404, f"Profile {profile_name!r} not found")

    # Collect recent user messages (up to last 10)
    user_msgs = [
        m["content"] for m in agent.memory.short_term
        if m.get("role") == "user"
    ][-10:]

    if not user_msgs:
        return {"updated": False, "reason": "no messages"}

    # Try to load existing profile
    try:
        profile = UserProfile.load(profile_name)
    except Exception:
        raise HTTPException(404, f"Cannot load profile {profile_name!r}")

    updates: dict[str, list[str]] = {k: [] for k in ("persona", "style", "rules", "stack", "interests")}
    for msg in user_msgs:
        try:
            layer = route_fact(msg, manager.provider, agent.model)
            updates[layer].append(msg)
        except Exception:
            pass

    changed = False
    for layer, facts in updates.items():
        if not facts:
            continue
        existing = getattr(profile, layer, "") or ""
        new_content = existing + ("\n" if existing else "") + "; ".join(facts)
        setattr(profile, layer, new_content.strip())
        changed = True

    if changed:
        profile.save()

    return {"updated": changed, "layers": {k: v for k, v in updates.items() if v}}
