import os
import time
import redis
from typing import List

class Limiter:
    def __init__(self):
        self.redis_url = os.environ.get("REDIS_URL")
        self.client = None
        if self.redis_url:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
            except Exception as e:
                print(f"Redis connection failed: {e}")

    def check(self, cmd: str, user_id: str, window_mins: float, max_count: int, default: bool = False) -> bool:
        if not self.client:
            return default
        
        key = f"{cmd}_{user_id}"
        now = time.time()
        cutoff = now - (window_mins * 60)
        
        try:
            # Get all timestamps
            timestamps = self.client.lrange(key, 0, -1)
            valid_timestamps = []
            
            # Filter old timestamps
            for t in timestamps:
                try:
                    if float(t) > cutoff:
                        valid_timestamps.append(float(t))
                except ValueError:
                    continue
            
            # Check if limit reached
            if len(valid_timestamps) >= max_count:
                return False
            
            # Add new timestamp
            valid_timestamps.append(now)
            self._update(key, valid_timestamps)
            return True
            
        except Exception as e:
            print(f"Limiter error: {e}")
            return default

    def checkWithSpecialUsers(self, cmd: str, user_id: str, window_mins: float, max_count: int, special_users: dict) -> bool:
        uid = str(user_id)
        limit = max_count
        
        if uid in special_users:
            limit = special_users[uid]
        else:
            try:
                uid_int = int(uid)
                if uid_int in special_users:
                    limit = special_users[uid_int]
            except (ValueError, TypeError):
                pass
        
        if limit == -1:
            return True

        return self.check(cmd, uid, window_mins, limit)

    def _update(self, key: str, timestamps: List[float]):
        pipe = self.client.pipeline()
        pipe.delete(key)
        if timestamps:
            pipe.rpush(key, *timestamps)
            pipe.expire(key, int(30 * 24 * 3600)) # 30 days expiry
        pipe.execute()

limiter = Limiter()
