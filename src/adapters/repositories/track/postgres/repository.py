from psycopg_pool import AsyncConnectionPool


class TrackPostgresRepository:
    def __init__(self, db_pool: AsyncConnectionPool) -> None:
        self._db_pool = db_pool
