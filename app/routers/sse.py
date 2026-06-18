import asyncio
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.core.audit import current_actor, log_event
from app.core.redis import get_redis
from app.core.security import decode_access_token

router = APIRouter(tags=["realtime"])


@router.get("/sse/games/{game_id}")
async def game_sse(
    game_id: str,
    token: str = Query(...),
    actor: str = Query("spectator"),
    redis: aioredis.Redis = Depends(get_redis),
):
    try:
        decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    current_actor.set(actor)
    log_event("sse", f"SSE connect game:{game_id}", "client connected", actor=actor)

    async def event_stream() -> AsyncGenerator[str, None]:
        pubsub = redis.pubsub()
        channel = f"game:{game_id}"
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=15
                )
                if message is None:
                    yield ": keepalive\n\n"
                    continue
                if message["type"] != "message":
                    continue
                log_event(
                    "sse", f"SSE push game:{game_id}", message["data"], actor=actor
                )
                yield f"data: {message['data']}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
