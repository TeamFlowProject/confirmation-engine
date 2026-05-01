import uuid
from typing import Protocol

from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track


class ConfirmationService(Protocol):
    async def create_rule(self, track: Track) -> None: ...

    async def confirm_team(self, application_id: uuid.UUID) -> None: ...

    async def get_application(self, track_id: uuid.UUID) -> list[TeamApplication]: ...

    async def get_rule_by_track_id(self, track_id: uuid.UUID) -> Track: ...

    async def get_confirmed_teams_by_track(
        self, track_id: uuid.UUID
    ) -> list[TeamApplication]: ...
