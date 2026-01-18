from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings


class MongoClientManager:
    """Manages the MongoDB client and database connection."""
    _client = None
    _db = None

    @classmethod
    async def init(cls):
        if cls._client is None:
            settings = get_settings()
            cls._client = AsyncIOMotorClient(settings.mongo_dsn)
            cls._db = cls._client[settings.mongo_db_name]

            await cls._db["chat_messages"].create_index(
                [("user_id", 1), ("session_id", 1), ("created_at", -1)],
                background=True
            )

            await cls._db["chat_requests"].create_index(
                "request_id", unique=True, background=True
            )

        return cls._db

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Returns the MongoDB database instance."""
        if cls._db is None:
            raise RuntimeError("Mongo not initialized! Call init() first.")
        return cls._db

    @classmethod
    async def close(cls):
        """Closes the MongoDB client connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
