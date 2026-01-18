from app.core.config import get_settings

from app.infrastructure.clients.mongo import MongoClientManager
from app.infrastructure.clients.redis import RedisClientManager
from app.infrastructure.repositories.mongo import MongoChatRepository
from app.infrastructure.cache.redis import RedisCacheService
from app.infrastructure.llm.openai import OpenAIProvider
from app.infrastructure.llm.vllm import VLLMProvider

class InfrastructureFactory:
    """Uygulamanın tüm dış bağımlılıklarını yöneten merkezi Factory."""

    @staticmethod
    def get_chat_repository():
        """Veritabanı sağlayıcısını döndürür."""
        db = MongoClientManager.get_db()
        return MongoChatRepository(db)

    @staticmethod
    def get_cache_service():
        """Cache sağlayıcısını döndürür."""
        redis_client = RedisClientManager.get_client()
        return RedisCacheService(redis_client)

    @staticmethod
    def get_llm_provider():
        """Ayarlara göre doğru LLM sağlayıcısını döndürür."""
        settings = get_settings()
        client_type = settings.chat_client.lower()

        if client_type == "vllm":
            return VLLMProvider(
                base_url=settings.chat_base_url,
                api_key=settings.vllm_chat_api_key,
                default_model=settings.chat_model_id
            )
        elif client_type == "openai":
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                default_model=settings.openai_model,
                timeout=settings.stream_hard_timeout
            )
        else:
            raise ValueError(f"Unsupported chat_client: {client_type}")