from src.controller.kafka.dto import (
    TeamCreatedDTO,
    TeamSubmittedDTO,
    TeamUpdatedDTO,
    MemberKickedDTO,
    MemberLeftDTO,
    MemberJoinedDTO,
)

TOPICS = {
    "event_service.team.created": TeamCreatedDTO,
    "event_service.team.submitted": TeamSubmittedDTO,
    "event_service.team.updated": TeamUpdatedDTO,
    "event_service.member.kicked": MemberKickedDTO,
    "event_service.member.left": MemberLeftDTO,
    "event_service.invitation.accepted": MemberJoinedDTO,
    "event_service.join_request.accepted": MemberJoinedDTO,
}