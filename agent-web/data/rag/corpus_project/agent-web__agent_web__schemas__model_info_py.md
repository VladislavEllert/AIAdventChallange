<!-- source: agent-web/agent_web/schemas/model_info.py | title: model_info.py -->

from pydantic import BaseModel


class ModelInfo(BaseModel):
    model_id: str
    input_price: float
    output_price: float
    type: str = "text"
