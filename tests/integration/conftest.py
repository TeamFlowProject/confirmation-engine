import uuid
import psycopg_pool
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from migrations.migrate import up
from src.adapters.repositories.track.postgres.repository import TrackPostgresRepository
from src.adapters.repositories.team_application.postgres.repository import TeamApplicationPostgresRepository


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17") as pg:
        host = pg.get_container_host_ip()
        port = pg.get_exposed_port(5432)
        user = pg.username
        password = pg.password
        dbname = pg.dbname
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        yoyo_dsn = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
        up(yoyo_dsn)
        yield dsn


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def pool(postgres_container):
    async with psycopg_pool.AsyncConnectionPool(
        conninfo=postgres_container,
        min_size=2,
        max_size=10,
    ) as pool:
        yield pool


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def track_repository(pool):
    return TrackPostgresRepository(pool)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def team_application_repository(pool):
    return TeamApplicationPostgresRepository(pool)
