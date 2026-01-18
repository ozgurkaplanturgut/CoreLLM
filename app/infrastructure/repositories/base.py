from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.utils.chat.schemas import ChatRequest

class BaseChatRepository(ABC):
    @abstractmethod
    async def create_chat_request_log(self, req: ChatRequest) -> None:
        """Creates a new chat request log."""
        pass

    @abstractmethod
    async def mark_request_status(
        self, 
        request_id: str, 
        status: str, 
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Marks the status of a chat request."""
        pass

    @abstractmethod
    async def save_message(
        self, 
        user_id: Optional[str], 
        session_id: str, 
        role: str, 
        content: str
    ) -> None:
        """Saves a new message."""
        pass

    @abstractmethod
    async def get_session_history(
        self, 
        user_id: Optional[str], 
        session_id: str, 
        max_pairs: int = 20
    ) -> List[Dict[str, Any]]:
        """Retrieves the session history."""
        pass