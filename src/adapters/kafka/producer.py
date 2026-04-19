from aiokafka import AIOKafkaProducer as AsyncKafkaProducer


class KafkaProducer:
    def __init__(self, producer: AsyncKafkaProducer) -> None:
        self._producer = producer
