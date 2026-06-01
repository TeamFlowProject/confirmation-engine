from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
import uuid

from src.domain.entities.member import Member
from src.domain.events import (
    DomainEvent,
    SlotReleased,
    TeamBecameInvalid,
    TeamConfirmed,
    TeamRejected,
    TeamValidated,
)
from src.domain.errors import InvalidStatusTransitionError
from src.domain.value_objects.team_status import TeamStatus

if TYPE_CHECKING:
    from src.domain.aggregates.track import Track


@dataclass
class TeamApplication:
    id: uuid.UUID
    track_id: uuid.UUID
    name: str

    members: list[Member] = field(default_factory=list)
    status: TeamStatus = TeamStatus.NONE
    rejection_reason: str | None = None
    grace_deadline: datetime | None = None

    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    def _push_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    def add_member(self, member: Member) -> None:
        self.members.append(member)

    def remove_member(self, member_id: uuid.UUID) -> None:
        self.members = [m for m in self.members if m.id != member_id]

    def change_member_role(self, member_id: uuid.UUID, new_role_id: uuid.UUID) -> bool:
        for m in self.members:
            if m.id == member_id:
                m.role_id = new_role_id
                return True
        return False

    def confirm(self) -> None:
        if self.status != TeamStatus.VALIDATED:
            raise InvalidStatusTransitionError(self.status, TeamStatus.CONFIRMED)
        self.status = TeamStatus.CONFIRMED
        self.rejection_reason = None
        self.grace_deadline = None
        self._push_event(TeamConfirmed(application_id=self.id))

    def reject(self, reason: str) -> None:
        self.status = TeamStatus.REJECTED
        self.rejection_reason = reason
        self.grace_deadline = None
        self._push_event(TeamRejected(application_id=self.id, reason=reason))

    def expire_grace_period(self) -> None:
        if self.status == TeamStatus.INVALID:
            self._push_event(
                SlotReleased(application_id=self.id, track_id=self.track_id)
            )
            self.reject("Grace period expired")

    def validate(self, track: Track, track_is_full: bool) -> None:
        old_status = self.status

        reasons: list[str] = []
        for rule in track.confirmation_rules:
            reason = rule.check(self, track)
            if reason is not None:
                reasons.append(reason)

        if not reasons:
            self._on_valid(track, old_status, track_is_full)
        else:
            self._on_invalid(track, old_status, "; ".join(reasons))

    def _on_valid(
        self, track: Track, old_status: TeamStatus, track_is_full: bool
    ) -> None:
        self.status = TeamStatus.VALIDATED
        self.rejection_reason = None
        if old_status == TeamStatus.INVALID:
            self.grace_deadline = None
            self.status = TeamStatus.CONFIRMED
        self._push_event(TeamValidated(application_id=self.id))

        if track.auto_confirm and not track_is_full:
            self.status = TeamStatus.CONFIRMED
            self._push_event(TeamConfirmed(application_id=self.id))

    def _on_invalid(self, track: Track, old_status: TeamStatus, reason: str) -> None:
        if old_status == TeamStatus.INVALID:
            return

        if old_status == TeamStatus.CONFIRMED:
            self.status = TeamStatus.INVALID
            self.grace_deadline = datetime.now(timezone.utc) + timedelta(
                hours=track.grace_period_hours
            )
            self._push_event(
                TeamBecameInvalid(
                    application_id=self.id,
                    grace_deadline=self.grace_deadline,
                )
            )
        elif old_status == TeamStatus.VALIDATED:
            self.reject(reason)
        else:
            self.reject(reason)
