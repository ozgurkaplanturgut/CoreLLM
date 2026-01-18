from __future__ import annotations
from typing import AsyncIterator
from openai import AsyncOpenAI
from httpx import Timeout

from app.infrastructure.llm.base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI provider for chat interactions.
    """
    def __init__(self, api_key: str, default_model: str, timeout: float = 120.0):
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=Timeout(connect=10.0, read=timeout, write=10.0, pool=10.0)
        )
        self.default_model = default_model

    async def stream_chat(
        self, 
        prompt: str, 
        history: str = "", 
    ) -> AsyncIterator[str]:
        """Streams chat responses from the OpenAI model."""
        full_prompt = self._build_prompt(prompt, history)
        model = self.default_model

        stream = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a strictly grounded assistant."},
                {"role": "user", "content": full_prompt},
            ],
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            
            #stop signal
            if chunk.choices and chunk.choices[0].finish_reason == "stop":
                break