from redis.asyncio import Redis
from app.infrastructure.cache.base import BaseCacheService

class RedisCacheService(BaseCacheService):
    """Redis-based implementation of the BaseCacheService for idempotency handling."""
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def acquire_idempotency(self, request_id: str, ttl_seconds: int) -> bool:
        """Tries to acquire an idempotency lock for the given request ID.
        Returns True if the lock was acquired, False otherwise.
        """
        key = f"chat:done:{request_id}"
        return await self.redis.set(key, "1", ex=ttl_seconds, nx=True)

    async def release_idempotency(self, request_id: str):
        """Releases the idempotency lock for the given request ID."""
        await self.redis.delete(f"chat:done:{request_id}")