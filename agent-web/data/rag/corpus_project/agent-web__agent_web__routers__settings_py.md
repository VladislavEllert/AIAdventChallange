<!-- source: agent-web/agent_web/routers/settings.py | title: settings.py -->

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
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    num_ctx: int | None = None
    image_steps: int | None = None
    image_cfg: float | None = None
    image_seed: int | None = None
    image_width: int | None = None
    image_height: int | None = None
    # image_seed needs an explicit "clear to random" — None from Pydantic is
    # indistinguishable from "field omitted", so a bool flag does the clearing.
    image_seed_random: bool | None = None


@router.get("")
def get_settings():
    return load_settings()


@router.put("")
def update_settings(body: SettingsPatch):
    patch = {k: v for k, v in body.model_dump().items()
             if v is not None and k != "image_seed_random"}
    if body.image_seed_random:
        patch["image_seed"] = None
    return save_settings(patch)
