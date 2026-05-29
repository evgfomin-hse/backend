import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.redis import get_redis
from app.core.security import decode_access_token

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/games/{game_id}")
async def game_websocket(
    game_id: str,
    websocket: WebSocket,
    token: str = Query(...),
    redis: aioredis.Redis = Depends(get_redis),
):
    try:
        decode_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    pubsub = redis.pubsub()
    channel = f"game:{game_id}"
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
