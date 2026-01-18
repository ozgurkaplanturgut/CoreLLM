from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from typing import Set

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.config import get_settings
from app.core.logging import configure_logging

from app.infrastructure.clients.mongo import MongoClientManager
from app.infrastructure.factory import InfrastructureFactory
from app.infrastructure.repositories.base import BaseChatRepository
from app.infrastructure.cache.base import BaseCacheService
from app.infrastructure.llm.base import BaseLLMProvider

from app.workers.worker_utils import (
    backoff_seconds,
    commit,
    get_retry_count,
    send_dlq,
    with_retry_header,
)

from app.utils.chat.service import (
    process_query,
    send_end,
    send_error_and_mark,
)

from app.utils.chat.schemas import ChatRequest
from app.infrastructure.factory import InfrastructureFactory

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

async def process_chat_request(
    req: ChatRequest,
    producer: AIOKafkaProducer,
    provider: BaseLLMProvider,
    repository: BaseChatRepository, 
) -> None:
    """Processes a chat request by streaming responses from the LLM provider and managing session history."""

    await repository.mark_request_status(req.request_id, "processing")

    try:
        await process_query(
            req=req, 
            producer=producer, 
            provider=provider, 
            repository=repository 
        )
    except Exception as e:
        logger.exception("Chat request failed", extra={"request_id": req.request_id, "error": str(e)})

        await send_error_and_mark(producer, req.request_id, str(e), repository)
        with suppress(Exception):
            await repository.mark_request_status(req.request_id, "error", {"error": str(e)})

    finally:
        await send_end(producer, req.request_id)

async def worker_main() -> None:
    """Main worker loop."""
    logger.info("Starting chat worker...")

    await MongoClientManager.init()

    provider: BaseLLMProvider = InfrastructureFactory.get_llm_provider()
    repository: BaseChatRepository = InfrastructureFactory.get_chat_repository()
    cache: BaseCacheService = InfrastructureFactory.get_cache_service()

    consumer = AIOKafkaConsumer(
        settings.chat_request_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.chat_worker_group_id,
        enable_auto_commit=False,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        session_timeout_ms=30000,
        heartbeat_interval_ms=3000,
        max_poll_interval_ms=10 * 60 * 1000,
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        key_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else v,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False, default=str).encode("utf-8"),
        acks="all",
        linger_ms=10,
    )

    await consumer.start()
    await producer.start()

    semaphore = asyncio.Semaphore(settings.worker_max_concurrency)
    in_flight: Set[asyncio.Task] = set()

    async def _handle_message(msg) -> None:
        try:
            try:
                req = ChatRequest.model_validate(msg.value)
            except Exception as e:
                with suppress(Exception):
                    await send_dlq(producer, msg, f"validation_error: {e}")
                await commit(consumer, msg)
                return

            request_id = req.request_id
            retry_count = get_retry_count(msg)

            is_new = await cache.acquire_idempotency(request_id, settings.idempotency_ttl_seconds)
            if not is_new:
                await commit(consumer, msg)
                return

            try:
                await process_chat_request(
                    req,
                    producer=producer,
                    provider=provider,
                    repository=repository 
                )
                await commit(consumer, msg)
                return
            except Exception as e:
                logger.exception("Processing exception, handling retry...")
                
                await cache.release_idempotency(request_id)

                if retry_count < int(settings.max_retries):
                    delay = backoff_seconds(retry_count + 1)
                    await asyncio.sleep(delay)

                    headers = with_retry_header(msg.headers, retry_count + 1)
                    await producer.send_and_wait(
                        settings.chat_request_topic,
                        key=request_id,
                        value=msg.value,
                        headers=headers,
                    )
                    await commit(consumer, msg)
                    return

                with suppress(Exception):
                    await send_dlq(producer, msg, f"max_retries_exceeded: {e}")
                await commit(consumer, msg)

        finally:
            semaphore.release()

    try:
        async for msg in consumer:
            await semaphore.acquire()
            task = asyncio.create_task(_handle_message(msg))
            in_flight.add(task)
            task.add_done_callback(lambda t: in_flight.discard(t))
    finally:
        if in_flight:
            await asyncio.gather(*in_flight, return_exceptions=True)

        with suppress(KafkaError):
            await consumer.stop()
        with suppress(KafkaError):
            await producer.stop()

        await MongoClientManager.close()
        logger.info("chat worker stopped")

if __name__ == "__main__":
    asyncio.run(worker_main())