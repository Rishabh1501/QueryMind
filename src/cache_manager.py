"""
Redis-based cache manager for semantic caching of LLM responses.
Reduces API costs by caching similar queries.
"""
import redis
import json
import hashlib
from datetime import timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class QueryCache:
    """Manages semantic caching for LLM query/response pairs using Redis."""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, ttl_hours: int = 24):
        """
        Initialize Redis-based query cache.
        
        Args:
            redis_host: Redis server hostname
            redis_port: Redis server port
            ttl_hours: Time-to-live for cache entries in hours
        """
        self.ttl = timedelta(hours=ttl_hours)
        self.ttl_seconds = int(self.ttl.total_seconds())
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(
                f"Cannot connect to Redis at {redis_host}:{redis_port}. "
                "Ensure Redis is running (try: docker-compose up -d)"
            )
    
    def _generate_key(self, query: str, schema_hash: str) -> str:
        """
        Generate cache key from query and schema.
        
        Args:
            query: User query (normalized)
            schema_hash: Hash of dataset schema
            
        Returns:
            Cache key
        """
        # Normalize query (lowercase, strip whitespace)
        normalized = query.lower().strip()
        
        # Combine with schema hash
        combined = f"{normalized}:{schema_hash}"
        
        # Generate hash with prefix
        key_hash = hashlib.md5(combined.encode()).hexdigest()
        return f"query_cache:{key_hash}"
    
    def get(self, query: str, schema_hash: str) -> Optional[str]:
        """
        Retrieve cached response if exists and not expired.
        
        Args:
            query: User query
            schema_hash: Hash of dataset schema
            
        Returns:
            Cached response or None
        """
        try:
            key = self._generate_key(query, schema_hash)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"Cache HIT for query: {query[:50]}...")
                return data.get('response')
            
            logger.info(f"Cache MISS for query: {query[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, query: str, schema_hash: str, response: str):
        """
        Store query/response in cache with TTL.
        
        Args:
            query: User query
            schema_hash: Hash of dataset schema
            response: LLM response to cache
        """
        try:
            key = self._generate_key(query, schema_hash)
            
            data = {
                'query': query,
                'schema_hash': schema_hash,
                'response': response
            }
            
            # Store with TTL
            self.redis_client.setex(
                key,
                self.ttl_seconds,
                json.dumps(data)
            )
            
            logger.info(f"Cached response for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def clear(self):
        """Clear all cache entries."""
        try:
            pattern = "query_cache:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
            else:
                logger.info("Cache already empty")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            pattern = "query_cache:*"
            keys = self.redis_client.keys(pattern)
            
            return {
                'total_entries': len(keys),
                'redis_info': self.redis_client.info('stats')
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {'total_entries': 0, 'error': str(e)}

def generate_schema_hash(schema_info: Dict[str, Any]) -> str:
    """
    Generate hash of dataset schema for cache key.
    
    Args:
        schema_info: Schema information dict
        
    Returns:
        Schema hash
    """
    # Use columns and dtypes for hash
    columns = str(schema_info.get('columns', []))
    dtypes = str(schema_info.get('dtypes', []))
    combined = f"{columns}:{dtypes}"
    
    return hashlib.md5(combined.encode()).hexdigest()[:8]

def ensure_redis_running():
    """
    Ensure Redis container is running via docker-compose.
    """
    import subprocess
    import time
    
    logger.info("Checking Redis availability...")
    
    try:
        # Try to connect first
        test_client = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
        test_client.ping()
        logger.info("Redis is already running")
        return True
    except:
        logger.info("Redis not running, starting via docker-compose...")
        
        try:
            # Start Redis container
            subprocess.run(
                ["docker-compose", "up", "-d", "redis"],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Wait for Redis to be ready
            for i in range(10):
                try:
                    time.sleep(1)
                    test_client = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
                    test_client.ping()
                    logger.info("Redis started successfully")
                    return True
                except:
                    if i < 9:
                        continue
                    else:
                        raise
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start Redis: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error starting Redis: {e}")
            return False
