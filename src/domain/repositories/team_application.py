import uuid
from typing import Protocol

from src.domain.aggregates.team_application import TeamApplication


class TeamApplicationRepository(Protocol):
    async def save(self, application: TeamApplication) -> None: ...

    async def get_by_id(self, application_id: uuid.UUID) -> TeamApplication | None: ...

    async def get_by_track_id(self, track_id: uuid.UUID) -> list[TeamApplication]: ...

    async def get_confirmed_by_track_id(
        self, track_id: uuid.UUID
    ) -> list[TeamApplication]: ...

    async def count_confirmed_by_track(self, track_id: uuid.UUID) -> int: ...

    async def get_expired_invalid(self) -> list[TeamApplication]: ...

    async def get_next_waiting_by_track(
        self, track_id: uuid.UUID
    ) -> TeamApplication | None: ...
