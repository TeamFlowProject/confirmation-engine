from src.domain.repositories.team_application import TeamApplicationRepository
from src.domain.repositories.track import TrackRepository


class ConfirmationService:
    def __init__(
        self,
        team_application_repository: TeamApplicationRepository,
        track_repository: TrackRepository,
    ) -> None:
        self._team_application_repository = team_application_repository
        self._track_repository = track_repository
