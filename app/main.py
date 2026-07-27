"""
Signal Gate API entry point.

Folders:
  app/core/     auth, supabase, alpaca helpers
  app/agent/    AI agent + CLI (python -m app.agent.cli)
  app/routers/  HTTP routes (/chat, /paper, /price, /candles)
  app/schemas/  request/response models
  app/exits/    stop-loss / take-profit store + monitor
  MCP/          tool scripts the agent calls

Local:
  uvicorn app.main:app --reload --port 8000

Production (Render):
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  Serves frontend/dist SPA when present (single-service deploy).
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # LangSmith + API keys before routers/agent load

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.exits.monitor import monitor_loop
from app.routers.chat import router as chat_router
from app.routers.paper import router as paper_router
from app.routers.price import router as price_router
from app.routers.settings import router as settings_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("signal_gate")

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def _cors_origins() -> list[str]:
    """Local Vite ports + optional FRONTEND_URL / CORS_ORIGINS (comma-separated)."""
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    raw = os.getenv("CORS_ORIGINS") or os.getenv("FRONTEND_URL") or ""
    extra = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for origin in defaults + extra:
        if origin not in seen:
            seen.add(origin)
            out.append(origin)
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the SL/TP price monitor with the API; stop it on shutdown."""
    # Ensure exit-rules dir exists (ephemeral on free Render; see README).
    (Path(__file__).resolve().parents[1] / "data").mkdir(parents=True, exist_ok=True)

    stop = asyncio.Event()
    task = asyncio.create_task(monitor_loop(stop), name="exit-monitor")
    logger.info("exit monitor task started (production-safe lifespan)")
    try:
        yield
    finally:
        stop.set()
        try:
            await asyncio.wait_for(task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()


app = FastAPI(title="Signal Gate", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    # Vite bumps ports when several `npm run dev` are running
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers (registered before SPA catch-all)
app.include_router(price_router)
app.include_router(paper_router)
app.include_router(chat_router)
app.include_router(settings_router)


@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    """Render health check — keep this path (not `/`) so SPA can own `/`."""
    return {"status": "ok"}


@app.get("/api", status_code=status.HTTP_200_OK)
def api_root():
    return {"message": "Signal Gate API"}


def _spa_enabled() -> bool:
    return FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file()


if _spa_enabled():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def spa_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """Serve built static files or index.html for client-side routes."""
        # Never treat health/api as SPA (also registered above; belt-and-suspenders)
        if full_path in {"health", "api"}:
            return JSONResponse({"status": "ok"} if full_path == "health" else {"message": "Signal Gate API"})

        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

    logger.info("Serving SPA from %s", FRONTEND_DIST)
else:

    @app.get("/", status_code=status.HTTP_200_OK)
    def root():
        return {"message": "Signal Gate API"}
