import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.controller.rest.v1.confirmation_router import create_confirmation_router
from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track
from src.domain.entities.member import Member
from src.domain.entities.role import Role
from src.domain.errors import InvalidStatusTransitionError
from src.domain.value_objects.confirmation_rule import (
    RoleConfirmationRule,
    TeamSizeConfirmationRule,
)
from src.domain.value_objects.team_status import TeamStatus
from src.service.errors import ApplicationNotFoundError, TrackNotFoundError


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConfirmationService:
    def __init__(self) -> None:
        self.create_rule_calls: list[Track] = []
        self.confirm_team_calls: list[uuid.UUID] = []
        self.get_application_calls: list[uuid.UUID] = []
        self.get_rule_calls: list[uuid.UUID] = []
        self.get_confirmed_calls: list[uuid.UUID] = []

        self.applications_by_track: dict[uuid.UUID, list[TeamApplication]] = {}
        self.confirmed_by_track: dict[uuid.UUID, list[TeamApplication]] = {}
        self.tracks: dict[uuid.UUID, Track] = {}

        self.confirm_team_error: Exception | None = None
        self.get_rule_error: Exception | None = None

    async def create_rule(self, track: Track) -> None:
        self.create_rule_calls.append(track)

    async def confirm_team(self, application_id: uuid.UUID) -> None:
        self.confirm_team_calls.append(application_id)
        if self.confirm_team_error is not None:
            raise self.confirm_team_error

    async def get_application(self, track_id: uuid.UUID) -> list[TeamApplication]:
        self.get_application_calls.append(track_id)
        return self.applications_by_track.get(track_id, [])

    async def get_rule_by_track_id(self, track_id: uuid.UUID) -> Track:
        self.get_rule_calls.append(track_id)
        if self.get_rule_error is not None:
            raise self.get_rule_error
        return self.tracks[track_id]

    async def get_confirmed_teams_by_track(
        self, track_id: uuid.UUID
    ) -> list[TeamApplication]:
        self.get_confirmed_calls.append(track_id)
        return self.confirmed_by_track.get(track_id, [])


@pytest.fixture
def service() -> FakeConfirmationService:
    return FakeConfirmationService()


@pytest.fixture
def app(service: FakeConfirmationService) -> FastAPI:
    fastapi_app = FastAPI()
    fastapi_app.include_router(create_confirmation_router(service))
    return fastapi_app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_application(track_id: uuid.UUID, status: TeamStatus) -> TeamApplication:
    role_id = uuid.uuid4()
    return TeamApplication(
        id=uuid.uuid4(),
        track_id=track_id,
        name="Team",
        members=[
            Member(
                id=uuid.uuid4(),
                name="N",
                surname="S",
                patronymic="P",
                role_id=role_id,
            )
        ],
        status=status,
    )


def _make_track() -> Track:
    return Track(
        id=uuid.uuid4(),
        name="Main",
        roles=[Role(id=uuid.uuid4(), name="Dev", count=1)],
        confirmation_rules=[
            TeamSizeConfirmationRule(min_team_size=1, max_team_size=5),
            RoleConfirmationRule(take_into_account_role_count=True),
        ],
        max_team_count=3,
        auto_confirm=True,
        grace_period_hours=12,
    )


