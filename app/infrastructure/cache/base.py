from abc import ABC, abstractmethod

class BaseCacheService(ABC):
    @abstractmethod
    async def acquire_idempotency(self, request_id: str, ttl_seconds: int) -> bool:
        """Tries to acquire an idempotency lock for the given request ID.
        Returns True if the lock was acquired, False otherwise.
        """
        pass

    @abstractmethod
    async def release_idempotency(self, request_id: str) -> None:
        """Releases the idempotency lock for the given request ID."""
        pass