import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.controller.kafka.consumer import KafkaConsumerController, TOPICS
from src.controller.kafka.dto import (
    TeamCreatedDTO,
    TeamSubmittedDTO,
    TeamUpdatedDTO,
    MemberKickedDTO,
    MemberLeftDTO,
    MemberJoinedDTO,
)
from src.service.errors import ApplicationNotFoundError, TrackNotFoundError


def make_participant_data(**overrides) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": "Ivan",
        "surname": "Ivanov",
        "patronymic": "Ivanovich",
        "role_id": str(uuid.uuid4()),
        **overrides,
    }


def make_team_data(**overrides) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "track_id": str(uuid.uuid4()),
        "event_id": str(uuid.uuid4()),
        "owner": make_participant_data(),
        "name": "Team Alpha",
        "description": "Best team",
        "status": "created",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        **overrides,
    }


def make_member_team_data(**overrides) -> dict:
    return {
        **make_team_data(),
        "member": make_participant_data(),
        **overrides,
    }


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def controller(service: AsyncMock) -> KafkaConsumerController:
    config = MagicMock()
    config.kafka_bootstrap = "localhost:9092"
    config.kafka_group_id = "test-group"

    with patch("src.controller.kafka.consumer.AIOKafkaConsumer") as mock_consumer_cls:
        mock_consumer_cls.return_value = AsyncMock()  
        ctrl = KafkaConsumerController(service=service, config=config)

    return ctrl


def make_msg(topic: str, value: dict) -> MagicMock:
    msg = MagicMock()
    msg.topic = topic
    msg.value = value
    msg.partition = 0
    msg.offset = 0
    return msg


class TestTopicDtoMap:
    def test_all_topics_covered(self):
        from src.controller.kafka.topics import TOPICS
        for topic in TOPICS:
            assert topic in TOPICS, f"Topic {topic!r} missing from TOPICS"

    def test_dto_types(self):
        assert TOPICS["event_service.team.created"] is TeamCreatedDTO
        assert TOPICS["event_service.team.submitted"] is TeamSubmittedDTO
        assert TOPICS["event_service.team.updated"] is TeamUpdatedDTO
        assert TOPICS["event_service.member.kicked"] is MemberKickedDTO
        assert TOPICS["event_service.member.left"] is MemberLeftDTO
        assert TOPICS["event_service.invitation.accepted"] is MemberJoinedDTO
        assert TOPICS["event_service.join_request.accepted"] is MemberJoinedDTO



class TestHandleTeamCreated:
    @pytest.mark.asyncio
    async def test_calls_create_team(self, controller, service):
        data = make_team_data()
        dto = TeamCreatedDTO.model_validate(data)

        await controller.handle_team_created(dto)

        service.create_team.assert_called_once()
        application = service.create_team.call_args[0][0]
        assert application.id == dto.id
        assert application.track_id == dto.track_id
        assert application.name == dto.name


class TestHandleTeamSubmitted:
    @pytest.mark.asyncio
    async def test_calls_submit_team(self, controller, service):
        data = make_team_data()
        dto = TeamSubmittedDTO.model_validate(data)

        await controller.handle_team_submitted(dto)

        service.submit_team.assert_called_once()
        application = service.submit_team.call_args[0][0]
        assert application.id == dto.id


class TestHandleTeamUpdated:
    @pytest.mark.asyncio
    async def test_calls_update_team(self, controller, service):
        data = make_team_data()
        dto = TeamUpdatedDTO.model_validate(data)

        await controller.handle_team_updated(dto)

        service.update_team.assert_called_once()
        application = service.update_team.call_args[0][0]
        assert application.id == dto.id


class TestHandleMemberRemoved:
    @pytest.mark.asyncio
    async def test_kicked_calls_delete_member(self, controller, service):
        data = make_member_team_data()
        dto = MemberKickedDTO.model_validate(data)

        await controller.handle_member_removed(dto)

        service.delete_member.assert_called_once_with(dto.id, dto.member.id)

    @pytest.mark.asyncio
    async def test_left_calls_delete_member(self, controller, service):
        data = make_member_team_data()
        dto = MemberLeftDTO.model_validate(data)

        await controller.handle_member_removed(dto)

        service.delete_member.assert_called_once_with(dto.id, dto.member.id)


