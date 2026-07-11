"""
Day 29 — tiny metrics agent for the Windows LLM box.

Runs next to Ollama/ComfyUI. Exposes GET /metrics -> JSON with CPU/RAM/GPU/VRAM
and the models currently loaded in Ollama, so the Mac-side app can show a live
HUD. Deliberately dependency-light (stdlib http.server + psutil + nvidia-smi
via subprocess) so it doesn't need the full agent-web venv on Windows.

Usage (on the Windows box, next to Ollama):
    pip install psutil
    python metrics_server.py            # listens on 0.0.0.0:11435

Requires: an NVIDIA GPU with `nvidia-smi` on PATH (RTX 4060 in this setup).
If nvidia-smi or Ollama aren't reachable, those fields come back null instead
of crashing the whole response — one down component shouldn't blank the HUD.
"""
import json
import subprocess
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import psutil
except ImportError:
    psutil = None

PORT = 11435
OLLAMA_URL = "http://localhost:11434"


def _cpu_ram() -> dict:
    if psutil is None:
        return {"cpu_pct": None, "ram_used_gb": None, "ram_total_gb": None}
    vm = psutil.virtual_memory()
    return {
        "cpu_pct": psutil.cpu_percent(interval=0.3),
        "ram_used_gb": round(vm.used / 1e9, 2),
        "ram_total_gb": round(vm.total / 1e9, 2),
    }


def _gpu() -> dict:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            timeout=5,
        ).decode().strip()
        gpu_pct, vram_used, vram_total, temp = [x.strip() for x in out.split(",")]
        return {
            "gpu_pct": float(gpu_pct),
            "vram_used_gb": round(float(vram_used) / 1024, 2),
            "vram_total_gb": round(float(vram_total) / 1024, 2),
            "gpu_temp_c": float(temp),
        }
    except Exception:
        return {"gpu_pct": None, "vram_used_gb": None, "vram_total_gb": None, "gpu_temp_c": None}


def _ollama_models() -> list:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=3) as resp:
            data = json.loads(resp.read())
        return [
            {"name": m["name"], "size_vram_gb": round(m.get("size_vram", 0) / 1e9, 2)}
            for m in data.get("models", [])
        ]
    except Exception:
        return []


def collect_metrics() -> dict:
    return {**_cpu_ram(), **_gpu(), "ollama_models": _ollama_models()}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(collect_metrics()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # quiet — this runs unattended next to Ollama/ComfyUI


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"metrics_server listening on 0.0.0.0:{PORT} — GET /metrics")
    server.serve_forever()
