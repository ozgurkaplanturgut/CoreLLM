from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

from aiokafka import AIOKafkaProducer

from app.core.config import get_settings
from app.core.stream_buffer import StreamBuffer
from app.infrastructure.llm.base import BaseLLMProvider
from app.infrastructure.repositories.base import BaseChatRepository
from app.utils.chat.schemas import ChatRequest, ChatResponseEvent
from app.utils.chat.service_utils import (
    build_conversation_text,
    send_end,
    send_error_and_mark,
    send_event,
)

settings = get_settings()
logger = logging.getLogger(__name__)


async def process_query(
    *,
    req: ChatRequest,
    producer: AIOKafkaProducer,
    provider: BaseLLMProvider,
    repository: BaseChatRepository,
) -> None:
    """Processes a chat query by streaming responses from the LLM provider and managing session history."""
    
    if not req.prompt or not req.session_id:
        raise RuntimeError("prompt/session_id missing")

    try:
        history_docs = await repository.get_session_history(
            req.user_id,
            req.session_id,
            max_pairs=20,
        )
        conversation_text = await build_conversation_text(history_docs)

        await repository.save_message(
            req.user_id,
            req.session_id,
            role="user",
            content=req.prompt,
        )
    except Exception as e:
        raise e

    buffer = StreamBuffer(
        on_flush=lambda chunk: send_event(
            producer,
            ChatResponseEvent(
                request_id=req.request_id,
                event_type="chunk",
                content=chunk,
            ),
        ),
        max_chars=256,
        max_interval_s=0.05,
    )

    full_response: List[str] = []
    error_msg: Optional[str] = None

    start_ts = time.monotonic()
    last_token_ts = start_ts
    got_first_token = False
    
    # Stream Task
    async def stream_llm() -> None:
        nonlocal last_token_ts, got_first_token
        
        try:
            async for delta in provider.stream_chat(
                req.prompt,
                history=conversation_text,
            ):
                if not delta:
                    continue

                if not got_first_token:
                    got_first_token = True

                last_token_ts = time.monotonic()
                full_response.append(delta)
                await buffer.add(delta)
            
        except Exception as e:
            raise e

    # Watchdog Task
    async def watchdog(target_task: asyncio.Task) -> None:
        while True:
            await asyncio.sleep(0.5)
            now = time.monotonic()

            if not got_first_token and now - start_ts > settings.stream_first_token_timeout:
                target_task.cancel()
                raise TimeoutError("first_token_timeout")

            if got_first_token and now - last_token_ts > settings.stream_idle_timeout:
                target_task.cancel()
                raise TimeoutError("stream_idle_timeout")

    stream_task = asyncio.create_task(stream_llm())
    watchdog_task = asyncio.create_task(watchdog(stream_task))

    try:
        done, _ = await asyncio.wait(
            [stream_task, watchdog_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in done:
            if task.exception():
                raise task.exception()

    except asyncio.CancelledError:
        error_msg = "Task Cancelled"
        logger.warning("[DEBUG] Stream task cancelled")
    except TimeoutError as te:
        error_msg = str(te)
        logger.error(f"[DEBUG] Timeout occurred: {te}")
    except Exception as exc:
        error_msg = str(exc)
        logger.exception(
            "CHAT streaming failed",
            extra={"request_id": req.request_id},
        )
        await send_error_and_mark(
            producer,
            req.request_id,
            "error",
            repository,
        )

    finally:
        watchdog_task.cancel()
        
        try:
            await buffer.close()
        except Exception as e:
            logger.error(f"[DEBUG] Failed to close buffer: {e}")

        await send_end(producer, req.request_id)

    if error_msg is None:
        try:
            answer = "".join(full_response).strip()

            await repository.save_message(
                req.user_id,
                req.session_id,
                role="assistant",
                content=answer,
            )

            await repository.mark_request_status(
                req.request_id,
                "success",
                {
                    "response_time_s": time.monotonic() - start_ts,
                },
            )

        except Exception as exc:
            logger.exception(
                "CHAT saving response failed",
                extra={"error": str(exc)},
            )
            await repository.mark_request_status(
                req.request_id, 
                "error", 
                {"error": f"Saving failed: {str(exc)}"}
            )
    else:
        logger.info(f"[DEBUG] Skipping DB save because error_msg is present: {error_msg}")