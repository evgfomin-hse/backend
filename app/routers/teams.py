import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.services.team import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
async def list_teams(skip: int = 0, limit: int = 100, session: AsyncSession = Depends(get_db)):
    return await TeamService(session).list(skip=skip, limit=limit)


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreate,
    session: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    return await TeamService(session).create(body)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: uuid.UUID, session: AsyncSession = Depends(get_db)):
    return await TeamService(session).get_or_404(team_id)


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    body: TeamUpdate,
    session: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    return await TeamService(session).update(team_id, body)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    await TeamService(session).delete(team_id)
