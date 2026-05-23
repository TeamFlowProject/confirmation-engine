from typing import Protocol


class KafkaProducerProtocol(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def send(
        self,
        topic: str,
        key: bytes,
        value: bytes,
    ) -> None: ...