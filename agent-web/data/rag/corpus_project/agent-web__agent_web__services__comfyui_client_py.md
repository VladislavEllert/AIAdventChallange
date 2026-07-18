<!-- source: agent-web/agent_web/services/comfyui_client.py | title: comfyui_client.py -->

"""
ComfyUI image generation client (day 27/29).

Not an LLMProvider — ComfyUI's protocol is graph-JSON submit + poll, not
OpenAI-compatible chat. `generate()` is a sync generator yielding progress/image
events so it can be consumed directly from the sync SSE generator in chat.py.

Deliberate simplification vs. the original plan: poll GET /history instead of
listening on the ComfyUI websocket. A polling loop gives the same end-user
value (a progress bar) without mixing asyncio into chat.py's sync generator —
simpler and more robust for this use case, at the cost of coarser progress
granularity (time-estimate based, not real step-by-step %).
"""
import base64
import json
import time
import uuid
from pathlib import Path
from typing import Iterator

import httpx

WORKFLOW_PATH = Path(__file__).parent / "comfyui_workflows" / "sdxl.json"

# Node ids in sdxl.json (confirmed against the exported API-format workflow)
_NODE_POSITIVE = "6"
_NODE_NEGATIVE = "7"
_NODE_SAMPLER = "3"
_NODE_LATENT = "5"

# Rough estimate for progress-bar pacing, from the Windows session's cold-start
# measurement (1024x1024, 20 steps, --lowvram): ~44s. Not a guarantee.
_ESTIMATED_SECONDS = 45.0


def _load_workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def build_prompt(
    prompt: str,
    negative: str = "",
    seed: int | None = None,
    steps: int = 20,
    cfg: float = 8.0,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    wf = _load_workflow()
    wf[_NODE_POSITIVE]["inputs"]["text"] = prompt
    if negative:
        wf[_NODE_NEGATIVE]["inputs"]["text"] = negative
    wf[_NODE_SAMPLER]["inputs"]["seed"] = seed if seed is not None else int(time.time() * 1000) % (2**31)
    wf[_NODE_SAMPLER]["inputs"]["steps"] = steps
    wf[_NODE_SAMPLER]["inputs"]["cfg"] = cfg
    wf[_NODE_LATENT]["inputs"]["width"] = width
    wf[_NODE_LATENT]["inputs"]["height"] = height
    return wf


def generate(
    base_url: str,
    prompt: str,
    negative: str = "",
    seed: int | None = None,
    steps: int = 20,
    cfg: float = 8.0,
    width: int = 1024,
    height: int = 1024,
    poll_interval: float = 1.0,
    timeout: float = 240.0,
) -> Iterator[dict]:
    """Yields {"type": "progress", "pct": int} then either
    {"type": "image", "data_b64": str} or {"type": "error", "message": str}."""
    client_id = str(uuid.uuid4())
    wf = build_prompt(prompt, negative, seed, steps, cfg, width, height)

    # trust_env=False: bypass a system SOCKS proxy (VPN software) that otherwise
    # breaks this local ComfyUI call on Windows with "Unknown scheme for proxy URL".
    with httpx.Client(timeout=10.0, trust_env=False) as http:
        try:
            resp = http.post(f"{base_url}/prompt", json={"prompt": wf, "client_id": client_id})
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]
        except Exception as e:
            yield {"type": "error", "message": f"ComfyUI недоступен: {e}"}
            return

        t0 = time.time()
        while True:
            elapsed = time.time() - t0
            if elapsed > timeout:
                yield {"type": "error", "message": f"Таймаут генерации ComfyUI ({timeout:.0f}s)"}
                return

            try:
                hist_resp = http.get(f"{base_url}/history/{prompt_id}")
                hist_resp.raise_for_status()
                history = hist_resp.json()
            except Exception:
                history = {}

            entry = history.get(prompt_id)
            if entry and entry.get("outputs"):
                image_info = None
                for node_out in entry["outputs"].values():
                    images = node_out.get("images") or []
                    if images:
                        image_info = images[0]
                        break

                if image_info:
                    yield {"type": "progress", "pct": 100}
                    try:
                        img_resp = http.get(
                            f"{base_url}/view",
                            params={
                                "filename": image_info["filename"],
                                "subfolder": image_info.get("subfolder", ""),
                                "type": image_info.get("type", "output"),
                            },
                        )
                        img_resp.raise_for_status()
                    except Exception as e:
                        yield {"type": "error", "message": f"Не удалось получить картинку: {e}"}
                        return
                    b64 = base64.b64encode(img_resp.content).decode()
                    yield {"type": "image", "data_b64": b64}
                    return

            pct = min(95, int(elapsed / _ESTIMATED_SECONDS * 100))
            yield {"type": "progress", "pct": pct}
            time.sleep(poll_interval)