class TestCreateRule:
    async def test_creates_track_and_returns_201(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        track_id = uuid.uuid4()
        payload = {
            "name": "Track A",
            "roles": [{"id": str(uuid.uuid4()), "name": "Dev", "count": 2}],
            "confirmation_rules": [
                {"rule_type": "TEAM_SIZE", "min_team_size": 2, "max_team_size": 4},
                {"rule_type": "ROLE", "take_into_account_role_count": True},
            ],
            "max_team_count": 5,
            "auto_confirm": True,
            "grace_period_hours": 10,
        }

        response = await client.post(f"/rule/{track_id}", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == str(track_id)
        assert body["name"] == "Track A"
        assert body["max_team_count"] == 5
        assert body["auto_confirm"] is True
        assert body["grace_period_hours"] == 10

        assert len(service.create_rule_calls) == 1
        saved = service.create_rule_calls[0]
        assert saved.id == track_id
        assert saved.roles == []
        assert len(saved.confirmation_rules) == 2
        assert isinstance(saved.confirmation_rules[0], TeamSizeConfirmationRule)
        assert saved.confirmation_rules[0].min_team_size == 2
        assert saved.confirmation_rules[0].max_team_size == 4
        assert isinstance(saved.confirmation_rules[1], RoleConfirmationRule)
        assert saved.confirmation_rules[1].take_into_account_role_count is True

    async def test_invalid_body_returns_422(self, client: AsyncClient):
        response = await client.post(f"/rule/{uuid.uuid4()}", json={})
        assert response.status_code == 422


class TestConfirmTeam:
    async def test_confirms_team(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        application_id = uuid.uuid4()

        response = await client.post(
            "/applications", json={"application_id": str(application_id)}
        )

        assert response.status_code == 200
        assert service.confirm_team_calls == [application_id]

    async def test_application_not_found_returns_404(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        application_id = uuid.uuid4()
        service.confirm_team_error = ApplicationNotFoundError(application_id)

        response = await client.post(
            "/applications", json={"application_id": str(application_id)}
        )

        assert response.status_code == 404

    async def test_invalid_transition_returns_409(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        service.confirm_team_error = InvalidStatusTransitionError(
            TeamStatus.NONE, TeamStatus.CONFIRMED
        )

        response = await client.post(
            "/applications", json={"application_id": str(uuid.uuid4())}
        )

        assert response.status_code == 409

    async def test_invalid_body_returns_422(self, client: AsyncClient):
        response = await client.post("/applications", json={})
        assert response.status_code == 422


class TestGetApplications:
    async def test_returns_applications_for_track(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        track_id = uuid.uuid4()
        app1 = _make_application(track_id, TeamStatus.VALIDATED)
        app2 = _make_application(track_id, TeamStatus.REJECTED)
        service.applications_by_track[track_id] = [app1, app2]

        response = await client.get(f"/track/{track_id}/applications")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        ids = {item["id"] for item in body}
        assert ids == {str(app1.id), str(app2.id)}
        assert service.get_application_calls == [track_id]

    async def test_returns_empty_list_when_no_applications(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        track_id = uuid.uuid4()

        response = await client.get(f"/track/{track_id}/applications")

        assert response.status_code == 200
        assert response.json() == []

    async def test_invalid_uuid_returns_422(self, client: AsyncClient):
        response = await client.get("/track/not-a-uuid/applications")
        assert response.status_code == 422


class TestGetRule:
    async def test_returns_track(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        track = _make_track()
        service.tracks[track.id] = track

        response = await client.get(f"/rule/{track.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(track.id)
        assert body["name"] == track.name
        assert body["max_team_count"] == 3
        assert body["auto_confirm"] is True
        assert body["grace_period_hours"] == 12
        assert len(body["roles"]) == 1
        rule_types = {r["rule_type"] for r in body["confirmation_rules"]}
        assert rule_types == {"TEAM_SIZE", "ROLE"}
        assert service.get_rule_calls == [track.id]

    async def test_not_found_returns_404(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        track_id = uuid.uuid4()
        service.get_rule_error = TrackNotFoundError(track_id)

        response = await client.get(f"/rule/{track_id}")

        assert response.status_code == 404

    async def test_invalid_uuid_returns_422(self, client: AsyncClient):
        response = await client.get("/rule/not-a-uuid")
        assert response.status_code == 422


class TestGetConfirmedTeams:
    async def test_returns_confirmed_applications(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        track_id = uuid.uuid4()
        confirmed = _make_application(track_id, TeamStatus.CONFIRMED)
        service.confirmed_by_track[track_id] = [confirmed]

        response = await client.get(f"/track/{track_id}/teams")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == str(confirmed.id)
        assert body[0]["status"] == TeamStatus.CONFIRMED.value
        assert service.get_confirmed_calls == [track_id]

    async def test_returns_empty_list_when_no_confirmed(
        self, client: AsyncClient, service: FakeConfirmationService
    ):
        track_id = uuid.uuid4()

        response = await client.get(f"/track/{track_id}/teams")

        assert response.status_code == 200
        assert response.json() == []

    async def test_invalid_uuid_returns_422(self, client: AsyncClient):
        response = await client.get("/track/not-a-uuid/teams")
        assert response.status_code == 422
