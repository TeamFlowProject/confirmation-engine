import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.aggregates.team_application import TeamApplication
from tests.integration.adapters.repository.postgress.helper import cleanup_db
from src.domain.entities.member import Member
from src.domain.value_objects.team_status import TeamStatus
import src.adapters.repositories.errors as adapter_error


async def _save_role(pool, role_id: uuid.UUID) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO roles (id, name, count, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (role_id, "Developer", 2, now),
        )


def _make_member(role_id: uuid.UUID) -> Member:  # role_id теперь обязательный
    return Member(
        id=uuid.uuid4(),
        name="Ivan",
        surname="Ivanov",
        patronymic="Ivanovich",
        role_id=role_id,
    )


def _make_application(
    track_id: uuid.UUID | None = None,
    members: list[Member] | None = None,
    status: TeamStatus = TeamStatus.NONE,
) -> TeamApplication:
    return TeamApplication(
        id=uuid.uuid4(),
        track_id=track_id or uuid.uuid4(),
        name="Test Team",
        members=members or [],
        status=status,
        rejection_reason=None,
        grace_deadline=None,
    )


async def _save_track(pool, track_id: uuid.UUID) -> None:
    """Создаёт трек напрямую в БД чтобы FK не упал."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO tracks (id, name, max_team_count, auto_confirm, grace_period_hours, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (track_id, "Track", 10, False, 24, now, now),
        )


@pytest.mark.integration
class TestTeamApplicationRepositorySave:
    @pytest.mark.asyncio
    async def test_saves_application_and_retrieves_it(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)
        application = _make_application(track_id=track_id)
        try:
            await team_application_repository.save(application)
            result = await team_application_repository.get_by_id(application.id)

            assert result.id == application.id
            assert result.track_id == application.track_id
            assert result.name == application.name
            assert result.status == TeamStatus.NONE
            assert result.rejection_reason is None
            assert result.grace_deadline is None
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_saves_application_with_members(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        role_id = uuid.uuid4()
        await _save_track(pool, track_id)
        await _save_role(pool, role_id)
        members = [_make_member(role_id), _make_member(role_id)]
        application = _make_application(track_id=track_id, members=members)
        try:
            await team_application_repository.save(application)
            result = await team_application_repository.get_by_id(application.id)

            assert len(result.members) == 2
            result_ids = {m.id for m in result.members}
            assert result_ids == {m.id for m in members}
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_updates_status_on_second_save(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)
        application = _make_application(track_id=track_id, status=TeamStatus.NONE)
        try:
            await team_application_repository.save(application)

            application.status = TeamStatus.SUBMITTED
            await team_application_repository.save(application)

            result = await team_application_repository.get_by_id(application.id)
            assert result.status == TeamStatus.SUBMITTED
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_updates_members_on_second_save(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        role_id = uuid.uuid4()
        await _save_track(pool, track_id)
        await _save_role(pool, role_id)
        old_member = _make_member(role_id)
        application = _make_application(track_id=track_id, members=[old_member])
        try:
            await team_application_repository.save(application)

            new_member = _make_member(role_id)
            application.members = [new_member]
            await team_application_repository.save(application)

            result = await team_application_repository.get_by_id(application.id)
            assert len(result.members) == 1
            assert result.members[0].id == new_member.id
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_saves_application_with_rejection_reason(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)
        application = _make_application(track_id=track_id, status=TeamStatus.REJECTED)
        application.rejection_reason = "Not enough members"
        try:
            await team_application_repository.save(application)
            result = await team_application_repository.get_by_id(application.id)

            assert result.rejection_reason == "Not enough members"
        finally:
            await cleanup_db(pool)


@pytest.mark.integration
class TestTeamApplicationRepositoryGetById:
    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_application(
        self, team_application_repository
    ):
        with pytest.raises(adapter_error.TeamApplicationNotFoundError):
            await team_application_repository.get_by_id(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_returns_correct_member_fields(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        role_id = uuid.uuid4()
        await _save_track(pool, track_id)
        await _save_role(pool, role_id)
        member = _make_member(role_id)
        application = _make_application(track_id=track_id, members=[member])
        try:
            await team_application_repository.save(application)
            result = await team_application_repository.get_by_id(application.id)

            m = result.members[0]
            assert m.id == member.id
            assert m.name == member.name
            assert m.surname == member.surname
            assert m.patronymic == member.patronymic
            assert m.role_id == member.role_id
        finally:
            await cleanup_db(pool)


@pytest.mark.integration
class TestTeamApplicationRepositoryGetByTrackId:
    @pytest.mark.asyncio
    async def test_returns_all_applications_for_track(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)
        apps = [_make_application(track_id=track_id) for _ in range(3)]
        try:
            for app in apps:
                await team_application_repository.save(app)

            result = await team_application_repository.get_by_track_id(track_id)
            result_ids = {a.id for a in result}

            assert len(result) == 3
            assert result_ids == {a.id for a in apps}
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_unknown_track(
        self, team_application_repository
    ):
        result = await team_application_repository.get_by_track_id(uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_does_not_return_applications_from_other_tracks(
        self, team_application_repository, pool
    ):
        track_id_1 = uuid.uuid4()
        track_id_2 = uuid.uuid4()
        await _save_track(pool, track_id_1)
        await _save_track(pool, track_id_2)

        app1 = _make_application(track_id=track_id_1)
        app2 = _make_application(track_id=track_id_2)
        try:
            await team_application_repository.save(app1)
            await team_application_repository.save(app2)

            result = await team_application_repository.get_by_track_id(track_id_1)
            assert len(result) == 1
            assert result[0].id == app1.id
        finally:
            await cleanup_db(pool)


@pytest.mark.integration
class TestTeamApplicationRepositoryGetConfirmedByTrackId:
    @pytest.mark.asyncio
    async def test_returns_only_confirmed(self, team_application_repository, pool):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)

        confirmed = _make_application(track_id=track_id, status=TeamStatus.CONFIRMED)
        pending = _make_application(track_id=track_id, status=TeamStatus.SUBMITTED)
        try:
            await team_application_repository.save(confirmed)
            await team_application_repository.save(pending)

            result = await team_application_repository.get_confirmed_by_track_id(
                track_id
            )

            assert len(result) == 1
            assert result[0].id == confirmed.id
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_confirmed(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)
        application = _make_application(track_id=track_id, status=TeamStatus.SUBMITTED)
        try:
            await team_application_repository.save(application)
            result = await team_application_repository.get_confirmed_by_track_id(
                track_id
            )
            assert result == []
        finally:
            await cleanup_db(pool)


@pytest.mark.integration
class TestTeamApplicationRepositoryCountConfirmed:
    @pytest.mark.asyncio
    async def test_counts_confirmed_applications(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)

        for _ in range(3):
            app = _make_application(track_id=track_id, status=TeamStatus.CONFIRMED)
            await team_application_repository.save(app)

        app_other = _make_application(track_id=track_id, status=TeamStatus.SUBMITTED)
        await team_application_repository.save(app_other)
        try:
            count = await team_application_repository.count_confirmed_by_track(track_id)
            assert count == 3
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_returns_zero_for_unknown_track(self, team_application_repository):
        count = await team_application_repository.count_confirmed_by_track(uuid.uuid4())
        assert count == 0


@pytest.mark.integration
class TestTeamApplicationRepositoryGetExpiredInvalid:
    @pytest.mark.asyncio
    async def test_returns_invalid_with_expired_deadline(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)

        expired = _make_application(track_id=track_id, status=TeamStatus.INVALID)
        expired.grace_deadline = datetime.now(timezone.utc) - timedelta(hours=1)

        not_expired = _make_application(track_id=track_id, status=TeamStatus.INVALID)
        not_expired.grace_deadline = datetime.now(timezone.utc) + timedelta(hours=1)

        valid_app = _make_application(track_id=track_id, status=TeamStatus.CONFIRMED)
        try:
            await team_application_repository.save(expired)
            await team_application_repository.save(not_expired)
            await team_application_repository.save(valid_app)

            result = await team_application_repository.get_expired_invalid()
            result_ids = {a.id for a in result}

            assert expired.id in result_ids
            assert not_expired.id not in result_ids
            assert valid_app.id not in result_ids
        finally:
            await cleanup_db(pool)


@pytest.mark.integration
class TestTeamApplicationRepositoryGetNextWaiting:
    @pytest.mark.asyncio
    async def test_returns_oldest_validated_application(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)

        first = _make_application(track_id=track_id, status=TeamStatus.VALIDATED)
        second = _make_application(track_id=track_id, status=TeamStatus.VALIDATED)
        try:
            await team_application_repository.save(first)
            await team_application_repository.save(second)

            result = await team_application_repository.get_next_waiting_by_track(
                track_id
            )

            assert result is not None
            assert result.id == first.id
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_returns_none_when_no_validated(
        self, team_application_repository, pool
    ):
        track_id = uuid.uuid4()
        await _save_track(pool, track_id)
        application = _make_application(track_id=track_id, status=TeamStatus.SUBMITTED)
        try:
            await team_application_repository.save(application)
            result = await team_application_repository.get_next_waiting_by_track(
                track_id
            )
            assert result is None
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_track(self, team_application_repository):
        result = await team_application_repository.get_next_waiting_by_track(
            uuid.uuid4()
        )
        assert result is None
