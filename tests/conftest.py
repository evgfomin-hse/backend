import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — ensure all models are registered on Base.metadata
from app.core.db import Base, get_async_session
from app.core.redis import get_redis

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        conn = await s.connection()
        await conn.run_sync(Base.metadata.create_all)
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def fake_redis():
    from fakeredis.aioredis import FakeRedis
    r = FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def client(session, fake_redis):
    from app.main import app

    async def override_session():
        yield session

    app.dependency_overrides[get_async_session] = override_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def create_test_user(
    session,
    *,
    login: str = "testuser",
    password: str = "password123",
    role: str = "player",
    email: str = "test@example.com",
    first_name: str = "Test",
    last_name: str = "User",
    team_id=None,
):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        login=login,
        hashed_password=hash_password(password),
        role=UserRole(role),
        team_id=team_id,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def get_auth_headers(client, login: str = "testuser", password: str = "password123") -> dict:
    resp = await client.post("/auth/login", json={"login": login, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
