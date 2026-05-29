from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.answer import AnswerRepository
from app.schemas.stats import PlayerStats, TeamStats


class StatsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AnswerRepository(session)

    async def top_players(self, period: str, limit: int = 10) -> list[PlayerStats]:
        rows = await self.repo.get_top_players(period, limit)
        return [
            PlayerStats(
                player_id=row["player_id"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                total_points=row["total_points"] or 0,
                correct_answers=row["correct_answers"] or 0,
            )
            for row in rows
        ]

    async def top_teams(self, period: str, limit: int = 10) -> list[TeamStats]:
        rows = await self.repo.get_top_teams(period, limit)
        return [
            TeamStats(
                team_id=row["team_id"],
                name=row["name"],
                total_points=row["total_points"] or 0,
                games_played=row["games_played"] or 0,
                games_won=row["games_won"] or 0,
            )
            for row in rows
        ]
