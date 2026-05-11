from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.resource_manager import resource_manager
import asyncio
import json

router = APIRouter()

@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            metrics = resource_manager.get_system_metrics()
            await websocket.send_text(json.dumps(metrics))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
