import uuid
from dataclasses import dataclass


@dataclass
class Role:
    id: uuid.UUID
    name: str
    count: int
