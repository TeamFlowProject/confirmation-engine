import json
import uuid
from datetime import datetime, timezone
from psycopg_pool import AsyncConnectionPool
from psycopg import errors as psycopg_error

from src.domain.entities.member import Member
from src.domain.aggregates.team_application import TeamApplication, TeamStatus
from src.adapters.repositories.team_application.postgres.queries import (
    TeamApplicationQueries,
    MembersQueries,
    OutboxQueries,
)
import src.adapters.repositories.errors as adapter_error


class TeamApplicationPostgresRepository:
    def __init__(self, db_pool: AsyncConnectionPool) -> None:
        self._db_pool = db_pool

    async def save(self, application: TeamApplication) -> None:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                try:
                    now = datetime.now(timezone.utc)
                    await conn.execute(
                        TeamApplicationQueries.INSERT_TEAM_APPLICATION,
                        {
                            "id": application.id,
                            "track_id": application.track_id,
                            "name": application.name,
                            "status": application.status.value,
                            "rejection_reason": application.rejection_reason,
                            "grace_deadline": application.grace_deadline,
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

                    for member in application.members:
                        await conn.execute(
                            MembersQueries.INSERT_MEMBER,
                            {
                                "id": member.id,
                                "name": member.name,
                                "surname": member.surname,
                                "patronymic": member.patronymic,
                                "role_id": member.role_id,
                                "created_at": now,
                            },
                        )

                    await conn.execute(
                        MembersQueries.DELETE_OLD_MEMBER_CONNECTION,
                        {"application_id": application.id},
                    )

                    for member in application.members:
                        await conn.execute(
                            MembersQueries.INSERT_MEMBER_CONNECTION,
                            {
                                "application_id": application.id,
                                "member_id": member.id,
                            },
                        )

                    events = application.collect_events()
                    for event in events:
                        idempotency_key = (
                            f"TeamApplication:{application.id}:{type(event).__name__}:{now.isoformat()}"
                        )
                        await conn.execute(
                            OutboxQueries.INSERT_OUTBOX_EVENT,
                            {
                                "id": uuid.uuid4(),
                                "aggregate_type": "TeamApplication",
                                "aggregate_id": str(application.id),
                                "event_type": type(event).__name__,
                                "payload": json.dumps(event.__dict__),
                                "idempotency_key": idempotency_key,
                            },
                        )

                except psycopg_error.UniqueViolation:
                    raise adapter_error.TeamApplicationAlreadyExistsError(
                        application.id
                    )
                except psycopg_error.ForeignKeyViolation:
                    raise adapter_error.TeamApplicationRelatedEntityNotFoundError(
                        application.id
                    )

    async def get_by_id(self, application_id: uuid.UUID) -> TeamApplication:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                try:
                    application_result = await conn.execute(
                        TeamApplicationQueries.SELECT_TEAM_APPLICATION,
                        {"id": application_id},
                    )
                    application_row = await application_result.fetchone()
                    if not application_row:
                        raise adapter_error.TeamApplicationNotFoundError(
                            application_id)

                    members_result = await conn.execute(
                        MembersQueries.SELECT_MEMBERS,
                        {"application_id": application_id},
                    )
                    members_rows = await members_result.fetchall()
                    members = [
                        Member(
                            id=row[0],
                            name=row[1],
                            surname=row[2],
                            patronymic=row[3],
                            role_id=row[4],
                        )
                        for row in members_rows
                    ]

                    return TeamApplication(
                        id=application_row[0],
                        track_id=application_row[1],
                        name=application_row[2],
                        status=TeamStatus(application_row[3]),
                        rejection_reason=application_row[4],
                        grace_deadline=application_row[5],
                        members=members,
                    )

                except adapter_error.TeamApplicationNotFoundError:
                    raise

    async def get_by_track_id(self, track_id: uuid.UUID) -> list[TeamApplication]:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                return await self._fetch_applications(
                    conn,
                    TeamApplicationQueries.SELECT_TEAM_APPLICATION_BY_TRACK_ID,
                    {"track_id": track_id},
                )

    async def get_confirmed_by_track_id(
        self, track_id: uuid.UUID
    ) -> list[TeamApplication]:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                return await self._fetch_applications(
                    conn,
                    TeamApplicationQueries.SELECT_CONFIRMED_BY_TRACK_ID,
                    {"track_id": track_id},
                )

    async def count_confirmed_by_track(self, track_id: uuid.UUID) -> int:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    TeamApplicationQueries.COUNT_CONFIRMED_APPLICATIONS_BY_ID,
                    {"track_id": track_id},
                )
                row = await result.fetchone()
                return int(row[0]) if row else 0

    async def get_expired_invalid(self) -> list[TeamApplication]:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                return await self._fetch_applications(
                    conn, TeamApplicationQueries.SELECT_EXPIRED_INVALID
                )

    async def get_next_waiting_by_track(
        self, track_id: uuid.UUID
    ) -> TeamApplication | None:
        async with self._db_pool.connection() as conn:
            async with conn.transaction():
                application_result = await conn.execute(
                    TeamApplicationQueries.SELECT_NEXT_TEAM_APPLICATION,
                    {"track_id": track_id},
                )
                application_row = await application_result.fetchone()
                if not application_row:
                    return None

                members_result = await conn.execute(
                    MembersQueries.SELECT_MEMBERS,
                    {"application_id": application_row[0]},
                )
                members_rows = await members_result.fetchall()
                members = [
                    Member(
                        id=row[0],
                        name=row[1],
                        surname=row[2],
                        patronymic=row[3],
                        role_id=row[4],
                    )
                    for row in members_rows
                ]

                return TeamApplication(
                    id=application_row[0],
                    track_id=application_row[1],
                    name=application_row[2],
                    status=TeamStatus(application_row[3]),
                    rejection_reason=application_row[4],
                    grace_deadline=application_row[5],
                    members=members,
                )

    async def _fetch_applications(
        self, conn, query: str, params: dict | None = None
    ) -> list[TeamApplication]:
        params = params or {}
        applications_result = await conn.execute(query, params)
        applications_rows = await applications_result.fetchall()

        if not applications_rows:
            return []

        application_ids = [row[0] for row in applications_rows]

        members_result = await conn.execute(
            MembersQueries.SELECT_MEMBERS_BY_APPLICATION_IDS,
            {"application_ids": application_ids},
        )
        members_rows = await members_result.fetchall()

        members_by_application: dict[uuid.UUID, list[Member]] = {}
        for row in members_rows:
            application_id = row[5]
            members_by_application.setdefault(application_id, []).append(
                Member(
                    id=row[0],
                    name=row[1],
                    surname=row[2],
                    patronymic=row[3],
                    role_id=row[4],
                )
            )

        return [
            TeamApplication(
                id=row[0],
                track_id=row[1],
                name=row[2],
                status=TeamStatus(row[3]),
                rejection_reason=row[4],
                grace_deadline=row[5],
                members=members_by_application.get(row[0], []),
            )
            for row in applications_rows
        ]
