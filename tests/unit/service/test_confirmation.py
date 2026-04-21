import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track
from src.domain.entities.role import Role
from src.domain.errors import InvalidStatusTransitionError
from src.domain.value_objects.team_status import TeamStatus
from src.service.confirmation import ConfirmationService
from src.service.errors import ApplicationNotFoundError, TrackNotFoundError

from tests.unit.service.conftest import (
    FakeTeamApplicationRepository,
    FakeTrackRepository,
)
from src.domain.value_objects.confirmation_rule import (
    TeamSizeConfirmationRule,
)


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestCreateTeam:
    async def test_sets_status_none_and_saves(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
    ):
        application = TeamApplication(
            id=uuid.uuid4(),
            track_id=track.id,
            name="New Team",
            status=TeamStatus.CONFIRMED,
        )

        await service.create_team(application)

        assert application.status == TeamStatus.NONE
        assert app_repo.store[application.id] is application


class TestSubmitTeam:
    async def test_submit_missing_application_raises(
        self,
        service: ConfirmationService,
        valid_application: TeamApplication,
    ):
        with pytest.raises(ApplicationNotFoundError) as exc_info:
            await service.submit_team(valid_application)
        assert exc_info.value.application_id == valid_application.id

    async def test_submit_confirmed_is_noop(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.CONFIRMED
        app_repo.store[valid_application.id] = valid_application

        await service.submit_team(valid_application)

        assert app_repo.save_calls == []

    async def test_submit_missing_track_raises(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        app_repo.store[valid_application.id] = valid_application
        valid_application.track_id = uuid.uuid4()

        with pytest.raises(TrackNotFoundError):
            await service.submit_team(valid_application)

    async def test_submit_valid_application_becomes_validated(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        app_repo.store[valid_application.id] = valid_application

        await service.submit_team(valid_application)

        assert valid_application.status == TeamStatus.VALIDATED
        assert valid_application in app_repo.save_calls

    async def test_submit_with_auto_confirm_on_non_full_track_confirms(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
    ):
        track.auto_confirm = True
        app_repo.store[valid_application.id] = valid_application
        app_repo.confirmed_counts[track.id] = 0

        await service.submit_team(valid_application)

        assert valid_application.status == TeamStatus.CONFIRMED

    async def test_submit_with_auto_confirm_on_full_track_only_validates(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
    ):
        track.auto_confirm = True
        app_repo.store[valid_application.id] = valid_application
        app_repo.confirmed_counts[track.id] = track.max_team_count

        await service.submit_team(valid_application)

        assert valid_application.status == TeamStatus.VALIDATED

    async def test_submit_invalid_application_gets_rejected(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
    ):
        application = TeamApplication(
            id=uuid.uuid4(),
            track_id=track.id,
            name="Empty",
        )
        app_repo.store[application.id] = application

        await service.submit_team(application)

        assert application.status == TeamStatus.REJECTED
        assert application.rejection_reason is not None


class TestUpdateTeam:
    async def test_update_missing_application_raises(
        self,
        service: ConfirmationService,
        valid_application: TeamApplication,
    ):
        with pytest.raises(ApplicationNotFoundError):
            await service.update_team(valid_application)

    async def test_update_same_track_keeps_status_and_validates(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        app_repo.store[valid_application.id] = valid_application

        await service.update_team(valid_application)

        assert valid_application.status == TeamStatus.VALIDATED

    async def test_update_changing_track_resets_status_to_none(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track_repo: FakeTrackRepository,
        track: Track,
        valid_application: TeamApplication,
        developer_role: Role,
        designer_role: Role,
    ):
        existing = TeamApplication(
            id=valid_application.id,
            track_id=track.id,
            name="Team",
            status=TeamStatus.CONFIRMED,
        )
        app_repo.store[existing.id] = existing

        new_track = Track(
            id=uuid.uuid4(),
            name="Other",
            roles=[developer_role, designer_role],
            confirmation_rules=track.confirmation_rules,
            max_team_count=5,
        )
        track_repo.store[new_track.id] = new_track

        valid_application.track_id = new_track.id
        valid_application.status = TeamStatus.CONFIRMED

        await service.update_team(valid_application)

        assert valid_application.status == TeamStatus.VALIDATED

    async def test_update_missing_track_raises(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        app_repo.store[valid_application.id] = valid_application
        valid_application.track_id = uuid.uuid4()

        with pytest.raises(TrackNotFoundError):
            await service.update_team(valid_application)


class TestDeleteMember:
    async def test_missing_application_raises(self, service: ConfirmationService):
        with pytest.raises(ApplicationNotFoundError):
            await service.delete_member(uuid.uuid4(), uuid.uuid4())

    async def test_removes_member_and_validates(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        app_repo.store[valid_application.id] = valid_application
        victim = valid_application.members[0]

        await service.delete_member(valid_application.id, victim.id)

        assert victim not in valid_application.members
        assert valid_application in app_repo.save_calls

    async def test_removing_required_member_invalidates(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.VALIDATED
        app_repo.store[valid_application.id] = valid_application

        # Remove one member -> team size becomes 1 < min_team_size(2) AND missing role
        removed = valid_application.members[0]
        await service.delete_member(valid_application.id, removed.id)

        assert valid_application.status == TeamStatus.REJECTED

    async def test_removing_member_from_confirmed_triggers_grace_period(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.CONFIRMED
        app_repo.store[valid_application.id] = valid_application

        removed = valid_application.members[0]
        await service.delete_member(valid_application.id, removed.id)

        assert valid_application.status == TeamStatus.INVALID
        assert valid_application.grace_deadline is not None


class TestAddMember:
    async def test_missing_application_raises(
        self, service: ConfirmationService, make_member, developer_role: Role
    ):
        with pytest.raises(ApplicationNotFoundError):
            await service.add_member(uuid.uuid4(), make_member(developer_role.id))

    async def test_adds_member_and_validates(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
        make_member,
        developer_role: Role,
    ):
        app_repo.store[valid_application.id] = valid_application
        extra = make_member(developer_role.id)

        await service.add_member(valid_application.id, extra)

        assert extra in valid_application.members
        assert valid_application.status == TeamStatus.VALIDATED

    async def test_adding_member_exceeding_size_rejects(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
        make_member,
        developer_role: Role,
    ):
        track.confirmation_rules = [
            TeamSizeConfirmationRule(min_team_size=1, max_team_size=2),
        ]
        app_repo.store[valid_application.id] = valid_application

        await service.add_member(valid_application.id, make_member(developer_role.id))

        assert valid_application.status == TeamStatus.REJECTED


class TestCreateRule:
    async def test_saves_track(
        self,
        service: ConfirmationService,
        track_repo: FakeTrackRepository,
    ):
        t = Track(id=uuid.uuid4(), name="X", roles=[], confirmation_rules=[])
        await service.create_rule(t)
        assert track_repo.save_calls == [t]
        assert track_repo.store[t.id] is t


class TestConfirmTeam:
    async def test_missing_application_raises(self, service: ConfirmationService):
        with pytest.raises(ApplicationNotFoundError):
            await service.confirm_team(uuid.uuid4())

    async def test_validated_becomes_confirmed(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.VALIDATED
        app_repo.store[valid_application.id] = valid_application

        await service.confirm_team(valid_application.id)

        assert valid_application.status == TeamStatus.CONFIRMED
        assert valid_application in app_repo.save_calls

    async def test_invalid_transition_raises(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.NONE
        app_repo.store[valid_application.id] = valid_application

        with pytest.raises(InvalidStatusTransitionError):
            await service.confirm_team(valid_application.id)


class TestRejectTeam:
    async def test_missing_application_raises(self, service: ConfirmationService):
        with pytest.raises(ApplicationNotFoundError):
            await service.reject_team(uuid.uuid4(), "nope")

    async def test_rejects_and_saves(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        app_repo.store[valid_application.id] = valid_application

        await service.reject_team(valid_application.id, "bad")

        assert valid_application.status == TeamStatus.REJECTED
        assert valid_application.rejection_reason == "bad"
        assert valid_application in app_repo.save_calls


class TestQueries:
    async def test_get_application_returns_applications_for_track(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
    ):
        other = TeamApplication(id=uuid.uuid4(), track_id=uuid.uuid4(), name="Other")
        app_repo.store[valid_application.id] = valid_application
        app_repo.store[other.id] = other

        result = await service.get_application(track.id)

        assert result == [valid_application]

    async def test_get_rule_by_track_id_returns_track(
        self,
        service: ConfirmationService,
        track: Track,
    ):
        result = await service.get_rule_by_track_id(track.id)
        assert result is track

    async def test_get_rule_by_track_id_missing_raises(
        self, service: ConfirmationService
    ):
        with pytest.raises(TrackNotFoundError):
            await service.get_rule_by_track_id(uuid.uuid4())

    async def test_get_confirmed_teams_by_track(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.CONFIRMED
        app_repo.store[valid_application.id] = valid_application

        other = TeamApplication(
            id=uuid.uuid4(),
            track_id=track.id,
            name="Other",
            status=TeamStatus.VALIDATED,
        )
        other2 = TeamApplication(
            id=uuid.uuid4(),
            track_id=track.id,
            name="Other2",
            status=TeamStatus.INVALID,
        )
        app_repo.store[other.id] = other
        app_repo.store[other2.id] = other2

        result = await service.get_confirmed_teams_by_track(track.id)

        assert valid_application in result
        assert other not in result
        assert other2 in result


class TestConfirmNextFromWaitlist:
    async def test_missing_track_raises(self, service: ConfirmationService):
        with pytest.raises(TrackNotFoundError):
            await service.confirm_next_from_waitlist(uuid.uuid4())

    async def test_full_track_is_noop(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.VALIDATED
        app_repo.store[valid_application.id] = valid_application
        app_repo.confirmed_counts[track.id] = track.max_team_count

        await service.confirm_next_from_waitlist(track.id)

        assert valid_application.status == TeamStatus.VALIDATED
        assert app_repo.save_calls == []

    async def test_no_waiting_application_is_noop(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
    ):
        app_repo.confirmed_counts[track.id] = 0

        await service.confirm_next_from_waitlist(track.id)

        assert app_repo.save_calls == []

    async def test_confirms_next_validated_application(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.VALIDATED
        app_repo.store[valid_application.id] = valid_application
        app_repo.confirmed_counts[track.id] = 0

        await service.confirm_next_from_waitlist(track.id)

        assert valid_application.status == TeamStatus.CONFIRMED
        assert valid_application in app_repo.save_calls

    async def test_does_not_confirm_when_only_non_validated_exist(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        track: Track,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.REJECTED
        app_repo.store[valid_application.id] = valid_application
        app_repo.confirmed_counts[track.id] = 0

        await service.confirm_next_from_waitlist(track.id)

        assert valid_application.status == TeamStatus.REJECTED
        assert app_repo.save_calls == []


class TestExpireGracePeriods:
    async def test_no_expired_is_noop(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
    ):
        await service.expire_grace_periods()
        assert app_repo.save_calls == []

    async def test_expires_and_rejects_invalid_applications(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        valid_application.status = TeamStatus.INVALID
        valid_application.grace_deadline = datetime.now(timezone.utc) - timedelta(
            hours=1
        )
        app_repo.store[valid_application.id] = valid_application
        app_repo.expired = [valid_application]

        await service.expire_grace_periods()

        assert valid_application.status == TeamStatus.REJECTED
        assert valid_application.rejection_reason == "Grace period expired"
        assert valid_application in app_repo.save_calls

    async def test_expires_non_invalid_is_noop_but_still_saves(
        self,
        service: ConfirmationService,
        app_repo: FakeTeamApplicationRepository,
        valid_application: TeamApplication,
    ):
        # Defensive: if repository returns something that happens not to be INVALID,
        # expire_grace_period is a noop but the service still calls save.
        valid_application.status = TeamStatus.VALIDATED
        app_repo.store[valid_application.id] = valid_application
        app_repo.expired = [valid_application]

        await service.expire_grace_periods()

        assert valid_application.status == TeamStatus.VALIDATED
        assert valid_application in app_repo.save_calls
