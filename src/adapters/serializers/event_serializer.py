import dataclasses
import json
import uuid
from datetime import date, datetime
from enum import Enum

from src.domain.events import DomainEvent


class DomainJSONEncoder(json.JSONEncoder):
    """JSON encoder that understands the types used inside domain events.

    json.dumps не умеет сериализовать UUID/datetime/Enum, которыми
    наполнены доменные события, поэтому обходим их явно.
    """

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
            return dataclasses.asdict(o)
        return super().default(o)


def serialize_event(event: DomainEvent) -> str:
    """Сериализует доменное событие в JSON-строку для outbox."""
    return json.dumps(dataclasses.asdict(event), cls=DomainJSONEncoder)
