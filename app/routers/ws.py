import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.audit import current_actor, log_event
from app.core.redis import get_redis
from app.core.security import decode_access_token

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/games/{game_id}")
async def game_websocket(
    game_id: str,
    websocket: WebSocket,
    token: str = Query(...),
    actor: str = Query("spectator"),
    redis: aioredis.Redis = Depends(get_redis),
):
    try:
        decode_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    current_actor.set(actor)
    await websocket.accept()
    log_event("ws", f"WS connect game:{game_id}", "client connected", actor=actor)
    pubsub = redis.pubsub()
    channel = f"game:{game_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=15
            )
            if message is None:
                await websocket.send_text('{"type": "ping"}')
                continue
            if message["type"] != "message":
                continue
            log_event("ws", f"WS push game:{game_id}", message["data"], actor=actor)
            await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
