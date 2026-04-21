import uuid

import pytest

from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track
from src.domain.entities.member import Member
from src.domain.entities.role import Role
from src.domain.value_objects.confirmation_rule import (
    ConfirmationRuleType,
    RoleConfirmationRule,
    TeamSizeConfirmationRule,
)


pytestmark = pytest.mark.unit


def _member(role_id: uuid.UUID) -> Member:
    return Member(
        id=uuid.uuid4(),
        name="N",
        surname="S",
        patronymic="P",
        role_id=role_id,
    )


def _app(track_id: uuid.UUID, members: list[Member]) -> TeamApplication:
    return TeamApplication(
        id=uuid.uuid4(), track_id=track_id, name="T", members=members
    )


def _track(roles: list[Role]) -> Track:
    return Track(id=uuid.uuid4(), name="T", roles=roles, confirmation_rules=[])


class TestTeamSizeRule:
    def test_rule_type(self):
        assert TeamSizeConfirmationRule().rule_type == ConfirmationRuleType.TEAM_SIZE

    def test_team_too_small(self):
        track = _track([])
        app = _app(track.id, [])
        rule = TeamSizeConfirmationRule(min_team_size=2, max_team_size=5)

        reason = rule.check(app, track)

        assert reason is not None
        assert "Team too small" in reason
        assert "0" in reason
        assert "2" in reason

    def test_team_too_large(self):
        role_id = uuid.uuid4()
        track = _track([])
        app = _app(track.id, [_member(role_id) for _ in range(6)])
        rule = TeamSizeConfirmationRule(min_team_size=1, max_team_size=5)

        reason = rule.check(app, track)

        assert reason is not None
        assert "Team too large" in reason

    def test_within_bounds(self):
        role_id = uuid.uuid4()
        track = _track([])
        app = _app(track.id, [_member(role_id), _member(role_id)])
        rule = TeamSizeConfirmationRule(min_team_size=1, max_team_size=5)

        assert rule.check(app, track) is None

    @pytest.mark.parametrize("size", [1, 5])
    def test_boundary_sizes_valid(self, size: int):
        role_id = uuid.uuid4()
        track = _track([])
        app = _app(track.id, [_member(role_id) for _ in range(size)])
        rule = TeamSizeConfirmationRule(min_team_size=1, max_team_size=5)

        assert rule.check(app, track) is None


class TestRoleRule:
    def test_rule_type(self):
        assert RoleConfirmationRule().rule_type == ConfirmationRuleType.ROLE

    def test_missing_role_without_count_check(self):
        role = Role(id=uuid.uuid4(), name="Dev", count=3)
        track = _track([role])
        app = _app(track.id, [])
        rule = RoleConfirmationRule(take_into_account_role_count=False)

        reason = rule.check(app, track)

        assert reason is not None
        assert "Missing required role 'Dev'" in reason

    def test_present_role_without_count_check_passes_regardless_of_count(self):
        role = Role(id=uuid.uuid4(), name="Dev", count=3)
        track = _track([role])
        app = _app(track.id, [_member(role.id)])
        rule = RoleConfirmationRule(take_into_account_role_count=False)

        assert rule.check(app, track) is None

    def test_exact_count_required(self):
        role = Role(id=uuid.uuid4(), name="Dev", count=2)
        track = _track([role])
        app = _app(track.id, [_member(role.id), _member(role.id)])
        rule = RoleConfirmationRule(take_into_account_role_count=True)

        assert rule.check(app, track) is None

    def test_wrong_count(self):
        role = Role(id=uuid.uuid4(), name="Dev", count=2)
        track = _track([role])
        app = _app(track.id, [_member(role.id)])
        rule = RoleConfirmationRule(take_into_account_role_count=True)

        reason = rule.check(app, track)

        assert reason is not None
        assert "Role 'Dev'" in reason
        assert "expected 2" in reason
        assert "got 1" in reason

    def test_multiple_roles_first_failure_returned(self):
        role_a = Role(id=uuid.uuid4(), name="Dev", count=1)
        role_b = Role(id=uuid.uuid4(), name="Designer", count=1)
        track = _track([role_a, role_b])
        app = _app(track.id, [])
        rule = RoleConfirmationRule(take_into_account_role_count=False)

        reason = rule.check(app, track)

        assert reason is not None
        assert "Dev" in reason

    def test_all_roles_present(self):
        role_a = Role(id=uuid.uuid4(), name="Dev", count=1)
        role_b = Role(id=uuid.uuid4(), name="Designer", count=1)
        track = _track([role_a, role_b])
        app = _app(track.id, [_member(role_a.id), _member(role_b.id)])
        rule = RoleConfirmationRule(take_into_account_role_count=False)

        assert rule.check(app, track) is None

    def test_empty_track_roles_passes(self):
        track = _track([])
        app = _app(track.id, [])
        rule = RoleConfirmationRule(take_into_account_role_count=True)

        assert rule.check(app, track) is None
