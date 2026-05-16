import json
import logging
import uuid

from aiokafka import AIOKafkaConsumer

from src.adapters.kafka.protocols import ConfirmationServiceProtocol
from src.service.errors import ApplicationNotFoundError, TrackNotFoundError
from src.domain.aggregates.team_application import TeamApplication
from src.domain.entities.member import Member
from src.adapters.kafka.topics import TOPICS

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_GROUP_ID = "confirmation_engine_group"
OFFSET_ERRORS = (ApplicationNotFoundError, TrackNotFoundError)


class KafkaConsumer:
    def __init__(self, service: ConfirmationServiceProtocol) -> None:
        self._service = service
        self._consumer = AIOKafkaConsumer(
            *TOPICS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )

    def _build_application(self, payload: dict) -> TeamApplication:
        """
        Строит TeamApplication из payload.

        created  → name присутствует, сервис сохраняет объект как есть.
        submitted/updated → name тоже должен быть в payload, но сервис
          достаёт существующий объект из БД и использует переданный только
          для application.id и application.track_id (логика смены трека).
        """
        return TeamApplication(
            id=uuid.UUID(payload["team_id"]),
            track_id=uuid.UUID(payload["track_id"]),
            name=payload["name"],
        )

    def _build_member(self, payload: dict) -> Member:
        return Member(
            id=uuid.UUID(payload["user_id"]),
            name=payload["name"],
            surname=payload["surname"],
            patronymic=payload["patronymic"],
            role_id=uuid.UUID(payload["role_id"]),
        )

    async def handle_team_created(self, payload: dict) -> None:
        application = self._build_application(payload)
        await self._service.create_team(application)

    async def handle_team_submitted(self, payload: dict) -> None:
        application = self._build_application(payload)
        await self._service.submit_team(application)

    async def handle_team_updated(self, payload: dict) -> None:
        application = self._build_application(payload)
        await self._service.update_team(application)

    async def handle_member_removed(self, payload: dict) -> None:
        application_id = uuid.UUID(payload["team_id"])
        member_id = uuid.UUID(payload["user_id"])
        await self._service.delete_member(application_id, member_id)

    async def handle_member_joined(self, payload: dict) -> None:
        application_id = uuid.UUID(payload["team_id"])
        member = self._build_member(payload)
        await self._service.add_member(application_id, member)

    async def _dispatch(self, topic: str, payload: dict) -> None:
        match topic:
            case "team_service.team.created":
                await self.handle_team_created(payload)

            case "team_service.team.submitted":
                await self.handle_team_submitted(payload)

            case "team_service.team.updated":
                await self.handle_team_updated(payload)

            case "team_service.mebmer.kicked" | "team_service.mebmer.left":
                await self.handle_member_removed(payload)

            case (
                "invitation_service.invataion.accepted"
                | "invitation_service.join_request.accepred"
            ):
                await self.handle_member_joined(payload)

            case _:
                logger.warning("Unhandled topic: %s", topic)

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
            await self._dispatch(msg.topic, msg.value)
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
