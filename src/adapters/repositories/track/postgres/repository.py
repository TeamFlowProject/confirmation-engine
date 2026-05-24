import uuid
import json
from psycopg import errors as psycopg_errors
from psycopg_pool import AsyncConnectionPool
from src.adapters.serializers.confirmation_rule_serializer import serialize, deserialize
from src.domain.aggregates.track import Track
from src.domain.entities.role import Role
from src.adapters.repositories.track.postgres.queries import TrackQueries

import src.adapters.repositories.errors as adapter_error


class TrackPostgresRepository:
    def __init__(self, db_pool: AsyncConnectionPool) -> None:
        self._db_pool = db_pool

    async def save(self, track: Track) -> None:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                try:
                    await conn.execute(
                        TrackQueries.INSERT_TRACK,
                        (
                            track.id,
                            track.name,
                            track.max_team_count,
                            track.auto_confirm,
                            track.grace_period_hours
                        )
                    )

                    for sort_order, rule in enumerate(track.confirmation_rules):
                        await conn.execute(
                            TrackQueries.INSERT_CONFIRMATION_RULE,
                            (
                                uuid.uuid4(),
                                track.id,
                                rule.rule_type.value,
                                json.dumps(serialize(rule)),
                                sort_order,
                            )
                        )

                    for role in track.roles:
                        await conn.execute(
                            TrackQueries.INSERT_ROLE,
                            (
                                role.id,
                                role.name,
                                role.count,
                            )
                        )

                    for role in track.roles:
                        await conn.execute(
                            TrackQueries.INSERT_ROLE_CONNECTION,
                            (
                                track.id,
                                role.id,
                            )
                        )

                except psycopg_errors.UniqueViolation:
                    raise adapter_error.TrackAlreadyExistsError(track.id)
                except psycopg_errors.ForeignKeyViolation:
                    raise adapter_error.TrackRelatedEntityNotFoundError(
                        track.id)

    async def get_by_id(self, track_id: uuid.UUID) -> Track:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                track_result = await conn.execute(
                    TrackQueries.SELECT_TRACK,
                    (track_id,)
                )

                track_row = await track_result.fetchone()

                if not track_row:
                    raise adapter_error.TrackNotFoundError(track_id)

                rules_result = await conn.execute(
                    TrackQueries.SELECT_RULES,
                    (track_id,)
                )

                rules_row = await rules_result.fetchall()

                confirmation_rules = []
                for row in rules_row:
                    confirmation_rules.append(
                        deserialize(
                            rule_type=row[0],
                            params=row[1],
                        )
                    )

                roles_result = await conn.execute(
                    TrackQueries.SELECT_ROLES,
                    (track_id,)
                )

                roles_row = await roles_result.fetchall()

                roles = []
                for row in roles_row:
                    roles.append(
                        Role(
                            id=row[0],
                            name=row[1],
                            count=row[2]
                        )
                    )

                return Track(
                    id=track_id,
                    name=track_row[0],
                    max_team_count=track_row[1],
                    auto_confirm=track_row[2],
                    grace_period_hours=track_row[3],
                    roles=roles,
                    confirmation_rules=confirmation_rules,
                )
