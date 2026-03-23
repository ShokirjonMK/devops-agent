from fastapi import APIRouter

from app.api import auth_router, credentials_router, health_api, servers, tasks, websocket_tasks

api_router = APIRouter()
api_router.include_router(health_api.router)
api_router.include_router(auth_router.router)
api_router.include_router(credentials_router.router)
api_router.include_router(websocket_tasks.router)
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
