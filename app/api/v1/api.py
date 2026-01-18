"""API router for version 1 of the API."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.chat import router as chat_router

api_router = APIRouter()
api_router.include_router(chat_router)
