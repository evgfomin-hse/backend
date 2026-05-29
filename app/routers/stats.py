from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.stats import PlayerStats, TeamStats
from app.services.stats import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/players", response_model=list[PlayerStats])
async def top_players(
    period: str = "all",
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
):
    return await StatsService(session).top_players(period, limit)


@router.get("/teams", response_model=list[TeamStats])
async def top_teams(
    period: str = "all",
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
):
    return await StatsService(session).top_teams(period, limit)
