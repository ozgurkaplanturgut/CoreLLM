from __future__ import annotations
from typing import AsyncIterator
from openai import AsyncOpenAI

from app.infrastructure.llm.base import BaseLLMProvider

class VLLMProvider(BaseLLMProvider):
    """VLLM provider for chat interactions."""
    def __init__(self, base_url: str, api_key: str, default_model: str):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.default_model = default_model

    async def stream_chat(
        self, 
        prompt: str, 
        history: str = "", 
        model_override: str | None = None
    ) -> AsyncIterator[str]:
        """Streams chat responses from the VLLM model."""
        full_prompt = self._build_prompt(prompt, history)
        model = model_override or self.default_model

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