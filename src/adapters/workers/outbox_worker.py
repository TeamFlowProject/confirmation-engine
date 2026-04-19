from src.adapters.kafka.producer import KafkaProducer


class OutboxWorker:
    def __init__(self, producer: KafkaProducer) -> None:
        self._producer = producer

    async def start(self) -> None: ...

    async def stop(self) -> None: ...
