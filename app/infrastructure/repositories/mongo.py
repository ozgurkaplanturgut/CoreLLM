from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.infrastructure.repositories.base import BaseChatRepository
from app.utils.chat.schemas import ChatRequest

class MongoChatRepository(BaseChatRepository):
    """
    MongoDB implementation of the BaseChatRepository.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.req_col = "chat_requests"
        self.msg_col = "chat_messages"

    async def create_chat_request_log(self, req: ChatRequest):
        """Creates a new chat request log."""
        await self.db[self.req_col].insert_one({
            "request_id": req.request_id,
            "user_id": req.user_id,
            "session_id": req.session_id,
            "created_at": req.created_at,
            "status": "queued",
        })

    async def mark_request_status(self, request_id: str, status: str, extra: Optional[Dict[str, Any]] = None):
        """Marks the status of a chat request."""
        upd: Dict[str, Any] = {"status": status, "updated_at": datetime.utcnow()}
        
        if status == "processing":
            upd["started_at"] = datetime.utcnow()
        elif status in ("success", "error"):
            upd["finished_at"] = datetime.utcnow()
        
        if extra:
            upd.update(extra)
        
        await self.db[self.req_col].update_one({"request_id": request_id}, {"$set": upd})

    async def save_message(self, user_id: Optional[str], session_id: str, role: str, content: str):
        """Saves a new message."""
        await self.db[self.msg_col].insert_one({
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow(),
        })

    async def get_session_history(self, user_id: Optional[str], session_id: str, max_pairs: int = 20):
        """Retrieves the session history."""
        q: Dict[str, Any] = {"session_id": session_id}
        if user_id:
            q["user_id"] = user_id
        
        cursor = self.db[self.msg_col].find(q).sort("created_at", -1).limit(max_pairs)
        docs = await cursor.to_list(length=max_pairs)
        docs.reverse()
        return docs