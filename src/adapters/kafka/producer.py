from aiokafka import AIOKafkaProducer as AsyncKafkaProducer


class KafkaProducer:
    def __init__(self, producer: AsyncKafkaProducer) -> None:
        self._producer = producer

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def send(
        self,
        topic: str,
        key: bytes,
        value: bytes,
    ) -> None: ...
