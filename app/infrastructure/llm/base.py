from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator

class BaseLLMProvider(ABC):
    @abstractmethod
    async def stream_chat(
        self, 
        prompt: str, 
        history: str = "", 
    ) -> AsyncIterator[str]:
        """Streams chat responses based on the given prompt and conversation history."""
        pass

    def _build_prompt(self, question: str, conversation: str) -> str:
        """Prepares the prompt for the LLM."""
        conv = (conversation or "").strip()
        return f"""
            You are a reliable, multilingual AI assistant.
            CONVERSATION HISTORY:
            {conv if conv else "[No prior conversation]"}
            USER QUESTION:
            {question}
            """.strip()