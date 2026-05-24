import uuid

from src.domain.errors import (
    InvalidStatusTransitionError as InvalidStatusTransitionError,
)


class ApplicationNotFoundError(Exception):
    def __init__(self, application_id: uuid.UUID) -> None:
        super().__init__(f"Application {application_id} not found")
        self.application_id = application_id


class TrackNotFoundError(Exception):
    def __init__(self, track_id: uuid.UUID) -> None:
        super().__init__(f"Track {track_id} not found")
        self.track_id = track_id


class TrackAlreadyExistsError(Exception):
    def __init__(self, track_id: uuid.UUID) -> None:
        super().__init__(f"Track {track_id} already exists")
        self.track_id = track_id


class TrackRelatedEntityNotFoundError(Exception):
    def __init__(self, track_id: uuid.UUID) -> None:
        super().__init__(f"Track {track_id} has invalid related entities")
        self.track_id = track_id


class ApplicationAlreadyExistsError(Exception):
    def __init__(self, application_id: uuid.UUID) -> None:
        super().__init__(f"Application {application_id} already exists")
        self.application_id = application_id


class ApplicationRelatedEntityNotFoundError(Exception):
    def __init__(self, application_id: uuid.UUID) -> None:
        super().__init__(f"Application {application_id} has invalid related entities")
        self.application_id = application_id
