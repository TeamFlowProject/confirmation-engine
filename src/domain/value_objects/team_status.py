from enum import Enum


class TeamStatus(Enum):
    NONE = "none"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    INVALID = "invalid"
