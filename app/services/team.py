import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.repositories.team import TeamRepository
from app.schemas.team import TeamCreate, TeamUpdate


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TeamRepository(session)

    async def get_or_404(self, team_id: uuid.UUID) -> Team:
        team = await self.repo.get(team_id)
        if not team:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
        return team

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repo.list(skip=skip, limit=limit)

    async def create(self, body: TeamCreate) -> Team:
        team = Team(name=body.name)
        return await self.repo.add(team)

    async def update(self, team_id: uuid.UUID, body: TeamUpdate) -> Team:
        team = await self.get_or_404(team_id)
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(team, field, value)
        await self.repo.session.flush()
        await self.repo.session.refresh(team)
        return team

    async def delete(self, team_id: uuid.UUID) -> None:
        team = await self.get_or_404(team_id)
        await self.repo.delete(team)
