from fastapi import APIRouter

from app.api import servers, tasks

api_router = APIRouter()
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
