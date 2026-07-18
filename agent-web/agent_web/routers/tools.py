"""Day 34: HTTP surface for the local file-agent tools + confirm flow.

GET  /api/tools           — list available tools + JSON schemas (debug/UI use).
POST /api/tools/confirm   — resolve a pending DANGEROUS tool call (Allow/Deny),
                             consumed by chat.ts's ConfirmToolModal.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from agent_web.services.tools import confirm, registry

router = APIRouter(tags=["tools"])


class ConfirmToolRequest(BaseModel):
    call_id: str
    approved: bool


@router.get("/tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "danger_level": t.danger_level,
            }
            for t in (registry.get(n) for n in registry.registered_names())
            if t is not None
        ]
    }


@router.post("/tools/confirm")
async def confirm_tool(req: ConfirmToolRequest):
    ok = confirm.resolve(req.call_id, req.approved)
    return {"ok": ok}
