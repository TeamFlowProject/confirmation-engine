from src.domain.value_objects.team_status import TeamStatus


class InvalidStatusTransitionError(Exception):
    def __init__(self, current: TeamStatus, target: TeamStatus) -> None:
        super().__init__(
            f"Cannot transition from {current.value!r} to {target.value!r}"
        )
        self.current = current
        self.target = target
