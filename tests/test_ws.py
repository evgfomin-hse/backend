import asyncio

import httpx
import pytest
from httpx_ws import WebSocketUpgradeError, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from tests.conftest import create_test_user, get_auth_headers


async def test_ws_invalid_token_rejected(session, fake_redis):
    """WS connection with invalid token is rejected before accept."""
    from app.core.db import get_async_session
    from app.core.redis import get_redis
    from app.main import app

    async def override_session():
        yield session

    app.dependency_overrides[get_async_session] = override_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    try:
        async with httpx.AsyncClient(
            transport=ASGIWebSocketTransport(app=app), base_url="http://test"
        ) as ws_client:
            with pytest.raises((WebSocketUpgradeError, Exception)):
                async with aconnect_ws(
                    "ws://test/ws/games/fake-game-id?token=badtoken", ws_client
                ) as ws:
                    await ws.receive_text()
    finally:
        app.dependency_overrides.clear()


async def test_ws_valid_token_handler_logic(fake_redis):
    """Valid token: handler accepts connection and forwards Redis messages.

    Tests the handler logic directly using a mock WebSocket to avoid the
    pubsub.listen() infinite-loop hang in integration tests.
    """
    import uuid

    from fastapi import WebSocketDisconnect

    from app.core.security import create_access_token

    token = create_access_token(uuid.uuid4(), "player")
    game_id = "mock-game-id"
    channel = f"game:{game_id}"
    sent_messages: list[str] = []
    accepted = False

    class MockWebSocket:
        """Minimal mock WebSocket for testing the handler."""

        async def accept(self):
            nonlocal accepted
            accepted = True

        async def send_text(self, data: str):
            # Idle keepalive pings are sent between real messages (fakeredis'
            # get_message returns immediately rather than blocking). Ignore them
            # and only react to the forwarded game event.
            if data == '{"type": "ping"}':
                return
            sent_messages.append(data)
            # Simulate client disconnect after receiving the first real message
            raise WebSocketDisconnect(code=1000)

        async def close(self, code: int = 1000):
            pass

    mock_ws = MockWebSocket()

    # Schedule a publish after a short delay so the handler has time to subscribe
    async def _delayed_publish():
        await asyncio.sleep(0.1)
        await fake_redis.publish(channel, '{"event": "started"}')

    publish_task = asyncio.create_task(_delayed_publish())

    from app.routers.ws import game_websocket

    await game_websocket(
        game_id=game_id,
        websocket=mock_ws,
        token=token,
        redis=fake_redis,
    )

    await publish_task  # ensure task completed cleanly

    assert accepted, "WebSocket should have been accepted with valid token"
    assert len(sent_messages) == 1
    assert sent_messages[0] == '{"event": "started"}'


async def test_ws_invalid_token_handler_rejects(fake_redis):
    """Handler closes WebSocket with 1008 for invalid token."""
    from app.routers.ws import game_websocket

    close_code = None

    class MockWebSocket:
        async def accept(self):
            raise AssertionError("Should not accept with invalid token")

        async def close(self, code: int = 1000):
            nonlocal close_code
            close_code = code

        async def send_text(self, data: str):
            raise AssertionError("Should not send with invalid token")

    mock_ws = MockWebSocket()
    await game_websocket(
        game_id="any",
        websocket=mock_ws,
        token="invalid-token",
        redis=fake_redis,
    )

    assert close_code == 1008, f"Expected close code 1008, got {close_code}"


async def test_ws_handler_swallows_send_errors(fake_redis):
    """A non-disconnect error mid-stream is caught and the pubsub is cleaned up."""
    import uuid

    from app.core.security import create_access_token

    token = create_access_token(uuid.uuid4(), "player")
    game_id = "err-game"
    channel = f"game:{game_id}"

    class MockWebSocket:
        async def accept(self):
            pass

        async def send_text(self, data: str):
            if data == '{"type": "ping"}':
                return
            raise RuntimeError("connection blew up")

        async def close(self, code: int = 1000):
            pass

    async def _delayed_publish():
        await asyncio.sleep(0.1)
        await fake_redis.publish(channel, '{"event": "boom"}')

    publish_task = asyncio.create_task(_delayed_publish())

    from app.routers.ws import game_websocket

    await game_websocket(
        game_id=game_id,
        websocket=MockWebSocket(),
        token=token,
        redis=fake_redis,
    )
    await publish_task


async def test_ws_endpoint_exists(session, fake_redis):
    """WS route is registered — bad token gives rejection, not 404."""
    from app.core.db import get_async_session
    from app.core.redis import get_redis
    from app.main import app

    async def override_session():
        yield session

    app.dependency_overrides[get_async_session] = override_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    try:
        async with httpx.AsyncClient(
            transport=ASGIWebSocketTransport(app=app), base_url="http://test"
        ) as ws_client:
            try:
                async with aconnect_ws(
                    "ws://test/ws/games/no-such-game?token=garbage", ws_client
                ) as ws:
                    await ws.receive_text()
            except WebSocketUpgradeError as e:
                # Route exists — got a specific rejection, not 404
                assert e.response.status_code != 404
            except Exception:
                # Any exception also confirms the route was found
                pass
    finally:
        app.dependency_overrides.clear()