class TestHandleMemberJoined:
    @pytest.mark.asyncio
    async def test_calls_add_member(self, controller, service):
        data = make_member_team_data()
        dto = MemberJoinedDTO.model_validate(data)

        await controller.handle_member_joined(dto)

        service.add_member.assert_called_once()
        application_id, member = service.add_member.call_args[0]
        assert application_id == dto.id
        assert member.id == dto.member.id
        assert member.name == dto.member.name
        assert member.surname == dto.member.surname
        assert member.patronymic == dto.member.patronymic
        assert member.role_id == dto.member.role_id


class TestProcess:
    @pytest.mark.asyncio
    async def test_unknown_topic_commits_and_warns(self, controller, caplog):
        msg = make_msg("unknown.topic", make_team_data())

        with caplog.at_level("WARNING"):
            await controller._process(msg)

        controller._consumer.commit.assert_called_once()
        assert "Unhandled topic" in caplog.text

    @pytest.mark.asyncio
    async def test_offset_error_commits_and_warns(self, controller, service, caplog):
        service.create_team.side_effect = ApplicationNotFoundError(application_id=uuid.uuid4())
        msg = make_msg("event_service.team.created", make_team_data())

        with caplog.at_level("WARNING"):
            await controller._process(msg)

        controller._consumer.commit.assert_called_once()
        assert "Skipping message" in caplog.text

    @pytest.mark.asyncio
    async def test_track_not_found_commits_and_warns(self, controller, service, caplog):
        service.create_team.side_effect = TrackNotFoundError(track_id=uuid.uuid4())
        msg = make_msg("event_service.team.created", make_team_data())

        with caplog.at_level("WARNING"):
            await controller._process(msg)

        controller._consumer.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unexpected_exception_logs_and_does_not_commit(self, controller, service, caplog):
        service.create_team.side_effect = RuntimeError("boom")
        msg = make_msg("event_service.team.created", make_team_data())

        with caplog.at_level("ERROR"):
            await controller._process(msg)

        controller._consumer.commit.assert_not_called()
        assert "Failed to process" in caplog.text

    @pytest.mark.asyncio
    async def test_invalid_payload_logs_and_does_not_commit(self, controller, caplog):
        msg = make_msg("event_service.team.created", {"bad": "data"})

        with caplog.at_level("ERROR"):
            await controller._process(msg)

        controller._consumer.commit.assert_not_called()


# ---------------------------------------------------------------------------
# _process → handler integration (по одному на каждый топик)
# ---------------------------------------------------------------------------

class TestProcessDispatchIntegration:
    @pytest.mark.asyncio
    async def test_team_created(self, controller, service):
        msg = make_msg("event_service.team.created", make_team_data())
        await controller._process(msg)
        service.create_team.assert_called_once()

    @pytest.mark.asyncio
    async def test_team_submitted(self, controller, service):
        msg = make_msg("event_service.team.submitted", make_team_data())
        await controller._process(msg)
        service.submit_team.assert_called_once()

    @pytest.mark.asyncio
    async def test_team_updated(self, controller, service):
        msg = make_msg("event_service.team.updated", make_team_data())
        await controller._process(msg)
        service.update_team.assert_called_once()

    @pytest.mark.asyncio
    async def test_member_kicked(self, controller, service):
        msg = make_msg("event_service.member.kicked", make_member_team_data())
        await controller._process(msg)
        service.delete_member.assert_called_once()

    @pytest.mark.asyncio
    async def test_member_left(self, controller, service):
        msg = make_msg("event_service.member.left", make_member_team_data())
        await controller._process(msg)
        service.delete_member.assert_called_once()

    @pytest.mark.asyncio
    async def test_invitation_accepted(self, controller, service):
        msg = make_msg("event_service.invitation.accepted", make_member_team_data())
        await controller._process(msg)
        service.add_member.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_request_accepted(self, controller, service):
        msg = make_msg("event_service.join_request.accepted", make_member_team_data())
        await controller._process(msg)
        service.add_member.assert_called_once()