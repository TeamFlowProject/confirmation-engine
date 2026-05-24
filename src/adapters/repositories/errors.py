class TrackError(Exception):
    ...


class TrackAlreadyExistsError(TrackError):
    ...


class TrackRelatedEntityNotFoundError(TrackError):
    ...


class TrackNotFoundError(TrackError):
    ...


class TeamApplicationError(Exception):
    ...


class TeamApplicationAlreadyExistsError(TeamApplicationError):
    ...


class TeamApplicationRelatedEntityNotFoundError(TeamApplicationError):
    ...


class TeamApplicationNotFoundError(Exception):
    ...
