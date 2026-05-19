"""
Structured Logging & Observability Module
包含结构化日志、性能监控、健康检查
"""

import json
import time
import uuid
import logging
import functools
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# ── 请求上下文 ────────────────────────────────────────────────

request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[Optional[int]] = ContextVar('user_id', default=None)

# ── 结构化日志格式 ───────────────────────────────────────────

class StructuredLogFormatter(logging.Formatter):
    """输出JSON格式的结构化日志"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': request_id_var.get(),
            'user_id': user_id_var.get(),
        }
        
        # 添加额外字段
        if hasattr(record, 'event'):
            log_obj['event'] = record.event
        if hasattr(record, 'metadata'):
            log_obj['metadata'] = record.metadata
        if hasattr(record, 'duration_ms'):
            log_obj['duration_ms'] = record.duration_ms
        
        # 异常信息
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, ensure_ascii=False, default=str)

# ── 日志配置 ────────────────────────────────────────────────

def setup_logging(level: str = 'INFO') -> logging.Logger:
    """配置结构化日志"""
    logger = logging.getLogger('emotion_sphere')
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredLogFormatter())
    logger.addHandler(console_handler)
    
    return logger

# 全局logger
logger = setup_logging()

# ── 结构化日志工具 ────────────────────────────────────────────

def log_event(event: str, level: str = 'info', **kwargs):
    """
    记录结构化事件
    
    示例:
        log_event('emotion_analyzed', intensity=7, emotion_type='anxiety')
    """
    extra = {
        'event': event,
        'metadata': kwargs
    }
    
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f'[{event}] {json.dumps(kwargs, default=str)}', extra=extra)

# ── 性能监控装饰器 ───────────────────────────────────────────

def timed(event_name: str = None):
    """
    函数执行时间监控装饰器
    
    示例:
        @timed('analyze_emotion')
        def analyze_emotion(...):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                
                log_event(
                    event_name or func.__name__,
                    'info',
                    duration_ms=round(duration, 2),
                    status='success'
                )
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                log_event(
                    event_name or func.__name__,
                    'error',
                    duration_ms=round(duration, 2),
                    status='error',
                    error=str(e)
                )
                raise
        return wrapper
    return decorator

# ── 指标收集 ────────────────────────────────────────────────

class MetricsCollector:
    """简单指标收集器（生产环境可替换为Prometheus）"""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
    
    def increment(self, name: str, value: int = 1, labels: dict = None):
        """计数器递增"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self._counters[key] = self._counters.get(key, 0) + value
    
    def gauge(self, name: str, value: float, labels: dict = None):
        """设置gauge值"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self._gauges[key] = value
    
    def histogram(self, name: str, value: float, labels: dict = None):
        """记录histogram值"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
    
    def get_metrics(self) -> dict:
        """获取所有指标"""
        return {
            'counters': self._counters,
            'gauges': self._gauges,
            'histograms': {k: {
                'count': len(v),
                'avg': sum(v) / len(v) if v else 0,
                'min': min(v) if v else 0,
                'max': max(v) if v else 0
            } for k, v in self._histograms.items()}
        }

# 全局指标收集器
metrics = MetricsCollector()

# ── 健康检查 ────────────────────────────────────────────────

class HealthCheck:
    """健康检查系统"""
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
    
    def register(self, name: str, check_func: callable):
        """注册健康检查"""
        self.checks[name] = check_func
    
    def run_all(self) -> dict:
        """运行所有健康检查"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'checks': {}
        }
        
        all_healthy = True
        for name, check_func in self.checks.items():
            try:
                check_result = check_func()
                results['checks'][name] = {
                    'status': 'healthy' if check_result.get('healthy', True) else 'unhealthy',
                    **check_result
                }
                if not check_result.get('healthy', True):
                    all_healthy = False
            except Exception as e:
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e)
                }
                all_healthy = False
        
        results['status'] = 'healthy' if all_healthy else 'unhealthy'
        return results

# 全局健康检查实例
health = HealthCheck()

# ── 预设健康检查 ─────────────────────────────────────────────

def setup_default_health_checks():
    """设置默认健康检查"""
    from .db_pool import health_check as db_health_check
    
    health.register('database', db_health_check)
    
    def memory_check():
        import psutil
        mem = psutil.virtual_memory()
        return {
            'healthy': mem.percent < 90,
            'usage_percent': mem.percent,
            'available_mb': mem.available / 1024 / 1024
        }
    
    try:
        health.register('memory', memory_check)
    except ImportError:
        pass
    
    def disk_check():
        import psutil
        disk = psutil.disk_usage('/')
        return {
            'healthy': disk.percent < 90,
            'usage_percent': disk.percent,
            'free_gb': disk.free / 1024 / 1024 / 1024
        }
    
    try:
        health.register('disk', disk_check)
    except ImportError:
        pass

# ── 请求追踪 ────────────────────────────────────────────────

class RequestTracer:
    """请求追踪上下文管理"""
    
    def __init__(self, user_id: Optional[int] = None):
        self.request_id = str(uuid.uuid4())
        self.user_id = user_id
        self._tokens = []
    
    def __enter__(self):
        self._tokens.append(request_id_var.set(self.request_id))
        self._tokens.append(user_id_var.set(self.user_id))
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        
        if exc_type:
            log_event('request_failed', 'error', 
                     request_id=self.request_id,
                     duration_ms=round(duration, 2),
                     error=str(exc_val))
        else:
            log_event('request_completed', 'info',
                     request_id=self.request_id,
                     duration_ms=round(duration, 2))
        
        for token in self._tokens:
            try:
                if hasattr(token, 'var'):
                    token.var.reset(token)
            except:
                pass
        
        return False
    
    @property
    def current_request_id(self) -> str:
        return self.request_id

# ── 便捷函数 ────────────────────────────────────────────────

def get_request_id() -> str:
    """获取当前请求ID"""
    return request_id_var.get()

def set_request_id(request_id: str):
    """设置当前请求ID"""
    request_id_var.set(request_id)

def get_user_id() -> Optional[int]:
    """获取当前用户ID"""
    return user_id_var.get()

def set_user_id(user_id: int):
    """设置当前用户ID"""
    user_id_var.set(user_id)

if __name__ == '__main__':
    # 测试日志
    log_event('test_event', message='Testing structured logging', value=42)
    
    # 测试指标
    metrics.increment('test_counter')
    metrics.histogram('response_time', 150.5)
    print(f'Metrics: {metrics.get_metrics()}')
    
    # 测试请求追踪
    with RequestTracer(user_id=123):
        log_event('in_request', message='Inside request context')
        print(f'Request ID: {get_request_id()}')
    
    print('Logging module test passed')
