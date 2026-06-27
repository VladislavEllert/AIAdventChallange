from fastapi import APIRouter
from pydantic import BaseModel

from agent_web.services.settings_store import load_settings, save_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    short_term_limit: int | None = None
    keep_recent: int | None = None
    default_model: str | None = None
    auto_profile_update: bool | None = None
    theme: str | None = None


@router.get("")
def get_settings():
    return load_settings()


@router.put("")
def update_settings(body: SettingsPatch):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    return save_settings(patch)
