from aiokafka import AIOKafkaConsumer as AsyncKafkaConsumer
from src.service.confirmation import ConfirmationService


class KafkaConsumerController:
    def __init__(
        self, consumer: AsyncKafkaConsumer, service: ConfirmationService
    ) -> None:
        self._consumer = consumer
        self._service = service

    async def start(self) -> None: ...
