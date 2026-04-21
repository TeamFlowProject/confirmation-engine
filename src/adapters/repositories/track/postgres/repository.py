import uuid

from psycopg_pool import AsyncConnectionPool

from src.domain.aggregates.track import Track


class TrackPostgresRepository:
    def __init__(self, db_pool: AsyncConnectionPool) -> None:
        self._db_pool = db_pool

    async def save(self, track: Track) -> None: ...

    async def get_by_id(self, track_id: uuid.UUID) -> Track | None: ...
