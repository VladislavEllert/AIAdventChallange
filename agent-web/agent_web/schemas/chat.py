from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
    image_b64: str | None = None
    persona: str | None = None
    model: str | None = None         # overrides saved model for this request
    profile_name: str | None = None  # profile to inject into system prompt


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_rub: float = 0.0
    elapsed_ms: int = 0
