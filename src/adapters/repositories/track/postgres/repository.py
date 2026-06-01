import json
import uuid
from datetime import datetime, timezone
from psycopg import errors as psycopg_errors
from psycopg_pool import AsyncConnectionPool
from src.adapters.serializers.confirmation_rule_serializer import serialize, deserialize
from src.domain.aggregates.track import Track
from src.domain.entities.role import Role
from src.adapters.repositories.track.postgres.queries import TrackQueries, RolesQueries
import src.adapters.repositories.errors as adapter_error


class TrackPostgresRepository:
    def __init__(self, db_pool: AsyncConnectionPool) -> None:
        self._db_pool = db_pool

    async def save(self, track: Track) -> None:
        """
        Сохраняет конфигурацию трека (confirmation rules + параметры).

        Роли и связи track_roles НЕ трогаются: они принадлежат синхронизации
        из event-service через Kafka (см. update_roles). Раньше save() делал
        DELETE_TRACK_ROLES + переинсерт из payload, и POST /rule без roles
        затирал синхронизированные из Kafka связи.
        """
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                try:
                    now = datetime.now(timezone.utc)
                    await conn.execute(
                        TrackQueries.INSERT_TRACK,
                        {
                            "id": track.id,
                            "name": track.name,
                            "max_team_count": track.max_team_count,
                            "auto_confirm": track.auto_confirm,
                            "grace_period_hours": track.grace_period_hours,
                            "confirmation_rules": json.dumps(
                                [serialize(r) for r in track.confirmation_rules]
                            ),
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

                except psycopg_errors.UniqueViolation:
                    raise adapter_error.TrackAlreadyExistsError(track.id)
                except psycopg_errors.ForeignKeyViolation:
                    raise adapter_error.TrackRelatedEntityNotFoundError(track.id)

    async def update_roles(
        self, track_id: uuid.UUID, name: str, roles: list[Role]
    ) -> None:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                now = datetime.now(timezone.utc)
                await conn.execute(
                    TrackQueries.INSERT_TRACK_IF_NOT_EXISTS,
                    {"id": track_id, "name": name, "now": now},
                )
                await conn.execute(
                    RolesQueries.DELETE_TRACK_ROLES, {"track_id": track_id}
                )
                for role in roles:
                    await conn.execute(
                        RolesQueries.UPSERT_ROLE,
                        {
                            "id": role.id,
                            "name": role.name,
                            "count": role.count,
                            "created_at": now,
                        },
                    )
                    await conn.execute(
                        RolesQueries.INSERT_ROLE_CONNECTION,
                        {"track_id": track_id, "role_id": role.id},
                    )

    async def get_by_id(self, track_id: uuid.UUID) -> Track:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                track_result = await conn.execute(
                    TrackQueries.SELECT_TRACK, {"id": track_id}
                )
                track_row = await track_result.fetchone()

                if not track_row:
                    raise adapter_error.TrackNotFoundError(track_id)

                roles_result = await conn.execute(
                    RolesQueries.SELECT_ROLES, {"track_id": track_id}
                )
                roles_rows = await roles_result.fetchall()

                return Track(
                    id=track_id,
                    name=track_row[0],
                    max_team_count=track_row[1],
                    auto_confirm=track_row[2],
                    grace_period_hours=track_row[3],
                    roles=[
                        Role(id=row[0], name=row[1], count=row[2]) for row in roles_rows
                    ],
                    confirmation_rules=[
                        deserialize(r["rule_type"], r["params"]) for r in track_row[4]
                    ],
                )
