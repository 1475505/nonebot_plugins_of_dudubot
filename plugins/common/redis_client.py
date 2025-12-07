import os
import redis
from typing import Optional, Any


class RedisClient:
    """封装 Redis 客户端的类。

    使用示例:
        client = RedisClient()
        client.set('k', 'v', ex=60)
        client.get('k')
    """

    def __init__(self, url: Optional[str] = None, decode_responses: bool = True, **kwargs):
        self._url = url or os.environ.get("REDIS_URL")
        self._client: Optional[redis.Redis] = None
        if not self._url:
            print("Redis URL not provided; redis client unavailable")
            return
        try:
            self._client = redis.from_url(self._url, decode_responses=decode_responses, **kwargs)
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self._client = None

    @property
    def client(self) -> Optional[redis.Redis]:
        return self._client

    def is_available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            return self._client.get(key)
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.set(key, value, ex=ex))
        except Exception as e:
            print(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> int:
        if not self._client:
            return 0
        try:
            return self._client.delete(key)
        except Exception as e:
            print(f"Redis delete error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False


# 创建模块级默认实例，保持向后兼容的使用方式
redis_client = RedisClient()


def get_redis_client() -> Optional[redis.Redis]:
    """返回底层 redis.Redis 对象，可能为 None。"""
    return redis_client.client


def redis_get(key: str) -> Optional[str]:
    """兼容旧的模块级函数：从 Redis 获取键的值。"""
    return redis_client.get(key)


def redis_set(key: str, value: str, ex: Optional[int] = None) -> bool:
    """兼容旧的模块级函数：设置 Redis 键的值。"""
    return redis_client.set(key, value, ex=ex)


if __name__ == "__main__":
    success = redis_set("test_key", "test_value", ex=60)
    if success:
        print("Set successful")
    else:
        print("Set failed")

    value = redis_get("test_key")
    if value:
        print(f"Got value: {value}")
    else:
        print("Get failed or key not found")