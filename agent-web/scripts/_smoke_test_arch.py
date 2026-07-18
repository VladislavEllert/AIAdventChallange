"""Throwaway smoke-test file for AI-review Action (day 35.5, PR b: architecture).

Not wired into the app. Simulates a FastAPI route handler that talks to
the filesystem directly instead of going through a service/repository
layer, to verify the review Action flags architecture issues.
"""

import json

from fastapi import APIRouter

router = APIRouter()


@router.get("/items/{item_id}")
def get_item(item_id: str):
    # Route handler reaches straight into the filesystem instead of
    # delegating to a service/repository layer.
    with open(f"data/{item_id}.json") as f:
        return json.load(f)


@router.put("/items/{item_id}")
def update_item(item_id: str, payload: dict):
    # Same problem on the write path: no validation layer, no service,
    # route handler owns persistence directly.
    with open(f"data/{item_id}.json", "w") as f:
        json.dump(payload, f)
    return {"status": "ok"}
