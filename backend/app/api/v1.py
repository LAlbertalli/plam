from fastapi import APIRouter
from app.api.endpoints import models, metrics, agents, proxies, chat

api_router = APIRouter()

api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(proxies.router, prefix="/proxies", tags=["proxies"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
