"""
Caching Layer Module
包含Redis缓存、内存缓存、缓存策略等
"""

import json
import time
import hashlib
from functools import wraps
from typing import Optional, Any, Callable
from datetime import datetime, timedelta

# ── 内存缓存（Fallback）────────────────────────────────────────

class MemoryCache:
    """内存缓存实现（作为Redis的fallback）"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            # 检查是否过期
            expiry = self._timestamps.get(key, 0)
            if expiry > time.time():
                return self._cache[key]
            else:
                # 过期删除
                self.delete(key)
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        self._cache[key] = value
        self._timestamps[key] = time.time() + ttl
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        return True
    
    def clear(self) -> bool:
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()
        return True
    
    def keys(self, pattern: str = '*') -> list:
        """获取匹配模式的keys"""
        import fnmatch
        return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

# ── Redis缓存 ─────────────────────────────────────────────────

class RedisCache:
    """Redis缓存实现"""
    
    def __init__(self, redis_url: str = None):
        self._redis = None
        self._memory_fallback = MemoryCache()
        
        if redis_url:
            try:
                import redis as redis_lib
                self._redis = redis_lib.from_url(redis_url, decode_responses=True)
                self._redis.ping()  # 测试连接
                print('[cache] Redis cache initialized')
            except Exception as e:
                print(f'[cache] Redis connection failed: {e}, using memory fallback')
                self._redis = None
    
    def _make_key(self, key: str) -> str:
        """标准化key"""
        return f"emotion_sphere:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        key = self._make_key(key)
        
        if self._redis:
            try:
                value = self._redis.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                print(f'[cache] Redis get error: {e}')
        
        # Fallback to memory
        return self._memory_fallback.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        key = self._make_key(key)
        
        if self._redis:
            try:
                serialized = json.dumps(value, default=str)
                self._redis.setex(key, ttl, serialized)
                return True
            except Exception as e:
                print(f'[cache] Redis set error: {e}')
        
        # Fallback to memory
        return self._memory_fallback.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        key = self._make_key(key)
        
        if self._redis:
            try:
                self._redis.delete(key)
                return True
            except Exception as e:
                print(f'[cache] Redis delete error: {e}')
        
        return self._memory_fallback.delete(key)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        count = 0
        
        if self._redis:
            try:
                keys = self._redis.keys(self._make_key(pattern))
                if keys:
                    count = self._redis.delete(*keys)
            except Exception as e:
                print(f'[cache] Redis pattern delete error: {e}')
        
        # Memory fallback
        memory_keys = self._memory_fallback.keys(pattern)
        for key in memory_keys:
            self._memory_fallback.delete(key)
            count += 1
        
        return count

# ── 全局缓存实例 ─────────────────────────────────────────────

import os
cache = RedisCache(os.getenv('REDIS_URL'))

# ── 缓存装饰器 ───────────────────────────────────────────────

def cached(ttl: int = 3600, key_prefix: str = '', key_func: Callable = None):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存key前缀
        key_func: 自定义key生成函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 基于函数名和参数生成key
                key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                cache_key = f"{key_prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
            
            # 尝试获取缓存
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(cache_key, result, ttl)
            
            return result
        
        # 附加清除缓存的方法
        wrapper.invalidate_cache = lambda: cache.invalidate_pattern(f"{key_prefix}*")
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str) -> int:
    """按模式清除缓存"""
    return cache.invalidate_pattern(pattern)

# ── 缓存策略 ─────────────────────────────────────────────────

class CacheStrategies:
    """常用缓存策略"""
    
    # 心理学分析结果 - 短期缓存
    PSYCHOLOGY_ANALYSIS_TTL = 300  # 5分钟
    
    # 用户仪表盘 - 中期缓存
    DASHBOARD_TTL = 600  # 10分钟
    
    # 身份迁移进度 - 长期缓存
    MIGRATION_PROGRESS_TTL = 3600  # 1小时
    
    # 情绪历史 - 长期缓存
    EMOTION_HISTORY_TTL = 1800  # 30分钟
    
    # 执行力动量 - 短期缓存
    EXECUTION_MOMENTUM_TTL = 60  # 1分钟
    
    # 习惯代币 - 即时缓存
    HABIT_TOKENS_TTL = 30  # 30秒

# ── 缓存工具函数 ─────────────────────────────────────────────

def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    try:
        if cache._redis:
            info = cache._redis.info()
            return {
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)),
                'memory_used': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0)
            }
    except Exception as e:
        print(f'[cache] Stats error: {e}')
    
    # 内存缓存统计
    return {
        'type': 'memory',
        'keys_count': len(cache._memory_fallback._cache),
        'hit_rate': 'N/A'
    }

if __name__ == '__main__':
    # 测试缓存
    @cached(ttl=10, key_prefix='test')
    def expensive_function(x):
        time.sleep(1)
        return x * 2
    
    start = time.time()
    result1 = expensive_function(5)
    time1 = time.time() - start
    
    start = time.time()
    result2 = expensive_function(5)  # 应从缓存获取
    time2 = time.time() - start
    
    print(f'First call: {result1} in {time1:.2f}s')
    print(f'Cached call: {result2} in {time2:.2f}s')
    print(f'Cache speedup: {time1/time2:.1f}x')
    assert result1 == result2 == 10
    print('Cache test passed')
