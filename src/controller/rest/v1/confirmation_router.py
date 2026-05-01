import uuid

from fastapi import APIRouter, HTTPException, status

from src.controller.rest.v1.protocols import ConfirmationService
from src.controller.rest.v1.schemas import (
    ConfirmTeamRequest,
    TeamApplicationResponse,
    TrackRequest,
    TrackResponse,
)
from src.domain.errors import InvalidStatusTransitionError
from src.service.errors import ApplicationNotFoundError, TrackNotFoundError


def create_confirmation_router(service: ConfirmationService) -> APIRouter:
    router = APIRouter()

    @router.post("/rules", status_code=status.HTTP_201_CREATED)
    async def create_rule(payload: TrackRequest) -> TrackResponse:
        track = payload.to_domain()
        await service.create_rule(track)
        return TrackResponse.from_domain(track)

    @router.post("/applications", status_code=status.HTTP_200_OK)
    async def confirm_team(payload: ConfirmTeamRequest) -> None:
        try:
            await service.confirm_team(payload.application_id)
        except ApplicationNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except InvalidStatusTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(exc)
            ) from exc

    @router.get("/track/{track_id}/applications")
    async def get_applications(track_id: uuid.UUID) -> list[TeamApplicationResponse]:
        applications = await service.get_application(track_id)
        return [TeamApplicationResponse.from_domain(a) for a in applications]

    @router.get("/rule/{track_id}")
    async def get_rule(track_id: uuid.UUID) -> TrackResponse:
        try:
            track = await service.get_rule_by_track_id(track_id)
        except TrackNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        return TrackResponse.from_domain(track)

    @router.get("/track/{track_id}/teams")
    async def get_confirmed_teams(track_id: uuid.UUID) -> list[TeamApplicationResponse]:
        applications = await service.get_confirmed_teams_by_track(track_id)
        return [TeamApplicationResponse.from_domain(a) for a in applications]

    return router
