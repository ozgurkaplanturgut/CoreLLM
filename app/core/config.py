from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = Field(default="sse-chatbot", validation_alias="APP_NAME")
    app_env: str = Field(default="dev", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # OpenAI
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-nano-2025-08-07",
                              validation_alias="OPENAI_MODEL")
    
    # VLLM
    chat_base_url: str = Field(
        default="http://vllm-chat:8003/v1", validation_alias="CHAT_BASE_URL")
    vllm_chat_api_key: str = Field(
        default="chat-abc123", validation_alias="VLLM_CHAT_API_KEY")
    chat_model_id: str = Field(
        default="Qwen/Qwen2.5-3B-Instruct", validation_alias="CHAT_MODEL_ID")
    
    # Chat client
    chat_client: str = Field(
        default="vllm", validation_alias="CHAT_CLIENT")  # options: openai, vllm

    # Kafka
    kafka_bootstrap_servers: str = Field(
        default="kafka:9092", validation_alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    chat_request_topic: str = Field(
        default="chat_requests", validation_alias="chat_request_topic"
    )
    chat_response_topic: str = Field(
        default="chat_responses", validation_alias="chat_response_topic"
    )
    chat_worker_group_id: str = Field(
        default="chat-worker", validation_alias="CHAT_WORKER_GROUP_ID"
    )

    # Dispatcher
    dispatcher_consumer_group: str = Field(
        default="api-dispatcher", validation_alias="DISPATCHER_CONSUMER_GROUP"
    )

    # DLQ / Retry
    chat_dlq_topic: str = Field(
        default="chat_requests_dlq", validation_alias="CHAT_DLQ_TOPIC"
    )
    max_retries: int = Field(default=5, validation_alias="MAX_RETRIES")
    retry_base_seconds: float = Field(
        default=1.0, validation_alias="RETRY_BASE_SECONDS")
    retry_max_seconds: float = Field(
        default=30.0, validation_alias="RETRY_MAX_SECONDS")

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0",
                           validation_alias="REDIS_URL")
    idempotency_ttl_seconds: int = Field(
        default=86400, validation_alias="IDEMPOTENCY_TTL_SECONDS"
    )

    # Mongo
    mongo_dsn: str = Field(default="mongodb://mongo:27017",
                           validation_alias="MONGO_DSN")
    mongo_db_name: str = Field(
        default="sse_di_chatbot", validation_alias="MONGO_DB_NAME")

    # Worker
    worker_max_concurrency: int = Field(
        default=8, validation_alias="WORKER_MAX_CONCURRENCY")

    # SSE API timeouts
    sse_heartbeat_s: float = Field(
        default=15.0, validation_alias="SSE_HEARTBEAT_S")
    sse_max_idle_s: float = Field(
        default=60.0, validation_alias="SSE_MAX_IDLE_S")
    sse_max_total_s: float = Field(
        default=180.0, validation_alias="SSE_MAX_TOTAL_S")

    # LLM stream timeouts
    stream_first_token_timeout: float = Field(
        default=30.0, validation_alias="STREAM_FIRST_TOKEN_TIMEOUT"
    )
    stream_idle_timeout: float = Field(
        default=60.0, validation_alias="STREAM_IDLE_TIMEOUT")
    stream_hard_timeout: float = Field(
        default=120.0, validation_alias="STREAM_HARD_TIMEOUT")

    @property
    def dispatcher_topics(self) -> List[str]:
        return [self.chat_response_topic]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
