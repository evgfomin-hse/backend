"""Lightweight in-process audit bus used by the demo dashboard.

It captures *who provoked what*: every HTTP call, DB read/write and Redis
operation is published as an event tagged with the current "actor" (user1,
user2, admin, ...). The demo `/demo/logs` SSE endpoint streams these events
to the browser so all four panels can watch the backend work in real time.

This module is intentionally self-contained and has no effect on the app
unless its middleware / instrumentation hooks are installed from main.py.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

# The actor that triggered the work happening in the current task.
# Set by AuditMiddleware (from the X-Demo-Actor header) for HTTP requests,
# and by the WS/SSE handlers (from the ?actor= query param) for realtime.
current_actor: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_actor", default="system"
)

# Set of live subscriber queues (one per open /demo/logs stream).
_subscribers: set[asyncio.Queue] = set()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def _short(value) -> str:
    """Collapse whitespace/newlines to one line. No truncation — full text."""
    text = str(value).replace("\n", " ").strip()
    return " ".join(text.split())


def log_event(category: str, action: str, detail: str = "", actor: str | None = None) -> None:
    """Publish one audit event to every open log stream.

    category: http | db | redis | ws | sse | auth | demo
    """
    event = {
        "ts": _now(),
        "actor": actor or current_actor.get(),
        "category": category,
        "action": action,
        "detail": _short(detail),
    }
    for queue in list(_subscribers):
        # Drop on a full queue rather than block the request path.
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def subscribe() -> AsyncGenerator[dict, None]:
    """Yield audit events as they happen for one /demo/logs connection."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers.add(queue)
    try:
        while True:
            yield await queue.get()
    finally:
        _subscribers.discard(queue)


# --------------------------------------------------------------------------- #
# HTTP instrumentation (pure ASGI middleware so contextvars propagate into
# the endpoint and the SQLAlchemy event handlers).
# --------------------------------------------------------------------------- #

# Paths we never log as HTTP (the log stream itself, the page, static, favicon).
_HTTP_SKIP = {"/demo", "/demo/logs", "/favicon.ico"}


class AuditMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
        actor = headers.get("x-demo-actor") or "anonymous"
        path = scope.get("path", "")
        method = scope.get("method", "")
        loggable = path not in _HTTP_SKIP and not path.startswith("/static")

        token = current_actor.set(actor)
        status_holder: dict[str, int] = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        if loggable:
            log_event("http", f"{method} {path}", "request in", actor=actor)
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if loggable:
                log_event(
                    "http",
                    f"{method} {path}",
                    f"response {status_holder.get('status', '?')}",
                    actor=actor,
                )
            current_actor.reset(token)


# --------------------------------------------------------------------------- #
# DB instrumentation (SQLAlchemy core events on the sync engine).
# --------------------------------------------------------------------------- #

def _fmt_value(value) -> str:
    """Render a single bound parameter value for the log, SQL-like."""
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return repr(value)  # keep quotes so '' vs NULL is unambiguous
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    return str(value)


def _fmt_row(row) -> str:
    if isinstance(row, dict):
        return "{" + ", ".join(f"{k}: {_fmt_value(v)}" for k, v in row.items()) + "}"
    if isinstance(row, (list, tuple)):
        return "(" + ", ".join(_fmt_value(v) for v in row) + ")"
    return _fmt_value(row)


def _format_params(parameters, executemany: bool) -> str:
    """Render the actual bound values so the log shows real data, not $1/$2…"""
    if not parameters:
        return ""
    try:
        if executemany and isinstance(parameters, (list, tuple)):
            return " — params: [" + ", ".join(_fmt_row(r) for r in parameters) + "]"
        return " — params: " + _fmt_row(parameters)
    except Exception:
        return ""


def setup_db_instrumentation(async_engine) -> None:
    from sqlalchemy import event

    @event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        verb = statement.lstrip().split(" ", 1)[0].upper()
        if verb == "SELECT":
            action = "DB read"
        elif verb in ("INSERT", "UPDATE", "DELETE"):
            action = "DB write"
        else:
            action = "DB exec"
        log_event("db", action, statement + _format_params(parameters, executemany))


# --------------------------------------------------------------------------- #
# Redis instrumentation (thin proxies around the async client / pubsub).
# --------------------------------------------------------------------------- #

class AuditedPubSub:
    def __init__(self, pubsub) -> None:
        self._ps = pubsub

    def __getattr__(self, name):
        return getattr(self._ps, name)

    async def subscribe(self, *channels, **kwargs):
        log_event("redis", "SUBSCRIBE", ", ".join(map(str, channels)))
        return await self._ps.subscribe(*channels, **kwargs)

    async def unsubscribe(self, *channels, **kwargs):
        log_event("redis", "UNSUBSCRIBE", ", ".join(map(str, channels)))
        return await self._ps.unsubscribe(*channels, **kwargs)


class AuditedRedis:
    """Wraps an aioredis.Redis client, logging the operations the app uses."""

    def __init__(self, client) -> None:
        self._client = client

    def __getattr__(self, name):
        return getattr(self._client, name)

    async def publish(self, channel, message, **kwargs):
        log_event("redis", f"PUBLISH {channel}", message)
        return await self._client.publish(channel, message, **kwargs)

    async def get(self, name, **kwargs):
        log_event("redis", "GET", str(name))
        return await self._client.get(name, **kwargs)

    async def set(self, name, value, **kwargs):
        log_event("redis", "SET", f"{name} = {_short(value)}")
        return await self._client.set(name, value, **kwargs)

    def pubsub(self, **kwargs):
        return AuditedPubSub(self._client.pubsub(**kwargs))
