from __future__ import annotations

import logging
import time
from contextlib import suppress

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import OffsetAndMetadata, TopicPartition

from app.core.config import get_settings
from app.core.logging import configure_logging


configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

RETRY_HEADER = b"x-retry"


def get_retry_count(msg) -> int:
    """Read retry count from Kafka message headers."""
    try:
        for k, v in (msg.headers or []):
            if k == RETRY_HEADER and v is not None:
                return int(v.decode("utf-8"))
    except Exception:
        pass
    return 0


def with_retry_header(headers, retry_count: int):
    """Return headers with updated x-retry."""
    h = list(headers or [])
    h = [(k, v) for (k, v) in h if k != RETRY_HEADER]
    h.append((RETRY_HEADER, str(retry_count).encode("utf-8")))
    return h


def backoff_seconds(retry_count: int) -> float:
    """Exponential backoff + jitter (same as original)."""
    base = float(settings.retry_base_seconds)
    cap = float(settings.retry_max_seconds)
    delay = min(cap, base * (2 ** max(0, retry_count - 1)))
    jitter = (time.time() % 1.0) * 0.25 * delay
    return delay + jitter


async def commit(consumer: AIOKafkaConsumer, msg) -> None:
    """Manual commit (enable_auto_commit=False)."""
    tp = TopicPartition(msg.topic, msg.partition)
    offsets = {tp: OffsetAndMetadata(msg.offset + 1, "")}
    await consumer.commit(offsets=offsets)


async def send_dlq(producer: AIOKafkaProducer, original_msg, err: str) -> None:
    """Send message to DLQ with metadata (behavior preserved)."""
    payload = {
        "topic": original_msg.topic,
        "partition": original_msg.partition,
        "offset": original_msg.offset,
        "timestamp_ms": int(time.time() * 1000),
        "error": err,
        "headers": [
            (
                k.decode("utf-8") if isinstance(k,
                                                (bytes, bytearray)) else str(k),
                v.decode("utf-8") if isinstance(v, (bytes, bytearray)
                                                ) else (None if v is None else str(v)),
            )
            for (k, v) in (original_msg.headers or [])
        ],
        "value": original_msg.value,
    }
    await producer.send_and_wait(settings.chat_dlq_topic, key=original_msg.key or "", value=payload)


