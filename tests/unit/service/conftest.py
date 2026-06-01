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
from src.adapters.repositories import errors as adapter_error
from src.service.confirmation import ConfirmationService


class FakeTeamApplicationRepository:
    def __init__(self) -> None:
        self.store: dict[uuid.UUID, TeamApplication] = {}
        self.confirmed_counts: dict[uuid.UUID, int] = {}
        self.expired: list[TeamApplication] = []
        self.save_calls: list[TeamApplication] = []

    async def save(self, application: TeamApplication) -> None:
        self.save_calls.append(application)
        self.store[application.id] = application

    async def get_by_id(self, application_id: uuid.UUID) -> TeamApplication:
        result = self.store.get(application_id)
        if result is None:
            raise adapter_error.TeamApplicationNotFoundError(application_id)
        return result

    async def get_by_track_id(self, track_id: uuid.UUID) -> list[TeamApplication]:
        return [a for a in self.store.values() if a.track_id == track_id]

    async def get_confirmed_by_track_id(
        self, track_id: uuid.UUID
    ) -> list[TeamApplication]:
        from src.domain.value_objects.team_status import TeamStatus

        return [
            a
            for a in self.store.values()
            if a.track_id == track_id
            and (a.status == TeamStatus.CONFIRMED or a.status == TeamStatus.INVALID)
        ]

    async def count_confirmed_by_track(self, track_id: uuid.UUID) -> int:
        return self.confirmed_counts.get(track_id, 0)

    async def get_expired_invalid(self) -> list[TeamApplication]:
        return list(self.expired)

    async def get_next_waiting_by_track(
        self, track_id: uuid.UUID
    ) -> TeamApplication | None:
        from src.domain.value_objects.team_status import TeamStatus

        return next(
            (
                a
                for a in self.store.values()
                if a.track_id == track_id and a.status == TeamStatus.VALIDATED
            ),
            None,
        )


class FakeTrackRepository:
    def __init__(self) -> None:
        self.store: dict[uuid.UUID, Track] = {}
        self.save_calls: list[Track] = []

    async def save(self, track: Track) -> None:
        self.save_calls.append(track)
        self.store[track.id] = track

    async def get_by_id(self, track_id: uuid.UUID) -> Track:
        result = self.store.get(track_id)
        if result is None:
            raise adapter_error.TrackNotFoundError(track_id)
        return result

    async def update_roles(
        self, track_id: uuid.UUID, name: str, roles: list[Role]
    ) -> None:
        existing = self.store.get(track_id)
        if existing is None:
            self.store[track_id] = Track(
                id=track_id,
                name=name,
                roles=list(roles),
                confirmation_rules=[],
            )
        else:
            existing.name = name
            existing.roles = list(roles)


@pytest.fixture
def app_repo() -> FakeTeamApplicationRepository:
    return FakeTeamApplicationRepository()


@pytest.fixture
def track_repo() -> FakeTrackRepository:
    return FakeTrackRepository()


@pytest.fixture
def service(
    app_repo: FakeTeamApplicationRepository, track_repo: FakeTrackRepository
) -> ConfirmationService:
    return ConfirmationService(
        team_application_repository=app_repo,
        track_repository=track_repo,
    )


@pytest.fixture
def developer_role() -> Role:
    return Role(id=uuid.uuid4(), name="Developer", count=1)


@pytest.fixture
def designer_role() -> Role:
    return Role(id=uuid.uuid4(), name="Designer", count=1)


@pytest.fixture
def track(
    track_repo: FakeTrackRepository,
    developer_role: Role,
    designer_role: Role,
) -> Track:
    t = Track(
        id=uuid.uuid4(),
        name="Main",
        roles=[developer_role, designer_role],
        confirmation_rules=[
            TeamSizeConfirmationRule(min_team_size=2, max_team_size=5),
            RoleConfirmationRule(take_into_account_role_count=False),
        ],
        max_team_count=2,
        auto_confirm=False,
        grace_period_hours=24,
    )
    track_repo.store[t.id] = t
    return t


@pytest.fixture
def make_member():
    def _make(role_id: uuid.UUID) -> Member:
        return Member(
            id=uuid.uuid4(),
            name="N",
            surname="S",
            patronymic="P",
            role_id=role_id,
        )

    return _make


@pytest.fixture
def valid_application(
    track: Track,
    make_member,
    developer_role: Role,
    designer_role: Role,
) -> TeamApplication:
    return TeamApplication(
        id=uuid.uuid4(),
        track_id=track.id,
        name="Team",
        members=[make_member(developer_role.id), make_member(designer_role.id)],
    )
