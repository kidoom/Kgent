"""Central API router — aggregates all HTTP + SSE route modules.

Route map (all prefixed with /api in main.py):

  POST   /sessions                          create or confirm session id
  POST   /sessions/{session_id}/messages    send message, start run
  POST   /runs/{run_id}/permission          allow / deny tool
  POST   /runs/{run_id}/cancel              cancel run
  GET    /sessions/{session_id}/events      SSE AgentEvent stream

App-level (main.py):

  GET    /health                            health + runtime status
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.events import router as events_router
from app.api.sessions import router as sessions_router

api_router = APIRouter()

api_router.include_router(sessions_router)
api_router.include_router(events_router)

__all__ = ["api_router"]
