import uuid
from pydantic import BaseModel


class ParticipantDTO(BaseModel):
    id: uuid.UUID
    name: str
    surname: str
    patronymic: str
    role_id: uuid.UUID


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


MemberJoinedDTO = MemberKickedDTO
