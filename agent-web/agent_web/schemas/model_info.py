from pydantic import BaseModel


class ModelInfo(BaseModel):
    model_id: str
    input_price: float
    output_price: float
