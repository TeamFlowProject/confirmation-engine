import asyncio

import psycopg_pool
import uvicorn
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI
from loguru import logger

from src.adapters.kafka.producer import KafkaProducer
from src.adapters.repositories.team_application.postgres.repository import (
    TeamApplicationPostgresRepository,
)
from src.adapters.repositories.track.postgres.repository import TrackPostgresRepository
from src.config import Settings
from src.controller.kafka.consumer import KafkaConsumerController
from src.controller.rest.v1.confirmation_router import create_confirmation_router
from src.service.confirmation import ConfirmationService

from src.adapters.workers.outbox_worker import OutboxWorker


async def run_application(settings: Settings) -> None:
    logger.debug("Connecting to database: {}", settings.database_dsn)
    db_pool = psycopg_pool.AsyncConnectionPool(
        settings.database_dsn,
        open=False,
    )
    await db_pool.open()
    team_application_repository = TeamApplicationPostgresRepository(db_pool)  # type: ignore
    track_repository = TrackPostgresRepository(db_pool)  # type: ignore
    logger.debug("Database connection established")

    logger.debug("Starting Kafka producer: {}", settings.kafka_bootstrap)
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap)
    await producer.start()
    kafka_producer = KafkaProducer(producer)
    logger.debug("Kafka producer started")

    outbox_worker = OutboxWorker(kafka_producer)
    logger.debug("OutboxWorker initialized")

    service = ConfirmationService(team_application_repository, track_repository)
    logger.debug("ConfirmationService initialized")

    fastapi_app = FastAPI(title="Confirmation Engine")
    confirmation_router = create_confirmation_router(service)
    fastapi_app.include_router(confirmation_router)
    logger.debug("HTTP router registered")

    consumer = AIOKafkaConsumer(
        settings.kafka_topic_events,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=settings.kafka_group_id,
    )
    kafka_consumer = KafkaConsumerController(consumer, service)
    logger.debug(
        "Kafka consumer created: topic={}, group={}",
        settings.kafka_topic_events,
        settings.kafka_group_id,
    )

    uvicorn_config = uvicorn.Config(
        fastapi_app, host=settings.http_host, port=settings.http_port
    )
    server = uvicorn.Server(uvicorn_config)
    logger.info("Starting service on {}:{}", settings.http_host, settings.http_port)

    try:
        await asyncio.gather(
            server.serve(),
            kafka_consumer.start(),
            outbox_worker.start(),
        )
    finally:
        logger.debug("Shutting down")
        await consumer.stop()
        await producer.stop()
        await outbox_worker.stop()
        await db_pool.close()
        logger.info("Shutdown complete")
