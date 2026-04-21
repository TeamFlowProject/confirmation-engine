import uuid

import pytest

from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track
from src.domain.entities.member import Member
from src.domain.entities.role import Role
from src.domain.value_objects.confirmation_rule import (
    RoleConfirmationRule,
    TeamSizeConfirmationRule,
)


@pytest.fixture
def developer_role() -> Role:
    return Role(id=uuid.uuid4(), name="Developer", count=2)


@pytest.fixture
def designer_role() -> Role:
    return Role(id=uuid.uuid4(), name="Designer", count=1)


@pytest.fixture
def make_member():
    def _make(role_id: uuid.UUID, name: str = "Ivan") -> Member:
        return Member(
            id=uuid.uuid4(),
            name=name,
            surname="Ivanov",
            patronymic="Ivanovich",
            role_id=role_id,
        )

    return _make


@pytest.fixture
def track(developer_role: Role, designer_role: Role) -> Track:
    return Track(
        id=uuid.uuid4(),
        name="Main",
        roles=[developer_role, designer_role],
        confirmation_rules=[
            TeamSizeConfirmationRule(min_team_size=2, max_team_size=5),
            RoleConfirmationRule(take_into_account_role_count=False),
        ],
        max_team_count=3,
        auto_confirm=False,
        grace_period_hours=24,
    )


@pytest.fixture
def application(track: Track) -> TeamApplication:
    return TeamApplication(
        id=uuid.uuid4(),
        track_id=track.id,
        name="The Avengers",
    )
