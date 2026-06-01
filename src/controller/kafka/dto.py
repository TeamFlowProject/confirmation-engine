import uuid
from typing import Optional
from pydantic import BaseModel


class ParticipantDTO(BaseModel):
    id: uuid.UUID
    name: str
    surname: str
    patronymic: str
    role_id: Optional[uuid.UUID] = None


class TrackRoleDTO(BaseModel):
    id: uuid.UUID
    name: str
    count: int


class TrackCreatedDTO(BaseModel):
    id: uuid.UUID
    name: str
    required_roles: list[TrackRoleDTO] = []


class TrackUpdatedDTO(TrackCreatedDTO):
    pass


class TeamCreatedDTO(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    event_id: uuid.UUID
    owner: ParticipantDTO
    name: str
    description: str
    status: str
    created_at: str
    updated_at: str


class TeamSubmittedDTO(TeamCreatedDTO):
    pass


class TeamUpdatedDTO(TeamCreatedDTO):
    pass


class TeamDeletedDTO(TeamCreatedDTO):
    pass


class MemberKickedDTO(TeamCreatedDTO):
    member: ParticipantDTO


class MemberLeftDTO(MemberKickedDTO):
    pass


class MemberRoleChangedDTO(MemberKickedDTO):
    previous_role_id: Optional[uuid.UUID] = None


MemberJoinedDTO = MemberKickedDTO
