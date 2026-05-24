import uuid

from src.domain.aggregates.team_application import TeamApplication
from src.domain.aggregates.track import Track
from src.domain.entities.member import Member
from src.domain.repositories.team_application import TeamApplicationRepository
from src.domain.repositories.track import TrackRepository
from src.domain.value_objects.team_status import TeamStatus
from src.service.errors import (
    ApplicationNotFoundError,
    ApplicationAlreadyExistsError,
    ApplicationRelatedEntityNotFoundError,
    TrackNotFoundError,
    TrackAlreadyExistsError,
    TrackRelatedEntityNotFoundError,
)
import src.adapters.repositories.errors as adapter_errors


class ConfirmationService:
    def __init__(
        self,
        team_application_repository: TeamApplicationRepository,
        track_repository: TrackRepository,
    ) -> None:
        self._team_application_repository = team_application_repository
        self._track_repository = track_repository

    async def _get_application_or_raise(
        self, application_id: uuid.UUID
    ) -> TeamApplication:
        try:
            application = await self._team_application_repository.get_by_id(application_id)
            if application is None:
                raise ApplicationNotFoundError(application_id)
            return application
        except adapter_errors.TeamApplicationNotFoundError as exc:
            raise ApplicationNotFoundError(application_id) from exc

    async def _get_track_or_raise(self, track_id: uuid.UUID) -> Track:
        try:
            track = await self._track_repository.get_by_id(track_id)
            if track is None:
                raise TrackNotFoundError(track_id)
            return track
        except adapter_errors.TrackNotFoundError as exc:
            raise TrackNotFoundError(track_id) from exc

    async def _track_is_full(self, track: Track) -> bool:
        confirmed = await self._team_application_repository.count_confirmed_by_track(
            track.id
        )
        return confirmed >= track.max_team_count

    async def _validate_and_save(
        self, application: TeamApplication, track: Track
    ) -> None:
        is_full = await self._track_is_full(track)
        application.validate(track, is_full)
        try:
            await self._team_application_repository.save(application)
        except adapter_errors.TeamApplicationAlreadyExistsError as exc:
            raise ApplicationAlreadyExistsError(application.id) from exc
        except adapter_errors.TeamApplicationRelatedEntityNotFoundError as exc:
            raise ApplicationRelatedEntityNotFoundError(
                application.id) from exc

    async def create_team(self, application: TeamApplication) -> None:
        application.status = TeamStatus.NONE
        try:
            await self._team_application_repository.save(application)
        except adapter_errors.TeamApplicationAlreadyExistsError as exc:
            raise ApplicationAlreadyExistsError(application.id) from exc
        except adapter_errors.TeamApplicationRelatedEntityNotFoundError as exc:
            raise ApplicationRelatedEntityNotFoundError(
                application.id) from exc

    async def submit_team(self, application: TeamApplication) -> None:
        existing = await self._get_application_or_raise(application.id)
        if existing.status == TeamStatus.CONFIRMED:
            return

        track = await self._get_track_or_raise(application.track_id)
        await self._validate_and_save(application, track)

    async def update_team(self, application: TeamApplication) -> None:
        existing = await self._get_application_or_raise(application.id)

        if existing.track_id != application.track_id:
            application.status = TeamStatus.NONE

        track = await self._get_track_or_raise(application.track_id)
        await self._validate_and_save(
            application, track
        )  # TODO: add slot_release if status is CONFIRMED

    async def delete_member(
        self, application_id: uuid.UUID, member_id: uuid.UUID
    ) -> None:
        application = await self._get_application_or_raise(application_id)
        application.remove_member(member_id)

        track = await self._get_track_or_raise(application.track_id)
        await self._validate_and_save(application, track)

    async def add_member(self, application_id: uuid.UUID, member: Member) -> None:
        application = await self._get_application_or_raise(application_id)
        application.add_member(member)

        track = await self._get_track_or_raise(application.track_id)
        await self._validate_and_save(application, track)

    async def create_rule(self, track: Track) -> None:
        try:
            await self._track_repository.save(track)
        except adapter_errors.TrackAlreadyExistsError as exc:
            raise TrackAlreadyExistsError(track.id) from exc
        except adapter_errors.TrackRelatedEntityNotFoundError as exc:
            raise TrackRelatedEntityNotFoundError(track.id) from exc

    async def confirm_team(self, application_id: uuid.UUID) -> None:
        application = await self._get_application_or_raise(application_id)
        application.confirm()
        try:
            await self._team_application_repository.save(application)
        except adapter_errors.TeamApplicationAlreadyExistsError as exc:
            raise ApplicationAlreadyExistsError(application.id) from exc
        except adapter_errors.TeamApplicationRelatedEntityNotFoundError as exc:
            raise ApplicationRelatedEntityNotFoundError(
                application.id) from exc

    async def reject_team(self, application_id: uuid.UUID, reason: str) -> None:
        application = await self._get_application_or_raise(application_id)
        application.reject(reason)
        try:
            await self._team_application_repository.save(application)
        except adapter_errors.TeamApplicationAlreadyExistsError as exc:
            raise ApplicationAlreadyExistsError(application.id) from exc
        except adapter_errors.TeamApplicationRelatedEntityNotFoundError as exc:
            raise ApplicationRelatedEntityNotFoundError(
                application.id) from exc

    async def get_application(self, track_id: uuid.UUID) -> list[TeamApplication]:
        return await self._team_application_repository.get_by_track_id(track_id)

    async def get_rule_by_track_id(self, track_id: uuid.UUID) -> Track:
        return await self._get_track_or_raise(track_id)

    async def get_confirmed_teams_by_track(
        self, track_id: uuid.UUID
    ) -> list[TeamApplication]:
        return await self._team_application_repository.get_confirmed_by_track_id(
            track_id
        )

    async def confirm_next_from_waitlist(self, track_id: uuid.UUID) -> None:
        track = await self._get_track_or_raise(track_id)
        if await self._track_is_full(track):
            return
        application = await self._team_application_repository.get_next_waiting_by_track(
            track_id
        )
        if application is None:
            return
        application.confirm()
        try:
            await self._team_application_repository.save(application)
        except adapter_errors.TeamApplicationAlreadyExistsError as exc:
            raise ApplicationAlreadyExistsError(application.id) from exc
        except adapter_errors.TeamApplicationRelatedEntityNotFoundError as exc:
            raise ApplicationRelatedEntityNotFoundError(
                application.id) from exc

    async def expire_grace_periods(self) -> None:
        """Called by infrastructure (scheduler/outbox worker) to reject
        teams whose grace period has expired."""
        expired = await self._team_application_repository.get_expired_invalid()
        for application in expired:
            application.expire_grace_period()
            try:
                await self._team_application_repository.save(application)
            except adapter_errors.TeamApplicationAlreadyExistsError as exc:
                raise ApplicationAlreadyExistsError(application.id) from exc
            except adapter_errors.TeamApplicationRelatedEntityNotFoundError as exc:
                raise ApplicationRelatedEntityNotFoundError(
                    application.id) from exc
