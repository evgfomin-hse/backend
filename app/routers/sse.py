import asyncio
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.core.redis import get_redis
from app.core.security import decode_access_token

router = APIRouter(tags=["realtime"])


@router.get("/sse/games/{game_id}")
async def game_sse(
    game_id: str,
    token: str = Query(...),
    redis: aioredis.Redis = Depends(get_redis),
):
    try:
        decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    async def event_stream() -> AsyncGenerator[str, None]:
        pubsub = redis.pubsub()
        channel = f"game:{game_id}"
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
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
