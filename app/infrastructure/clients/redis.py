import redis.asyncio as redis
from app.core.config import get_settings

class RedisClientManager:
    """Manages the Redis client connection."""
    _client = None

    @classmethod
    def get_client(cls):
        """Returns the Redis client instance."""
        if cls._client is None:
            settings = get_settings()
            cls._client = redis.from_url(settings.redis_url, decode_responses=True)
        return cls._client

    @classmethod
    async def close(cls):
        """Closes the Redis client connection."""
        if cls._client:
            await cls._client.close()
            cls._client = None