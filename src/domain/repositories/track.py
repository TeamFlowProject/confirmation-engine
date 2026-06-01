import uuid
from typing import Protocol

from src.domain.aggregates.track import Track
from src.domain.entities.role import Role


class TrackRepository(Protocol):
    async def save(self, track: Track) -> None: ...

    async def get_by_id(self, track_id: uuid.UUID) -> Track: ...

    async def update_roles(
        self, track_id: uuid.UUID, name: str, roles: list[Role]
    ) -> None: ...
