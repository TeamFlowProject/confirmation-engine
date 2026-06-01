import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=_utc_now)

    @property
    def topic(self) -> str:
        """Название Kafka-топика, в который публикуется событие."""
        raise NotImplementedError(f"{type(self).__name__} must define a Kafka topic")


@dataclass(frozen=True)
class TeamValidated(DomainEvent):
    TOPIC: ClassVar[str] = "confirmation_engine.team.validated"

    application_id: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def topic(self) -> str:
        return self.TOPIC


@dataclass(frozen=True)
class TeamConfirmed(DomainEvent):
    TOPIC: ClassVar[str] = "confirmation_engine.team.confirmed"

    application_id: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def topic(self) -> str:
        return self.TOPIC


@dataclass(frozen=True)
class TeamRejected(DomainEvent):
    TOPIC: ClassVar[str] = "confirmation_engine.team.rejected"

    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    reason: str = ""

    @property
    def topic(self) -> str:
        return self.TOPIC


@dataclass(frozen=True)
class TeamBecameInvalid(DomainEvent):
    TOPIC: ClassVar[str] = "confirmation_engine.team.became_invalid"

    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    grace_deadline: datetime | None = None

    @property
    def topic(self) -> str:
        return self.TOPIC


@dataclass(frozen=True)
class SlotReleased(DomainEvent):
    TOPIC: ClassVar[str] = "confirmation_engine.team.slot_released"

    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    track_id: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def topic(self) -> str:
        return self.TOPIC
