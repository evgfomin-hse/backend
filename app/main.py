from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401
from app.core.audit import AuditMiddleware, setup_db_instrumentation
from app.core.db import engine
from app.core.redis import close_redis, init_redis
from app.routers import auth, demo, games, questions, sse, stats, teams, users, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_redis()
    setup_db_instrumentation(engine)
    yield
    await close_redis()


app = FastAPI(title="Quiz Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(AuditMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(questions.router)
app.include_router(games.router)
app.include_router(stats.router)
app.include_router(ws.router)
app.include_router(sse.router)
app.include_router(demo.router)
