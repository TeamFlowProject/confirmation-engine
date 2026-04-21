from dataclasses import dataclass
import uuid

from src.domain.entities.role import Role
from src.domain.value_objects.confirmation_rule import ConfirmationRule


@dataclass
class Track:
    id: uuid.UUID
    name: str

    roles: list[Role]
    confirmation_rules: list[ConfirmationRule]

    max_team_count: int = 0
    auto_confirm: bool = False
    grace_period_hours: int = 24
