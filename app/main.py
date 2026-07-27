"""
Signal Gate API entry point.

Folders:
  app/core/     auth, supabase, alpaca helpers
  app/agent/    AI agent + CLI (python -m app.agent.cli)
  app/routers/  HTTP routes (/chat, /paper, /price, /candles)
  app/schemas/  request/response models
  app/exits/    stop-loss / take-profit store + monitor
  MCP/          tool scripts the agent calls

Run with:
  uvicorn app.main:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # LangSmith + API keys before routers/agent load

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.exits.monitor import monitor_loop
from app.routers.chat import router as chat_router
from app.routers.paper import router as paper_router
from app.routers.price import router as price_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the SL/TP price monitor with the API; stop it on shutdown."""
    stop = asyncio.Event()
    task = asyncio.create_task(monitor_loop(stop), name="exit-monitor")
    try:
        yield
    finally:
        stop.set()
        try:
            await asyncio.wait_for(task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()


app = FastAPI(title="Signal Gate", lifespan=lifespan)

# Allow the React frontend to call this API.
# Vite bumps ports (5173, 5174, …) when several `npm run dev` are running,
# so match any localhost / 127.0.0.1 port — not just 5173/5174.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(price_router)
app.include_router(paper_router)
app.include_router(chat_router)


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "Signal Gate API"}
