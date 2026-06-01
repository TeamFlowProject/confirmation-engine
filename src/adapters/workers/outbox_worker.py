import asyncio
import json
import logging
from typing import Optional

from psycopg_pool import AsyncConnectionPool

from src.adapters.workers.kafka_producer_protocol import KafkaProducerProtocol

logger = logging.getLogger(__name__)


class OutboxWorker:
    def __init__(
        self,
        producer: KafkaProducerProtocol,
        db_pool: AsyncConnectionPool,
    ) -> None:
        self._db_pool = db_pool
        self._producer = producer
        self._poll_interval = 0.2
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
            except Exception as e:
                logger.error("Unexpected error in outbox worker: %s", e, exc_info=True)
                await asyncio.sleep(5)
        await self._producer.stop()
        logger.info("Outbox worker stopped")

    async def _run(self) -> None:
        while self._running:
            try:
                await self._relay_pending_events()
                await asyncio.sleep(self._poll_interval)
            except Exception as e:
                logger.error("Unexpected error in outbox worker: %s", e, exc_info=True)
                await asyncio.sleep(5)

    async def _relay_pending_events(self) -> None:
        async with self._db_pool.connection() as conn:
            rows = await conn.execute(
                """
                SELECT id, aggregate_type, aggregate_id, event_type, payload, idempotency_key
                FROM outbox_events
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                """
            )
            events = await rows.fetchall()

        for (
            event_id,
            aggregate_type,
            aggregate_id,
            event_type,
            payload,
            idempotency_key,
        ) in events:
            await self._send_event(
                event_id,
                aggregate_type,
                aggregate_id,
                event_type,
                payload,
                idempotency_key,
            )

    async def _send_event(
        self,
        event_id,
        aggregate_type,
        aggregate_id,
        event_type,
        payload,
        idempotency_key,
    ) -> None:
        key = idempotency_key.encode() if idempotency_key else str(event_id).encode()
        value = json.dumps(
            {
                "aggregate_type": aggregate_type,
                "aggregate_id": str(aggregate_id),
                "event_type": event_type,
                "payload": payload,
            }
        ).encode()

        try:
            await self._producer.send(topic=event_type, key=key, value=value)
        except Exception as e:
            logger.error("Failed to send event %s: %s", event_id, e, exc_info=True)
            async with self._db_pool.connection() as conn:
                await conn.execute(
                    """
                    UPDATE outbox_events
                    SET retry_count = retry_count + 1,
                        error_message = %s
                    WHERE id = %s
                    """,
                    (str(e), event_id),
                )
            return

        async with self._db_pool.connection() as conn:
            await conn.execute(
                """
                UPDATE outbox_events
                SET status = 'SENT',
                    processed_at = NOW()
                WHERE id = %s AND status = 'PENDING'
                """,
                (event_id,),
            )
        logger.debug("Event %s sent and marked SENT", event_id)
