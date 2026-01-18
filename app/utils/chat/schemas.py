from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Chat request schema."""
    model_config = ConfigDict(extra="forbid")

    request_id: str
    user_id: str
    session_id: str
    prompt: str

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # model validate method
    @classmethod
    def model_validate(cls, data: dict) -> ChatRequest:
        return cls(**data)

class ChatResponseEvent(BaseModel):
    """Chat response event schema."""
    model_config = ConfigDict(extra="forbid")

    request_id: str
    event_type: str  # "token", "end", "error", etc.
    content: str

    created_at: datetime = Field(default_factory=datetime.utcnow)