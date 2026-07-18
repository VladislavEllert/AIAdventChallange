<!-- source: agent-web/agent_web/app.py | title: app.py -->

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agent_web.routers import chat, sessions, models, agents, memory, invariants, profiles, tasks, settings, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Agent Web", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(models.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")
    app.include_router(memory.router, prefix="/api")
    app.include_router(invariants.router, prefix="/api")
    app.include_router(profiles.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # Serve built React app
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            return FileResponse(static_dir / "index.html")

    return app
