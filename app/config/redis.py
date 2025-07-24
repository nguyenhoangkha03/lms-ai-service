import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import logging
from typing import Optional

from app.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global Redis connection pool
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[redis.Redis] = None

async def init_redis_pool():
    """Initialize Redis connection pool"""
    global redis_pool, redis_client
    
    try:
        redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            retry_on_timeout=True,
            decode_responses=True
        )
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise

async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if redis_client is None:
        await init_redis_pool()
    return redis_client

async def close_redis_pool():
    """Close Redis connection pool"""
    global redis_pool, redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
    
    logger.info("Redis connections closed")

# Cache utilities
class CacheManager:
    """Redis cache management utilities"""
    
    def __init__(self):
        self.default_expiry = 3600  # 1 hour
    
    async def get(self, key: str, default=None):
        """Get value from cache"""
        try:
            client = await get_redis()
            value = await client.get(key)
            return value if value is not None else default
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return default
    
    async def set(self, key: str, value: str, expiry: Optional[int] = None):
        """Set value in cache"""
        try:
            client = await get_redis()
            await client.set(key, value, ex=expiry or self.default_expiry)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    async def delete(self, key: str):
        """Delete key from cache"""
        try:
            client = await get_redis()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await get_redis()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False

# Global cache manager instance
cache = CacheManager()