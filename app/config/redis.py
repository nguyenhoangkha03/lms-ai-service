import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Sentinel
from redis.exceptions import ConnectionError, TimeoutError, RedisError
import json
import pickle
import logging
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager
import hashlib

from app.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global Redis connection pool and clients
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[redis.Redis] = None
redis_sentinel: Optional[Sentinel] = None

class RedisConnectionManager:
    """Advanced Redis connection management"""
    
    def __init__(self):
        self.pool = None
        self.client = None
        self.sentinel = None
        self.is_cluster = False
        self.is_sentinel = False
        self.connection_count = 0
        self.failed_connections = 0
    
    async def initialize(self):
        """Initialize Redis connections based on configuration"""
        try:
            logger.info("🔄 Initializing Redis connections...")
            
            # Determine Redis setup type
            if hasattr(settings, 'REDIS_SENTINEL_HOSTS') and settings.REDIS_SENTINEL_HOSTS:
                await self._init_sentinel()
            elif hasattr(settings, 'REDIS_CLUSTER_HOSTS') and settings.REDIS_CLUSTER_HOSTS:
                await self._init_cluster()
            else:
                await self._init_standalone()
            
            # Test connection
            await self.client.ping()
            logger.info("✅ Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis: {str(e)}")
            raise
    
    async def _init_standalone(self):
        """Initialize standalone Redis connection"""
        self.pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            retry_on_timeout=True,
            retry_on_error=[ConnectionError, TimeoutError],
            health_check_interval=30,
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 5,  # TCP_KEEPCNT
            }
        )
        
        self.client = redis.Redis(connection_pool=self.pool)
    
    async def _init_sentinel(self):
        """Initialize Redis Sentinel for high availability"""
        # This would be used in production with Redis Sentinel
        sentinel_hosts = [
            (host.split(':')[0], int(host.split(':')[1]))
            for host in settings.REDIS_SENTINEL_HOSTS.split(',')
        ]
        
        self.sentinel = Sentinel(sentinel_hosts)
        self.client = self.sentinel.master_for(
            settings.REDIS_SENTINEL_SERVICE_NAME,
            decode_responses=True
        )
        self.is_sentinel = True
    
    async def _init_cluster(self):
        """Initialize Redis Cluster"""
        # This would be used for Redis Cluster setup
        from redis.asyncio.cluster import RedisCluster
        
        startup_nodes = [
            {"host": host.split(':')[0], "port": int(host.split(':')[1])}
            for host in settings.REDIS_CLUSTER_HOSTS.split(',')
        ]
        
        self.client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            skip_full_coverage_check=True
        )
        self.is_cluster = True
    
    async def close(self):
        """Close Redis connections"""
        try:
            if self.client:
                await self.client.close()
            if self.pool:
                await self.pool.disconnect()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {str(e)}")
    
    async def health_check(self):
        """Perform Redis health check"""
        try:
            # Basic connectivity
            response = await self.client.ping()
            if not response:
                return {"status": "unhealthy", "error": "Ping failed"}
            
            # Memory usage
            info = await self.client.info("memory")
            memory_usage = info.get('used_memory_human', 'Unknown')
            
            # Connection stats
            info_clients = await self.client.info("clients")
            connected_clients = info_clients.get('connected_clients', 0)
            
            return {
                "status": "healthy",
                "memory_usage": memory_usage,
                "connected_clients": connected_clients,
                "connection_type": "cluster" if self.is_cluster else "sentinel" if self.is_sentinel else "standalone"
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

# Global connection manager
redis_manager = RedisConnectionManager()

async def init_redis_pool():
    """Initialize Redis connection pool"""
    global redis_manager
    await redis_manager.initialize()

async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if not redis_manager.client:
        await init_redis_pool()
    return redis_manager.client

async def close_redis_pool():
    """Close Redis connection pool"""
    await redis_manager.close()

class AdvancedCacheManager:
    """Advanced caching with compression, serialization, and TTL management"""
    
    def __init__(self):
        self.default_expiry = 3600  # 1 hour
        self.compression_threshold = 1024  # Compress data > 1KB
        self.max_retries = 3
        self.retry_delay = 0.1
    
    def _serialize_data(self, data: Any) -> tuple[bytes, str]:
        """Serialize data with appropriate method"""
        if isinstance(data, (str, int, float, bool)):
            return str(data).encode(), 'simple'
        elif isinstance(data, (dict, list)):
            return json.dumps(data).encode(), 'json'
        else:
            return pickle.dumps(data), 'pickle'
    
    def _deserialize_data(self, data: bytes, method: str) -> Any:
        """Deserialize data based on method"""
        if method == 'simple':
            return data.decode()
        elif method == 'json':
            return json.loads(data.decode())
        elif method == 'pickle':
            return pickle.loads(data)
        else:
            return data.decode()
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data if it exceeds threshold"""
        if len(data) > self.compression_threshold:
            import gzip
            return gzip.compress(data)
        return data
    
    def _decompress_data(self, data: bytes, is_compressed: bool = False) -> bytes:
        """Decompress data if needed"""
        if is_compressed:
            import gzip
            return gzip.decompress(data)
        return data
    
    def _generate_cache_key(self, key: str, prefix: str = None) -> str:
        """Generate standardized cache key"""
        if prefix:
            key = f"{prefix}:{key}"
        
        # Add environment prefix for isolation
        env_prefix = f"{settings.ENVIRONMENT}:ai_services"
        return f"{env_prefix}:{key}"
    
    async def get(self, key: str, default: Any = None, prefix: str = None) -> Any:
        """Get value from cache with deserialization"""
        cache_key = self._generate_cache_key(key, prefix)
        
        for attempt in range(self.max_retries):
            try:
                client = await get_redis()
                
                # Get data and metadata
                pipe = client.pipeline()
                pipe.get(cache_key)
                pipe.hget(f"{cache_key}:meta", "method")
                pipe.hget(f"{cache_key}:meta", "compressed")
                results = await pipe.execute()
                
                data, method, compressed = results
                
                if data is None:
                    return default
                
                # Deserialize
                is_compressed = compressed == 'true' if compressed else False
                raw_data = self._decompress_data(data, is_compressed)
                return self._deserialize_data(raw_data, method or 'simple')
                
            except Exception as e:
                logger.warning(f"Cache get attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Cache get failed after {self.max_retries} attempts: {str(e)}")
                    return default
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        return default
    
    async def set(self, key: str, value: Any, expiry: Optional[int] = None, prefix: str = None) -> bool:
        """Set value in cache with serialization and compression"""
        cache_key = self._generate_cache_key(key, prefix)
        expiry = expiry or self.default_expiry
        
        for attempt in range(self.max_retries):
            try:
                client = await get_redis()
                
                # Serialize data
                serialized_data, method = self._serialize_data(value)
                
                # Compress if needed
                is_compressed = len(serialized_data) > self.compression_threshold
                if is_compressed:
                    compressed_data = self._compress_data(serialized_data)
                else:
                    compressed_data = serialized_data
                
                # Store data and metadata
                pipe = client.pipeline()
                pipe.set(cache_key, compressed_data, ex=expiry)
                pipe.hset(f"{cache_key}:meta", mapping={
                    "method": method,
                    "compressed": str(is_compressed).lower(),
                    "created_at": datetime.utcnow().isoformat(),
                    "original_size": len(serialized_data),
                    "compressed_size": len(compressed_data)
                })
                pipe.expire(f"{cache_key}:meta", expiry)
                await pipe.execute()
                
                return True
                
            except Exception as e:
                logger.warning(f"Cache set attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Cache set failed after {self.max_retries} attempts: {str(e)}")
                    return False
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        return False
    
    async def delete(self, key: str, prefix: str = None) -> bool:
        """Delete key from cache"""
        cache_key = self._generate_cache_key(key, prefix)
        
        try:
            client = await get_redis()
            pipe = client.pipeline()
            pipe.delete(cache_key)
            pipe.delete(f"{cache_key}:meta")
            results = await pipe.execute()
            return sum(results) > 0
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    async def exists(self, key: str, prefix: str = None) -> bool:
        """Check if key exists in cache"""
        cache_key = self._generate_cache_key(key, prefix)
        
        try:
            client = await get_redis()
            return await client.exists(cache_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False
    
    async def expire(self, key: str, expiry: int, prefix: str = None) -> bool:
        """Set expiration for existing key"""
        cache_key = self._generate_cache_key(key, prefix)
        
        try:
            client = await get_redis()
            pipe = client.pipeline()
            pipe.expire(cache_key, expiry)
            pipe.expire(f"{cache_key}:meta", expiry)
            results = await pipe.execute()
            return all(results)
        except Exception as e:
            logger.error(f"Cache expire error: {str(e)}")
            return False
    
    async def get_ttl(self, key: str, prefix: str = None) -> int:
        """Get time to live for key"""
        cache_key = self._generate_cache_key(key, prefix)
        
        try:
            client = await get_redis()
            return await client.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error: {str(e)}")
            return -1
    
    async def get_pattern(self, pattern: str, prefix: str = None) -> List[str]:
        """Get keys matching pattern"""
        cache_pattern = self._generate_cache_key(pattern, prefix)
        
        try:
            client = await get_redis()
            return await client.keys(cache_pattern)
        except Exception as e:
            logger.error(f"Cache pattern error: {str(e)}")
            return []
    
    async def delete_pattern(self, pattern: str, prefix: str = None) -> int:
        """Delete keys matching pattern"""
        cache_pattern = self._generate_cache_key(pattern, prefix)
        
        try:
            client = await get_redis()
            keys = await client.keys(cache_pattern)
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {str(e)}")
            return 0
    
    async def get_cache_stats(self, prefix: str = None) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            client = await get_redis()
            
            # Get all keys for this prefix
            pattern = self._generate_cache_key("*", prefix)
            keys = await client.keys(pattern)
            
            # Get memory usage info
            info = await client.info("memory")
            
            # Calculate stats
            total_keys = len(keys)
            total_memory = info.get('used_memory', 0)
            
            return {
                "total_keys": total_keys,
                "memory_usage_bytes": total_memory,
                "memory_usage_human": info.get('used_memory_human', '0B'),
                "cache_hit_ratio": await self._calculate_hit_ratio(),
                "evicted_keys": info.get('evicted_keys', 0)
            }
        except Exception as e:
            logger.error(f"Cache stats error: {str(e)}")
            return {}
    
    async def _calculate_hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        try:
            client = await get_redis()
            info = await client.info("stats")
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            
            if hits + misses == 0:
                return 0.0
            
            return hits / (hits + misses)
        except Exception:
            return 0.0

# Specialized cache managers for different use cases
class AIModelCache(AdvancedCacheManager):
    """Cache manager for AI model results and embeddings"""
    
    def __init__(self):
        super().__init__()
        self.default_expiry = 7200  # 2 hours for AI results
    
    async def cache_embedding(self, text: str, model_name: str, embedding: List[float]) -> bool:
        """Cache text embedding"""
        # Create hash of text for consistent key
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        key = f"embedding:{model_name}:{text_hash}"
        return await self.set(key, embedding, expiry=86400)  # 24 hours
    
    async def get_embedding(self, text: str, model_name: str) -> Optional[List[float]]:
        """Get cached embedding"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        key = f"embedding:{model_name}:{text_hash}"
        return await self.get(key)
    
    async def cache_recommendation(self, user_id: str, rec_type: str, recommendations: List[Dict]) -> bool:
        """Cache user recommendations"""
        key = f"recommendation:{user_id}:{rec_type}"
        return await self.set(key, recommendations, expiry=3600)  # 1 hour
    
    async def get_recommendation(self, user_id: str, rec_type: str) -> Optional[List[Dict]]:
        """Get cached recommendations"""
        key = f"recommendation:{user_id}:{rec_type}"
        return await self.get(key)

class SessionCache(AdvancedCacheManager):
    """Cache manager for user sessions and temporary data"""
    
    def __init__(self):
        super().__init__()
        self.default_expiry = 1800  # 30 minutes for sessions
    
    async def store_session(self, session_id: str, data: Dict) -> bool:
        """Store session data"""
        key = f"session:{session_id}"
        return await self.set(key, data, expiry=3600)  # 1 hour
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data"""
        key = f"session:{session_id}"
        return await self.get(key)
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session"""
        key = f"session:{session_id}"
        return await self.delete(key)

# Global cache instances
cache = AdvancedCacheManager()
ai_cache = AIModelCache()
session_cache = SessionCache()

# Queue management for background tasks
class RedisQueue:
    """Redis-based queue for background tasks"""
    
    def __init__(self, name: str):
        self.name = name
        self.queue_key = f"queue:{name}"
        self.processing_key = f"queue:{name}:processing"
        self.failed_key = f"queue:{name}:failed"
    
    async def enqueue(self, data: Dict, priority: int = 0) -> bool:
        """Add task to queue"""
        try:
            client = await get_redis()
            task = {
                "id": str(datetime.utcnow().timestamp()),
                "data": data,
                "created_at": datetime.utcnow().isoformat(),
                "priority": priority
            }
            
            # Use sorted set for priority queue
            await client.zadd(self.queue_key, {json.dumps(task): priority})
            return True
        except Exception as e:
            logger.error(f"Queue enqueue error: {str(e)}")
            return False
    
    async def dequeue(self, timeout: int = 0) -> Optional[Dict]:
        """Get task from queue"""
        try:
            client = await get_redis()
            
            # Get highest priority task
            result = await client.bzpopmax(self.queue_key, timeout=timeout)
            if result:
                _, task_json, _ = result
                task = json.loads(task_json)
                
                # Move to processing
                await client.hset(self.processing_key, task["id"], task_json)
                return task
            
            return None
        except Exception as e:
            logger.error(f"Queue dequeue error: {str(e)}")
            return None
    
    async def complete_task(self, task_id: str) -> bool:
        """Mark task as completed"""
        try:
            client = await get_redis()
            await client.hdel(self.processing_key, task_id)
            return True
        except Exception as e:
            logger.error(f"Queue complete error: {str(e)}")
            return False
    
    async def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed"""
        try:
            client = await get_redis()
            
            # Move from processing to failed
            task_data = await client.hget(self.processing_key, task_id)
            if task_data:
                failed_task = json.loads(task_data)
                failed_task["failed_at"] = datetime.utcnow().isoformat()
                failed_task["error"] = error
                
                await client.hset(self.failed_key, task_id, json.dumps(failed_task))
                await client.hdel(self.processing_key, task_id)
            
            return True
        except Exception as e:
            logger.error(f"Queue fail error: {str(e)}")
            return False
    
    async def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        try:
            client = await get_redis()
            
            pending = await client.zcard(self.queue_key)
            processing = await client.hlen(self.processing_key)
            failed = await client.hlen(self.failed_key)
            
            return {
                "pending": pending,
                "processing": processing,
                "failed": failed
            }
        except Exception as e:
            logger.error(f"Queue stats error: {str(e)}")
            return {"pending": 0, "processing": 0, "failed": 0}

# Pre-defined queues for different task types
analytics_queue = RedisQueue("analytics")
ml_training_queue = RedisQueue("ml_training")
notifications_queue = RedisQueue("notifications")

# Rate limiting
class RedisRateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed"""
        try:
            client = await get_redis()
            key = f"rate_limit:{identifier}"
            
            now = datetime.utcnow().timestamp()
            pipeline = client.pipeline()
            
            # Remove old entries
            pipeline.zremrangebyscore(key, 0, now - self.window_seconds)
            
            # Count current requests
            pipeline.zcard(key)
            
            # Add current request
            pipeline.zadd(key, {str(now): now})
            
            # Set expiry
            pipeline.expire(key, self.window_seconds)
            
            results = await pipeline.execute()
            current_count = results[1]
            
            allowed = current_count < self.max_requests
            
            return allowed, {
                "allowed": allowed,
                "current_count": current_count,
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "reset_time": now + self.window_seconds
            }
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            return True, {}  # Allow on error

# Global rate limiters
api_rate_limiter = RedisRateLimiter(max_requests=100, window_seconds=60)  # 100 req/min
ai_rate_limiter = RedisRateLimiter(max_requests=10, window_seconds=60)   # 10 AI req/min