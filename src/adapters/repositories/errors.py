class TrackError(Exception):
    ...


class TrackAlreadyExistsError(TrackError):
    ...


class TrackRelatedEntityNotFoundError(TrackError):
    ...


class TrackNotFoundError(TrackError):
    ...
