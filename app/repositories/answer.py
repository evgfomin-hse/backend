import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.answer import Answer
from app.models.team import Team
from app.models.user import User
from app.repositories.base import BaseRepository


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    if period == "all":
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    raise ValueError(f"Unknown period: {period!r}. Use 'week', 'month', or 'all'.")


class AnswerRepository(BaseRepository[Answer]):
    model = Answer

    async def get_team_answer_for_game_question(
        self, game_question_id: uuid.UUID, team_id: uuid.UUID
    ) -> Answer | None:
        result = await self.session.execute(
            select(Answer).where(
                Answer.game_question_id == game_question_id,
                Answer.team_id == team_id,
            )
        )
        return result.scalars().first()

    async def get_top_players(self, period: str, limit: int = 10) -> list:
        since = _period_start(period)
        result = await self.session.execute(
            select(
                Answer.player_id.label("player_id"),
                User.first_name,
                User.last_name,
                func.sum(Answer.points_awarded).label("total_points"),
                func.count(Answer.id).filter(Answer.is_correct == True).label("correct_answers"),
            )
            .join(User, User.id == Answer.player_id)
            .where(Answer.answered_at >= since)
            .group_by(Answer.player_id, User.first_name, User.last_name)
            .order_by(func.sum(Answer.points_awarded).desc())
            .limit(limit)
        )
        return list(result.mappings().all())

    async def get_top_teams(self, period: str, limit: int = 10) -> list:
        since = _period_start(period)
        result = await self.session.execute(
            select(
                Answer.team_id.label("team_id"),
                Team.name,
                func.sum(Answer.points_awarded).label("total_points"),
                Team.games_played,
                Team.games_won,
            )
            .join(Team, Team.id == Answer.team_id)
            .where(Answer.answered_at >= since)
            .group_by(Answer.team_id, Team.name, Team.games_played, Team.games_won)
            .order_by(func.sum(Answer.points_awarded).desc())
            .limit(limit)
        )
        return list(result.mappings().all())
