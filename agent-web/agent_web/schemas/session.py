from pydantic import BaseModel


class SessionCreate(BaseModel):
    name: str = ""
    agent_id: str | None = None
    owner: str = ""


class SessionRename(BaseModel):
    name: str


class SessionOut(BaseModel):
    session_id: str
    name: str
    display_name: str
    created_at: float
    updated_at: float
    profile_name: str
    model: str
    msg_count: int = 0
    cost_rub: float = 0.0
    owner: str = ""


class MessageOut(BaseModel):
    role: str
    content: str


class SessionDetail(BaseModel):
    session_id: str
    name: str
    display_name: str
    model: str
    profile_name: str
    summary: str
    messages: list[MessageOut]
    cost_rub: float = 0.0
