import logging

from aiokafka import AIOKafkaConsumer

from src.controller.kafka.protocols import ConfirmationServiceProtocol
from src.controller.kafka.dto import (
    ParticipantDTO,
    TeamCreatedDTO,
    TeamSubmittedDTO,
    TeamUpdatedDTO,
    MemberKickedDTO,
    MemberLeftDTO,
    MemberJoinedDTO,
)
from src.service.errors import ApplicationNotFoundError, TrackNotFoundError
from src.domain.aggregates.team_application import TeamApplication
from src.domain.entities.member import Member
from src.controller.kafka.topics import TOPICS


logger = logging.getLogger(__name__)

OFFSET_ERRORS = (ApplicationNotFoundError, TrackNotFoundError)


class KafkaConsumerController:
    def __init__(
        self, сonsumer: AIOKafkaConsumer, service: ConfirmationServiceProtocol
    ) -> None:
        self._service = service
        self._consumer = сonsumer

    @staticmethod
    def _build_application(
        dto: TeamCreatedDTO | TeamSubmittedDTO | TeamUpdatedDTO,
    ) -> TeamApplication:
        """
        Строит TeamApplication из payload.

        created - name присутствует, сервис сохраняет объект как есть.
        submitted/updated - name тоже должен быть в payload, но сервис
          достаёт существующий объект из БД и использует переданный только
          для application.id и application.track_id (логика смены трека).
        """
        return TeamApplication(
            id=dto.id,
            track_id=dto.track_id,
            name=dto.name,
        )

    @staticmethod
    def _build_member(participant: ParticipantDTO) -> Member:
        return Member(
            id=participant.id,
            name=participant.name,
            surname=participant.surname,
            patronymic=participant.patronymic,
            role_id=participant.role_id,
        )

    async def handle_team_created(self, dto: TeamCreatedDTO) -> None:
        await self._service.create_team(self._build_application(dto))

    async def handle_team_submitted(self, dto: TeamSubmittedDTO) -> None:
        await self._service.submit_team(self._build_application(dto))

    async def handle_team_updated(self, dto: TeamUpdatedDTO) -> None:
        await self._service.update_team(self._build_application(dto))

    async def handle_member_removed(self, dto: MemberKickedDTO | MemberLeftDTO) -> None:
        await self._service.delete_member(dto.id, dto.member.id)

    async def handle_member_joined(self, dto: MemberJoinedDTO) -> None:
        await self._service.add_member(dto.id, self._build_member(dto.member))

    async def _dispatch(self, topic: str, dto) -> None:
        match topic:
            case "event_service.team.created":
                await self.handle_team_created(dto)
            case "event_service.team.submitted":
                await self.handle_team_submitted(dto)
            case "event_service.team.updated":
                await self.handle_team_updated(dto)
            case "event_service.team.member.kicked" | "event_service.team.member.left":
                await self.handle_member_removed(dto)
            case (
                "event_service.invitation.accepted"
                | "event_service.join_request.accepted"
            ):
                await self.handle_member_joined(dto)

    async def start(self) -> None:
        await self._consumer.start()
        logger.info("Kafka consumer started. Topics: %s", TOPICS)
        try:
            async for msg in self._consumer:
                logger.debug(
                    "Received: topic=%s partition=%s offset=%s",
                    msg.topic,
                    msg.partition,
                    msg.offset,
                )
                await self._process(msg)
        finally:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _process(self, msg) -> None:
        try:
            dto_class = TOPICS.get(msg.topic)
            if dto_class is None:
                logger.warning("Unhandled topic: %s", msg.topic)
                await self._consumer.commit()
                return

            dto = dto_class.model_validate(msg.value)
            await self._dispatch(msg.topic, dto)
            await self._consumer.commit()

        except OFFSET_ERRORS as e:
            logger.warning(
                "Skipping message: topic=%s offset=%s reason=%s",
                msg.topic,
                msg.offset,
                e,
            )
            await self._consumer.commit()

        except Exception:
            logger.exception(
                "Failed to process: topic=%s offset=%s payload=%s",
                msg.topic,
                msg.offset,
                msg.value,
            )
