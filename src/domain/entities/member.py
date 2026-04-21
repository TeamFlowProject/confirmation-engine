from dataclasses import dataclass
import uuid


@dataclass
class Member:
    id: uuid.UUID

    name: str
    surname: str
    patronymic: str

    role_id: uuid.UUID
