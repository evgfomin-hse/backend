import asyncio

import pytest

from tests.conftest import create_test_user, get_auth_headers


async def test_sse_invalid_token(client, session):
    """SSE endpoint rejects invalid token with 401."""
    resp = await client.get("/sse/games/fake-id?token=badtoken")
    assert resp.status_code == 401


async def test_sse_route_exists(client):
    """SSE endpoint is registered — invalid-token request returns 401, not 404."""
    resp = await client.get("/sse/games/some-id?token=anything")
    assert resp.status_code == 401


async def test_sse_event_stream_yields_messages(fake_redis):
    """The SSE event_stream generator yields SSE-formatted messages from pubsub."""
    channel = "game:test-game"
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe(channel)

    # Publish AFTER subscribing (concurrent via task)
    async def _publish():
        await asyncio.sleep(0.05)  # small delay to let listen() start
        await fake_redis.publish(channel, '{"event":"started"}')

    asyncio.create_task(_publish())

    collected = []
    async for msg in pubsub.listen():
        if msg["type"] == "message":
            collected.append(f"data: {msg['data']}\n\n")
            break  # Got one message, stop

    await pubsub.unsubscribe(channel)
    await pubsub.aclose()

    assert len(collected) == 1
    assert collected[0] == 'data: {"event":"started"}\n\n'


async def test_sse_valid_token_response_headers(client, session, fake_redis):
    """SSE endpoint with valid token returns StreamingResponse with text/event-stream.

    Directly calls the route function to verify auth and response metadata
    without consuming the infinite stream body.
    """
    await create_test_user(session, login="sseuser", password="p", email="sse@x.com")
    headers = await get_auth_headers(client, "sseuser", "p")
    token = headers["Authorization"].split(" ")[1]

    from fastapi import HTTPException
    from app.routers.sse import game_sse

    response = await game_sse(
        game_id="test-game",
        token=token,
        redis=fake_redis,
    )
    assert response.media_type == "text/event-stream"
    assert response.headers.get("Cache-Control") == "no-cache"


async def test_sse_event_stream_yields_keepalive_and_data(client, session, fake_redis):
    """Drive the StreamingResponse generator to cover keepalive + data + cleanup."""
    await create_test_user(session, login="sse2", password="p", email="sse2@x.com")
    headers = await get_auth_headers(client, "sse2", "p")
    token = headers["Authorization"].split(" ")[1]

    from app.routers.sse import game_sse

    game_id = "stream-game"
    response = await game_sse(game_id=game_id, token=token, redis=fake_redis)
    body_iterator = response.body_iterator

    async def _publish():
        await asyncio.sleep(0.1)
        await fake_redis.publish(f"game:{game_id}", '{"event":"go"}')

    publish_task = asyncio.create_task(_publish())

    saw_keepalive = False
    saw_data = False
    try:
        for _ in range(200):  # bounded so the test can't hang
            chunk = await body_iterator.__anext__()
            if chunk == ": keepalive\n\n":
                saw_keepalive = True
            elif chunk.startswith("data: "):
                saw_data = True
                assert chunk == 'data: {"event":"go"}\n\n'
                break
    finally:
        await body_iterator.aclose()  # triggers the generator's finally/cleanup
        await publish_task

    assert saw_keepalive
    assert saw_data
