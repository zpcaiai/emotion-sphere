"""
Database Connection Pool & Async Support Module
优化数据库连接管理
"""

import os
import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, AsyncGenerator, Generator

# ── 连接池配置 ────────────────────────────────────────────────

class DatabaseConfig:
    """数据库连接池配置"""
    
    # 连接池大小
    MIN_CONNECTIONS = 5
    MAX_CONNECTIONS = 20
    
    # 连接超时（秒）
    CONNECT_TIMEOUT = 10
    
    # 查询超时（秒）
    QUERY_TIMEOUT = 30
    
    # 连接回收（秒）
    IDLE_TIMEOUT = 300
    
    # 最大重试次数
    MAX_RETRIES = 3

# ── 同步连接池（psycopg2）─────────────────────────────────────

class SyncConnectionPool:
    """同步数据库连接池 - 基于 psycopg2.threadedpool"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool = None
        self._init_pool()
    
    def _init_pool(self):
        """初始化连接池"""
        import psycopg2
        from psycopg2 import pool
        
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=DatabaseConfig.MIN_CONNECTIONS,
            maxconn=DatabaseConfig.MAX_CONNECTIONS,
            dsn=self.database_url
        )
        print(f'[db] Sync connection pool initialized: {DatabaseConfig.MIN_CONNECTIONS}-{DatabaseConfig.MAX_CONNECTIONS}')
    
    @contextmanager
    def get_connection(self) -> Generator:
        """获取连接上下文管理器"""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self) -> Generator:
        """获取游标上下文管理器"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
    
    def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.closeall()

# ── 异步连接池（asyncpg）──────────────────────────────────────

class AsyncConnectionPool:
    """异步数据库连接池 - 基于 asyncpg"""
    
    def __init__(self):
        self._pool = None
        self.database_url = os.getenv('DATABASE_URL', '')
    
    async def initialize(self):
        """初始化异步连接池"""
        if not self.database_url:
            raise RuntimeError('DATABASE_URL not configured')
        
        try:
            import asyncpg
            
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=DatabaseConfig.MIN_CONNECTIONS,
                max_size=DatabaseConfig.MAX_CONNECTIONS,
                command_timeout=DatabaseConfig.QUERY_TIMEOUT,
                server_settings={
                    'jit': 'off'
                }
            )
            print(f'[db] Async connection pool initialized: {DatabaseConfig.MIN_CONNECTIONS}-{DatabaseConfig.MAX_CONNECTIONS}')
        except ImportError:
            print('[db] asyncpg not installed, async pool unavailable')
            raise
    
    async def close(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.close()
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator:
        """获取异步连接上下文管理器"""
        if not self._pool:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator:
        """获取事务上下文管理器"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn

# ── 全局实例 ──────────────────────────────────────────────────

# 同步连接池（主数据库）
sync_pool: Optional[SyncConnectionPool] = None

# 异步连接池
async_pool: Optional[AsyncConnectionPool] = None

def init_pools(database_url: str = None):
    """初始化连接池"""
    global sync_pool, async_pool
    
    url = database_url or os.getenv('DATABASE_URL', '')
    if not url:
        print('[db] DATABASE_URL not set, connection pools not initialized')
        return
    
    # 初始化同步池
    try:
        sync_pool = SyncConnectionPool(url)
    except Exception as e:
        print(f'[db] Failed to initialize sync pool: {e}')
    
    # 初始化异步池
    try:
        async_pool = AsyncConnectionPool()
    except Exception as e:
        print(f'[db] Async pool initialization deferred: {e}')

# ── 便捷函数 ────────────────────────────────────────────────

@contextmanager
def get_db_connection() -> Generator:
    """获取数据库连接的便捷函数"""
    if not sync_pool:
        init_pools()
    
    if not sync_pool:
        raise RuntimeError('Database pool not initialized')
    
    with sync_pool.get_connection() as conn:
        yield conn

@contextmanager
def get_db_cursor() -> Generator:
    """获取数据库游标的便捷函数"""
    if not sync_pool:
        init_pools()
    
    if not sync_pool:
        raise RuntimeError('Database pool not initialized')
    
    with sync_pool.get_cursor() as cursor:
        yield cursor

@asynccontextmanager
async def get_async_db() -> AsyncGenerator:
    """获取异步数据库连接的便捷函数"""
    global async_pool
    
    if not async_pool:
        async_pool = AsyncConnectionPool()
        await async_pool.initialize()
    
    async with async_pool.get_connection() as conn:
        yield conn

# ── 连接池监控 ───────────────────────────────────────────────

def get_pool_status() -> dict:
    """获取连接池状态"""
    status = {
        'sync': {'initialized': sync_pool is not None},
        'async': {'initialized': async_pool is not None}
    }
    
    if sync_pool and sync_pool._pool:
        # psycopg2 pool 没有直接的统计方法
        status['sync']['status'] = 'active'
    
    return status

# ── 数据库健康检查 ───────────────────────────────────────────

def health_check() -> dict:
    """数据库健康检查"""
    result = {
        'healthy': False,
        'response_time_ms': 0,
        'active_connections': 0,
        'error': None
    }
    
    try:
        import time
        start = time.time()
        
        with get_db_cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        
        result['response_time_ms'] = (time.time() - start) * 1000
        result['healthy'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

async def async_health_check() -> dict:
    """异步数据库健康检查"""
    result = {
        'healthy': False,
        'response_time_ms': 0,
        'error': None
    }
    
    try:
        import time
        start = time.time()
        
        async with get_async_db() as conn:
            await conn.fetch('SELECT 1')
        
        result['response_time_ms'] = (time.time() - start) * 1000
        result['healthy'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

if __name__ == '__main__':
    # 测试连接池
    test_url = os.getenv('DATABASE_URL', 'postgresql://localhost/test')
    
    # 同步测试
    init_pools(test_url)
    
    if sync_pool:
        with get_db_cursor() as cur:
            cur.execute('SELECT version()')
            version = cur.fetchone()
            print(f'PostgreSQL version: {version[0]}')
        
        print(f'Pool status: {get_pool_status()}')
        print(f'Health check: {health_check()}')
        
        sync_pool.close()
        print('Connection pool test passed')
