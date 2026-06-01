import uuid
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track
from src.domain.entities.member import Member
from src.domain.entities.role import Role
from src.domain.value_objects.confirmation_rule import (
    ConfirmationRule,
    RoleConfirmationRule,
    TeamSizeConfirmationRule,
)
from src.domain.value_objects.team_status import TeamStatus


class MemberSchema(BaseModel):
    id: uuid.UUID
    name: str
    surname: str
    patronymic: str
    role_id: uuid.UUID | None = None

    @classmethod
    def from_domain(cls, member: Member) -> "MemberSchema":
        return cls(
            id=member.id,
            name=member.name,
            surname=member.surname,
            patronymic=member.patronymic,
            role_id=member.role_id,
        )


class TeamApplicationResponse(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    name: str
    members: list[MemberSchema]
    status: TeamStatus
    rejection_reason: str | None = None

    @classmethod
    def from_domain(cls, application: TeamApplication) -> "TeamApplicationResponse":
        return cls(
            id=application.id,
            track_id=application.track_id,
            name=application.name,
            members=[MemberSchema.from_domain(m) for m in application.members],
            status=application.status,
            rejection_reason=application.rejection_reason,
        )


class RoleSchema(BaseModel):
    id: uuid.UUID
    name: str
    count: int

    def to_domain(self) -> Role:
        return Role(id=self.id, name=self.name, count=self.count)

    @classmethod
    def from_domain(cls, role: Role) -> "RoleSchema":
        return cls(id=role.id, name=role.name, count=role.count)


class RoleConfirmationRuleSchema(BaseModel):
    rule_type: Literal["ROLE"] = "ROLE"
    take_into_account_role_count: bool = False

    def to_domain(self) -> RoleConfirmationRule:
        return RoleConfirmationRule(
            take_into_account_role_count=self.take_into_account_role_count
        )


class TeamSizeConfirmationRuleSchema(BaseModel):
    rule_type: Literal["TEAM_SIZE"] = "TEAM_SIZE"
    min_team_size: int = 1
    max_team_size: int = 10

    def to_domain(self) -> TeamSizeConfirmationRule:
        return TeamSizeConfirmationRule(
            min_team_size=self.min_team_size,
            max_team_size=self.max_team_size,
        )


ConfirmationRuleSchema = Annotated[
    Union[RoleConfirmationRuleSchema, TeamSizeConfirmationRuleSchema],
    Field(discriminator="rule_type"),
]


def _rule_to_schema(
    rule: ConfirmationRule,
) -> RoleConfirmationRuleSchema | TeamSizeConfirmationRuleSchema:
    if isinstance(rule, RoleConfirmationRule):
        return RoleConfirmationRuleSchema(
            take_into_account_role_count=rule.take_into_account_role_count
        )
    if isinstance(rule, TeamSizeConfirmationRule):
        return TeamSizeConfirmationRuleSchema(
            min_team_size=rule.min_team_size,
            max_team_size=rule.max_team_size,
        )
    raise ValueError(f"Unknown rule type: {type(rule)}")


class TrackRequest(BaseModel):
    model_config = {"extra": "ignore"}

    name: str
    confirmation_rules: list[ConfirmationRuleSchema] = Field(default_factory=list)
    max_team_count: int = 0
    auto_confirm: bool = False
    grace_period_hours: int = 24

    def to_domain(self, track_id: uuid.UUID) -> Track:
        return Track(
            id=track_id,
            name=self.name,
            roles=[],
            confirmation_rules=[r.to_domain() for r in self.confirmation_rules],
            max_team_count=self.max_team_count,
            auto_confirm=self.auto_confirm,
            grace_period_hours=self.grace_period_hours,
        )


class TrackResponse(BaseModel):
    id: uuid.UUID
    name: str
    roles: list[RoleSchema]
    confirmation_rules: list[
        Union[RoleConfirmationRuleSchema, TeamSizeConfirmationRuleSchema]
    ]
    max_team_count: int
    auto_confirm: bool
    grace_period_hours: int

    @classmethod
    def from_domain(cls, track: Track) -> "TrackResponse":
        return cls(
            id=track.id,
            name=track.name,
            roles=[RoleSchema.from_domain(r) for r in track.roles],
            confirmation_rules=[_rule_to_schema(r) for r in track.confirmation_rules],
            max_team_count=track.max_team_count,
            auto_confirm=track.auto_confirm,
            grace_period_hours=track.grace_period_hours,
        )


class ConfirmTeamRequest(BaseModel):
    application_id: uuid.UUID
