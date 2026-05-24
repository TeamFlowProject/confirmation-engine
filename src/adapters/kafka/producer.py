import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def start(self) -> None:
        try:
            await self._producer.start()
            logger.info("Kafka producer started")
        except KafkaError as e:
            logger.exception("Failed to start Kafka producer: %s", e)
            raise

    async def stop(self) -> None:
        try:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
        except KafkaError as e:
            logger.exception("Failed to stop Kafka producer gracefully: %s", e)
            raise

    async def send(self, topic: str, key: bytes, value: bytes) -> None:
        try:
            await self._producer.send_and_wait(topic=topic, key=key, value=value)
        except KafkaError as e:
            logger.exception("Failed to send to topic=%s: %s", topic, e)
            raise
