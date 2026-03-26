import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Query, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.api.websocket_tasks import run_task_event_websocket
from app.config import get_settings


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    structlog.get_logger("api").info("starting")
    yield
    structlog.get_logger("api").info("stopping")


settings = get_settings()
app = FastAPI(title="DevOps AI Agent", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.websocket("/ws/tasks/{task_id}")
async def ws_tasks_root(
    websocket: WebSocket,
    task_id: int,
    token: str | None = Query(default=None),
) -> None:
    """Qabul qilish tekshiruvi: `wscat -c "ws://host/ws/tasks/1?token=JWT"`."""
    await run_task_event_websocket(websocket, task_id, token)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health_root() -> dict[str, str]:
    """Minimal probe (Docker / LB)."""
    return {"status": "ok"}
