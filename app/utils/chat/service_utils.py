from __future__ import annotations

import asyncio
import logging
import random
from contextlib import suppress
from functools import partial
from typing import Any, Dict, List

from app.core.config import get_settings
from app.utils.chat.schemas import ChatResponseEvent
from app.infrastructure.repositories.base import BaseChatRepository

settings = get_settings()
logger = logging.getLogger(__name__)


async def run_blocking(fn, *args, **kwargs):
    """Run sync work in a thread."""
    return await asyncio.to_thread(partial(fn, *args, **kwargs))


def backoff_seconds(retry_count: int) -> float:
    """Exponential backoff with jitter (preserves original behavior)."""
    base = float(settings.retry_base_seconds)
    cap = float(settings.retry_max_seconds)
    delay = min(cap, base * (2 ** max(0, retry_count - 1)))
    jitter = random.random() * 0.25 * delay
    return delay + jitter


async def send_event(producer, ev: ChatResponseEvent) -> None:
    """Send response event to Kafka (same topic/key/value behavior)."""
    await producer.send_and_wait(
        settings.chat_response_topic,
        key=ev.request_id,
        value=ev.model_dump(mode="json"),
    )


async def send_error_and_mark(producer, request_id: str, err: str, repository: BaseChatRepository) -> None:
    """Send error event + mark request error via repository."""
    with suppress(Exception):
        await send_event(
            producer,
            ChatResponseEvent(request_id=request_id, event_type="error", content=err),
        )
    with suppress(Exception):
        await repository.mark_request_status(request_id, "error", {"error": err})



async def send_end(producer, request_id: str) -> None:
    """Always send end event (best-effort)."""
    with suppress(Exception):
        await send_event(
            producer,
            ChatResponseEvent(request_id=request_id,
                             event_type="end", content=""),
        )


async def build_conversation_text(history_docs: List[Dict[str, Any]]) -> str:
    """Build compact conversation text from last 8 turns."""
    conv_turns: List[str] = []
    for m in (history_docs or [])[-8:]:
        role = (m.get("role") or "").upper()
        content = (m.get("content") or "").strip()
        if role and content:
            conv_turns.append(f"{role}: {content}")
    return "\n".join(conv_turns).strip()