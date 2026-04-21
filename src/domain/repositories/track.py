import uuid
from typing import Protocol

from src.domain.aggregates.track import Track


class TrackRepository(Protocol):
    async def save(self, track: Track) -> None: ...

    async def get_by_id(self, track_id: uuid.UUID) -> Track | None: ...
