import asyncio
import logging
from typing import Optional
 
from src.adapters.workers.kafka_producer_protocol import KafkaProducerProtocol
 
logger = logging.getLogger(__name__)
 
 
class OutboxWorker:
    def __init__(
        self,
        producer: KafkaProducerProtocol,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self._producer = producer
        self._poll_interval = poll_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
 
    async def start(self) -> None:
        if self._running:
            return
        await self._producer.start()
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Outbox worker started")
 
    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._producer.stop()
        logger.info("Outbox worker stopped")
 
    async def _run(self) -> None:
        while self._running:
            try:
                await self._producer.send_pending()
                await asyncio.sleep(self._poll_interval)
            except Exception as e:
                logger.error("Unexpected error in outbox worker: %s", e, exc_info=True)
                await asyncio.sleep(5)
 