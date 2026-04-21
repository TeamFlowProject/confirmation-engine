import uuid
from datetime import datetime, timezone

import pytest

from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track
from src.domain.entities.role import Role
from src.domain.errors import InvalidStatusTransitionError
from src.domain.events import (
    SlotReleased,
    TeamBecameInvalid,
    TeamConfirmed,
    TeamRejected,
    TeamValidated,
)
from src.domain.value_objects.confirmation_rule import (
    RoleConfirmationRule,
    TeamSizeConfirmationRule,
)
from src.domain.value_objects.team_status import TeamStatus


pytestmark = pytest.mark.unit


class TestMemberManagement:
    def test_add_member(
        self, application: TeamApplication, make_member, developer_role: Role
    ):
        member = make_member(developer_role.id)
        application.add_member(member)
        assert application.members == [member]

    def test_remove_member(
        self, application: TeamApplication, make_member, developer_role: Role
    ):
        member_a = make_member(developer_role.id)
        member_b = make_member(developer_role.id)
        application.add_member(member_a)
        application.add_member(member_b)

        application.remove_member(member_a.id)

        assert application.members == [member_b]

    def test_remove_missing_member_is_noop(
        self, application: TeamApplication, make_member, developer_role: Role
    ):
        member = make_member(developer_role.id)
        application.add_member(member)
        application.remove_member(uuid.uuid4())
        assert application.members == [member]


class TestConfirm:
    def test_confirm_from_validated(self, application: TeamApplication):
        application.status = TeamStatus.VALIDATED
        application.rejection_reason = "something"

        application.confirm()

        assert application.status == TeamStatus.CONFIRMED
        assert application.rejection_reason is None
        assert application.grace_deadline is None

        events = application.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], TeamConfirmed)
        assert events[0].application_id == application.id

    @pytest.mark.parametrize(
        "status",
        [
            TeamStatus.NONE,
            TeamStatus.SUBMITTED,
            TeamStatus.CONFIRMED,
            TeamStatus.REJECTED,
            TeamStatus.INVALID,
        ],
    )
    def test_confirm_from_other_status_raises(
        self, application: TeamApplication, status: TeamStatus
    ):
        application.status = status

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            application.confirm()

        assert exc_info.value.current == status
        assert exc_info.value.target == TeamStatus.CONFIRMED


class TestReject:
    def test_reject_sets_reason_and_emits_event(self, application: TeamApplication):
        application.status = TeamStatus.VALIDATED
        application.grace_deadline = datetime.now(timezone.utc)

        application.reject("bad team")

        assert application.status == TeamStatus.REJECTED
        assert application.rejection_reason == "bad team"
        assert application.grace_deadline is None

        events = application.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], TeamRejected)
        assert events[0].reason == "bad team"
        assert events[0].application_id == application.id


class TestExpireGracePeriod:
    def test_expire_when_invalid_rejects(self, application: TeamApplication):
        application.status = TeamStatus.INVALID
        application.grace_deadline = datetime.now(timezone.utc)

        application.expire_grace_period()

        assert application.status == TeamStatus.REJECTED
        assert application.rejection_reason == "Grace period expired"

        events = application.collect_events()
        assert any(
            isinstance(e, TeamRejected) and e.reason == "Grace period expired"
            for e in events
        )

    @pytest.mark.parametrize(
        "status",
        [
            TeamStatus.NONE,
            TeamStatus.SUBMITTED,
            TeamStatus.VALIDATED,
            TeamStatus.CONFIRMED,
            TeamStatus.REJECTED,
        ],
    )
    def test_expire_from_non_invalid_is_noop(
        self, application: TeamApplication, status: TeamStatus
    ):
        application.status = status
        application.expire_grace_period()
        assert application.status == status
        assert application.collect_events() == []


