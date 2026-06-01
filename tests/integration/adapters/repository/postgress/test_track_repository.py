import uuid
import pytest

from src.domain.aggregates.track import Track
from src.domain.entities.role import Role
from src.domain.value_objects.confirmation_rule import (
    RoleConfirmationRule,
    TeamSizeConfirmationRule,
)
from tests.integration.adapters.repository.postgress.helper import cleanup_db
import src.adapters.repositories.errors as adapter_error


def _make_track(roles: list[Role] | None = None) -> Track:
    return Track(
        id=uuid.uuid4(),
        name="Test Track",
        max_team_count=10,
        auto_confirm=False,
        grace_period_hours=24,
        roles=roles or [],
        confirmation_rules=[
            TeamSizeConfirmationRule(min_team_size=2, max_team_size=5),
        ],
    )


@pytest.mark.integration
class TestTrackPostgresRepositorySave:
    @pytest.mark.asyncio
    async def test_saves_track_and_retrieves_it(self, track_repository, pool):
        track = _make_track()
        try:
            await track_repository.save(track)
            result = await track_repository.get_by_id(track.id)

            assert result.id == track.id
            assert result.name == track.name
            assert result.max_team_count == track.max_team_count
            assert result.auto_confirm == track.auto_confirm
            assert result.grace_period_hours == track.grace_period_hours
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_saves_track_with_confirmation_rules(self, track_repository, pool):
        track = Track(
            id=uuid.uuid4(),
            name="Track with rules",
            max_team_count=5,
            auto_confirm=False,
            grace_period_hours=48,
            roles=[],
            confirmation_rules=[
                TeamSizeConfirmationRule(min_team_size=1, max_team_size=3),
                RoleConfirmationRule(take_into_account_role_count=True),
            ],
        )
        try:
            await track_repository.save(track)
            result = await track_repository.get_by_id(track.id)

            assert len(result.confirmation_rules) == 2
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_saves_track_without_roles_and_rules(self, track_repository, pool):
        track = Track(
            id=uuid.uuid4(),
            name="Empty Track",
            max_team_count=5,
            auto_confirm=True,
            grace_period_hours=24,
            roles=[],
            confirmation_rules=[],
        )
        try:
            await track_repository.save(track)
            result = await track_repository.get_by_id(track.id)

            assert result.id == track.id
            assert result.roles == []
            assert result.confirmation_rules == []
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_updates_track_on_second_save(self, track_repository, pool):
        track = _make_track()
        try:
            await track_repository.save(track)

            track.name = "Updated Track"
            track.max_team_count = 20
            track.auto_confirm = True
            await track_repository.save(track)

            result = await track_repository.get_by_id(track.id)
            assert result.name == "Updated Track"
            assert result.max_team_count == 20
            assert result.auto_confirm is True
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_updates_confirmation_rules_on_second_save(
        self, track_repository, pool
    ):
        track = Track(
            id=uuid.uuid4(),
            name="Track",
            max_team_count=5,
            auto_confirm=False,
            grace_period_hours=24,
            roles=[],
            confirmation_rules=[
                TeamSizeConfirmationRule(min_team_size=1, max_team_size=3),
            ],
        )
        try:
            await track_repository.save(track)

            track.confirmation_rules = [
                RoleConfirmationRule(take_into_account_role_count=True),
            ]
            await track_repository.save(track)

            result = await track_repository.get_by_id(track.id)
            assert len(result.confirmation_rules) == 1
            assert isinstance(result.confirmation_rules[0], RoleConfirmationRule)
        finally:
            await cleanup_db(pool)


@pytest.mark.integration
class TestTrackPostgresRepositoryGetById:
    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_track(self, track_repository):
        with pytest.raises(adapter_error.TrackNotFoundError):
            await track_repository.get_by_id(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_returns_correct_confirmation_rule_types(
        self, track_repository, pool
    ):
        track = Track(
            id=uuid.uuid4(),
            name="Track",
            max_team_count=5,
            auto_confirm=False,
            grace_period_hours=24,
            roles=[],
            confirmation_rules=[
                TeamSizeConfirmationRule(min_team_size=2, max_team_size=4),
            ],
        )
        try:
            await track_repository.save(track)
            result = await track_repository.get_by_id(track.id)

            rule = result.confirmation_rules[0]
            assert isinstance(rule, TeamSizeConfirmationRule)
            assert rule.min_team_size == 2
            assert rule.max_team_size == 4
        finally:
            await cleanup_db(pool)

    @pytest.mark.asyncio
    async def test_confirmation_rules_order_preserved(self, track_repository, pool):
        track = Track(
            id=uuid.uuid4(),
            name="Track",
            max_team_count=5,
            auto_confirm=False,
            grace_period_hours=24,
            roles=[],
            confirmation_rules=[
                TeamSizeConfirmationRule(min_team_size=1, max_team_size=3),
                RoleConfirmationRule(take_into_account_role_count=False),
            ],
        )
        try:
            await track_repository.save(track)
            result = await track_repository.get_by_id(track.id)

            assert isinstance(result.confirmation_rules[0], TeamSizeConfirmationRule)
            assert isinstance(result.confirmation_rules[1], RoleConfirmationRule)
        finally:
            await cleanup_db(pool)
