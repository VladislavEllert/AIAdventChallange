<!-- source: agent-web/agent_web/routers/profiles.py | title: profiles.py -->

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_cli.profile.profile import UserProfile
from agent_cli.config import PROFILES_DIR

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[str])
def list_profiles():
    return UserProfile.list_all()


@router.get("/{name}")
def get_profile(name: str):
    path = Path(PROFILES_DIR) / f"{name}.md"
    if not path.exists():
        raise HTTPException(404, f"Profile '{name}' not found")
    return {"name": name, "content": path.read_text(encoding="utf-8")}


class ProfileUpdate(BaseModel):
    content: str


@router.put("/{name}")
def update_profile(name: str, body: ProfileUpdate):
    path = Path(PROFILES_DIR) / f"{name}.md"
    if not path.exists():
        raise HTTPException(404, f"Profile '{name}' not found")
    path.write_text(body.content, encoding="utf-8")
    return {"name": name, "saved": True}
