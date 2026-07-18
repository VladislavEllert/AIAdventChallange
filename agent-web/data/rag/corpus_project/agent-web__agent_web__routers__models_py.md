<!-- source: agent-web/agent_web/routers/models.py | title: models.py -->

from fastapi import APIRouter

from agent_cli.config import _MODEL_PRICING, DEFAULT_MODEL
from agent_web.schemas.model_info import ModelInfo

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelInfo])
def list_models():
    return [
        ModelInfo(model_id=mid, input_price=p["input"], output_price=p["output"], type=p.get("type", "text"))
        for mid, p in _MODEL_PRICING.items()
    ]


@router.get("/models/default")
def default_model():
    return {"model": DEFAULT_MODEL}
