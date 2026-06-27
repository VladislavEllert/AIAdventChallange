from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_cli.invariants.store import load_invariants, save_invariants, add_invariant

router = APIRouter(prefix="/invariants", tags=["invariants"])


def _as_str_list(raw: list) -> list[str]:
    """Normalize: invariants can be str or dict (legacy format)."""
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # e.g. {"Бизнес-правило": "text"}
            result.append(": ".join(f"{k} — {v}" for k, v in item.items()))
    return result


class InvariantCreate(BaseModel):
    text: str


@router.get("", response_model=list[str])
def list_invariants():
    return _as_str_list(load_invariants())


@router.post("", response_model=list[str])
def create_invariant(body: InvariantCreate):
    if not body.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    add_invariant(body.text.strip())
    return _as_str_list(load_invariants())


@router.delete("/{index}", response_model=list[str])
def remove_invariant(index: int):
    raw = load_invariants()
    if index < 0 or index >= len(raw):
        raise HTTPException(404, "Index out of range")
    del raw[index]
    save_invariants(raw)
    return _as_str_list(raw)
