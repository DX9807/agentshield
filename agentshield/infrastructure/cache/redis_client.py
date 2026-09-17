"""Redis client for caching and rate limiting."""

import json
from typing import Any

from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis client wrapper."""

    _instance = None
    _client: Redis | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is None:
            try:
                # Configure retry mechanism
                retry = Retry(
                    ExponentialBackoff(cap=1, base=0.5),
                    retries=3,
                )

                pool = ConnectionPool.from_url(
                    str(settings.REDIS_URL),
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    retry=retry,
                    retry_on_timeout=True,
                )

                self._client = Redis(
                    connection_pool=pool,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                )

                # Test connection
                await self._client.ping()
                logger.info("Redis connected successfully")

            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            await self._client.connection_pool.disconnect()
            self._client = None
            logger.info("Redis disconnected")

    def _ensure_connected(self):
        """Ensure Redis is connected."""
        if self._client is None:
            raise RuntimeError("Redis client not connected")

    async def get(self, key: str) -> Any | None:
        """Get a value from Redis."""
        self._ensure_connected()
        try:
            value = await self._client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.decode("utf-8")
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a value in Redis."""
        self._ensure_connected()
        try:
            if not isinstance(value, str):
                value = json.dumps(value)

            result = await self._client.set(
                key,
                value,
                ex=ttl,
                nx=nx,
                xx=xx,
            )
            return bool(result)

        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        self._ensure_connected()
        try:
            return await self._client.delete(*keys)
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Redis delete error: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        self._ensure_connected()
        try:
            return await self._client.exists(*keys)
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Redis exists error: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key."""
        self._ensure_connected()
        try:
            return await self._client.expire(key, ttl)
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Redis expire error: {e}")
            return False

    async def incr(self, key: str, amount: int = 1) -> int | None:
        """Increment a counter."""
        self._ensure_connected()
        try:
            return await self._client.incrby(key, amount)
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Redis incr error: {e}")
            return None

    async def incr_with_expire(self, key: str, ttl: int, amount: int = 1) -> int | None:
        """Increment a counter and set expiration if not set."""
        self._ensure_connected()
        try:
            # Use pipeline for atomicity
            pipe = self._client.pipeline()
            pipe.incrby(key, amount)
            pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Redis incr_with_expire error: {e}")
            return None

    async def pipeline(self):
        """Get a Redis pipeline."""
        self._ensure_connected()
        return self._client.pipeline()


# Singleton instance
redis_client = RedisClient()


async def get_redis() -> Redis:
    """Dependency for FastAPI."""
    return redis_client
