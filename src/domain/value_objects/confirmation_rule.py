from __future__ import annotations

import uuid
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.aggregates.team_application import TeamApplication
    from src.domain.aggregates.track import Track


class ConfirmationRuleType(Enum):
    ROLE = "ROLE"
    TEAM_SIZE = "TEAM_SIZE"


@dataclass
class ConfirmationRule(ABC):
    @abstractmethod
    def check(self, team: TeamApplication, track: Track) -> str | None:
        """Return None if valid, or a rejection reason string."""
        ...

    @property
    @abstractmethod
    def rule_type(self) -> ConfirmationRuleType: ...


@dataclass
class RoleConfirmationRule(ConfirmationRule):
    take_into_account_role_count: bool = False

    @property
    def rule_type(self) -> ConfirmationRuleType:
        return ConfirmationRuleType.ROLE

    def check(self, team: TeamApplication, track: Track) -> str | None:
        role_map: dict[uuid.UUID, int] = {}
        for member in team.members:
            if member.role_id is None:
                continue
            role_map[member.role_id] = role_map.get(member.role_id, 0) + 1

        for role in track.roles:
            actual = role_map.get(role.id, 0)
            if self.take_into_account_role_count:
                if actual != role.count:
                    return f"Role '{role.name}': expected {role.count}, got {actual}"
            else:
                if actual == 0:
                    return f"Missing required role '{role.name}'"

        return None


@dataclass
class TeamSizeConfirmationRule(ConfirmationRule):
    min_team_size: int = 1
    max_team_size: int = 10

    @property
    def rule_type(self) -> ConfirmationRuleType:
        return ConfirmationRuleType.TEAM_SIZE

    def check(self, team: TeamApplication, track: Track) -> str | None:
        size = len(team.members)
        if size < self.min_team_size:
            return f"Team too small: {size}, minimum is {self.min_team_size}"
        if size > self.max_team_size:
            return f"Team too large: {size}, maximum is {self.max_team_size}"
        return None
