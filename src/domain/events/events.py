import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class TeamValidated(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class TeamConfirmed(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class TeamRejected(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    reason: str = ""


@dataclass(frozen=True)
class TeamBecameInvalid(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    grace_deadline: datetime | None = None


@dataclass(frozen=True)
class SlotReleased(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    track_id: uuid.UUID = field(default_factory=uuid.uuid4)
