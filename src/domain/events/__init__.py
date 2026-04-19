import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ApplicationSubmitted(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    team_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class ApplicationApproved(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class ApplicationRejected(DomainEvent):
    application_id: uuid.UUID = field(default_factory=uuid.uuid4)
    reason: str = ""