class TestValidate:
    def test_valid_team_becomes_validated(
        self,
        application: TeamApplication,
        track: Track,
        make_member,
        developer_role: Role,
        designer_role: Role,
    ):
        application.add_member(make_member(developer_role.id))
        application.add_member(make_member(designer_role.id))

        application.validate(track, track_is_full=False)

        assert application.status == TeamStatus.VALIDATED
        assert application.rejection_reason is None
        events = application.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], TeamValidated)

    def test_auto_confirm_when_track_not_full(
        self,
        application: TeamApplication,
        track: Track,
        make_member,
        developer_role: Role,
        designer_role: Role,
    ):
        track.auto_confirm = True
        application.add_member(make_member(developer_role.id))
        application.add_member(make_member(designer_role.id))

        application.validate(track, track_is_full=False)

        assert application.status == TeamStatus.CONFIRMED
        events = application.collect_events()
        assert any(isinstance(e, TeamValidated) for e in events)
        assert any(isinstance(e, TeamConfirmed) for e in events)

    def test_auto_confirm_skipped_when_track_is_full(
        self,
        application: TeamApplication,
        track: Track,
        make_member,
        developer_role: Role,
        designer_role: Role,
    ):
        track.auto_confirm = True
        application.add_member(make_member(developer_role.id))
        application.add_member(make_member(designer_role.id))

        application.validate(track, track_is_full=True)

        assert application.status == TeamStatus.VALIDATED
        events = application.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], TeamValidated)

    def test_invalid_from_none_rejects(
        self, application: TeamApplication, track: Track
    ):
        application.validate(track, track_is_full=False)

        assert application.status == TeamStatus.REJECTED
        assert application.rejection_reason is not None
        events = application.collect_events()
        assert any(isinstance(e, TeamRejected) for e in events)

    def test_invalid_from_validated_rejects(
        self, application: TeamApplication, track: Track
    ):
        application.status = TeamStatus.VALIDATED

        application.validate(track, track_is_full=False)

        assert application.status == TeamStatus.REJECTED
        assert application.rejection_reason is not None

    def test_invalid_from_confirmed_triggers_grace_period(
        self, application: TeamApplication, track: Track
    ):
        from datetime import timedelta

        application.status = TeamStatus.CONFIRMED
        track.grace_period_hours = 48

        before = datetime.now(timezone.utc)
        application.validate(track, track_is_full=False)
        after = datetime.now(timezone.utc)

        assert application.status == TeamStatus.INVALID
        assert application.grace_deadline is not None
        assert before + timedelta(hours=48) <= application.grace_deadline
        assert application.grace_deadline <= after + timedelta(hours=48)

        events = application.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], TeamBecameInvalid)
        assert events[0].grace_deadline == application.grace_deadline

    def test_recovery_from_invalid_clears_deadline(
        self,
        application: TeamApplication,
        track: Track,
        make_member,
        developer_role: Role,
        designer_role: Role,
    ):
        application.status = TeamStatus.INVALID
        application.grace_deadline = datetime.now(timezone.utc)
        application.add_member(make_member(developer_role.id))
        application.add_member(make_member(designer_role.id))

        application.validate(track, track_is_full=False)

        assert application.status == TeamStatus.CONFIRMED
        assert application.grace_deadline is None

    def test_multiple_rule_failures_concatenated(
        self, application: TeamApplication, developer_role: Role
    ):
        track = Track(
            id=uuid.uuid4(),
            name="Main",
            roles=[developer_role],
            confirmation_rules=[
                TeamSizeConfirmationRule(min_team_size=5, max_team_size=10),
                RoleConfirmationRule(take_into_account_role_count=False),
            ],
        )

        application.validate(track, track_is_full=False)

        assert application.status == TeamStatus.REJECTED
        assert application.rejection_reason is not None
        assert "Team too small" in application.rejection_reason
        assert "Missing required role" in application.rejection_reason
        assert "; " in application.rejection_reason

    def test_validate_invalid_with_invalid_status_noop(
        self, application: TeamApplication, track: Track
    ):
        application.status = TeamStatus.INVALID
        application.validate(track, track_is_full=False)
        assert application.status == TeamStatus.INVALID


class TestSlotReleased:
    def test_expire_grace_period_emits_slot_released_before_rejected(
        self, application: TeamApplication
    ):
        application.status = TeamStatus.INVALID
        application.grace_deadline = datetime.now(timezone.utc)

        application.expire_grace_period()

        events = application.collect_events()
        types = [type(e) for e in events]
        assert SlotReleased in types
        assert TeamRejected in types
        assert types.index(SlotReleased) < types.index(TeamRejected)

    def test_expire_grace_period_slot_released_has_correct_ids(
        self, application: TeamApplication
    ):
        application.status = TeamStatus.INVALID
        application.grace_deadline = datetime.now(timezone.utc)

        application.expire_grace_period()

        event = next(
            e for e in application.collect_events() if isinstance(e, SlotReleased)
        )
        assert event.application_id == application.id
        assert event.track_id == application.track_id

    @pytest.mark.parametrize(
        "status",
        [
            TeamStatus.NONE,
            TeamStatus.SUBMITTED,
            TeamStatus.VALIDATED,
            TeamStatus.CONFIRMED,
            TeamStatus.REJECTED,
        ],
    )
    def test_expire_from_non_invalid_does_not_emit_slot_released(
        self, application: TeamApplication, status: TeamStatus
    ):
        application.status = status

        application.expire_grace_period()

        assert not any(
            isinstance(e, SlotReleased) for e in application.collect_events()
        )


class TestCollectEvents:
    def test_collect_clears_events(self, application: TeamApplication):
        application.status = TeamStatus.VALIDATED
        application.confirm()

        events_first = application.collect_events()
        events_second = application.collect_events()

        assert len(events_first) == 1
        assert events_second == []
