import uuid

from psycopg_pool import AsyncConnectionPool

from src.domain.aggregates.team_application import TeamApplication


class TeamApplicationPostgresRepository:
    def __init__(self, db_pool: AsyncConnectionPool) -> None:
        self._db_pool = db_pool

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
