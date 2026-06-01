from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass
class Member:
    id: uuid.UUID

    name: str
    surname: str
    patronymic: str

    role_id: Optional[uuid.UUID] = None
