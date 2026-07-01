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

    def check(
        self,
        cmd: str,
        user_id: str,
        window_mins: float,
        max_count: int,
        default: bool = False,
    ) -> bool:
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
            expired_count = len(timestamps) - len(valid_timestamps)
            self._update(key, expired_count, now, set_expire=(len(timestamps) == 0))
            return True

        except Exception as e:
            print(f"Limiter error: {e}")
            return default

    def checkWithSpecialUsers(
        self,
        cmd: str,
        user_id: str,
        window_mins: float,
        max_count: int,
        special_users: dict,
    ) -> bool:
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

    def _update(
        self,
        key: str,
        expired_count: int,
        new_timestamp: float,
        set_expire: bool = False,
    ):
        pipe = self.client.pipeline(transaction=False)
        if expired_count > 0:
            pipe.ltrim(key, expired_count, -1)
        pipe.rpush(key, new_timestamp)
        if set_expire:
            pipe.expire(key, int(30 * 24 * 3600))  # 30 days expiry
        pipe.execute()

    def checkGroupLimit(
        self,
        cmd: str,
        user_id: str,
        group_id: str,
        whitelist: set,
        window_mins: float,
        max_count: int,
    ) -> bool:
        """检查群组限流，白名单用户不受限制

        Args:
            cmd: 命令名
            user_id: 用户QQ号
            group_id: 群号
            whitelist: 白名单用户集合
            window_mins: 时间窗口（分钟）
            max_count: 最大请求次数

        Returns:
            True: 允许请求
            False: 超过限制
        """
        # 白名单用户不受限制
        if str(user_id) in whitelist:
            return True

        if not self.client:
            return True

        # 按群+命令限流的key
        key = f"{cmd}_group_{group_id}"
        now = time.time()
        cutoff = now - (window_mins * 60)

        try:
            # 获取所有时间戳
            timestamps = self.client.lrange(key, 0, -1)
            valid_timestamps = []

            # 过滤过期时间戳
            for t in timestamps:
                try:
                    if float(t) > cutoff:
                        valid_timestamps.append(float(t))
                except ValueError:
                    continue

            # 检查是否达到限制
            if len(valid_timestamps) >= max_count:
                return False

            # 添加新时间戳
            expired_count = len(timestamps) - len(valid_timestamps)
            self._update(key, expired_count, now, set_expire=(len(timestamps) == 0))
            return True

        except Exception as e:
            print(f"Group limiter error: {e}")
            return True


limiter = Limiter()
