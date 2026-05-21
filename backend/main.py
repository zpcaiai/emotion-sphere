"""
backend/main.py — 情感星球 FastAPI 后端
包含认证（/api/auth/*）及核心查询接口

API版本: v1.0.0
"""

import asyncio
import json
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List, Union

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator

# ── API限流 ───────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    limiter = None
    print('[warning] slowapi not installed, rate limiting disabled')

# ── 路径配置 ──────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

FRONTEND_DIST = ROOT_DIR / 'dist'
LAYOUT_FILE   = ROOT_DIR / 'emotion_sphere_layout.json'
MATCHES_FILE  = ROOT_DIR / 'emotion_exemplar_verse_matches.json'
STATS_FILE    = ROOT_DIR / 'visit_stats.json'
STATS_LOCK    = threading.Lock()

# ── 数据库配置 ─────────────────────────────────────────────────
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()

_db_pool = None


def _init_database():
    global _db_pool
    if not DATABASE_URL:
        print(
            '[db] DATABASE_URL is not set; database-backed auth/session features are disabled.',
            flush=True,
        )
        return False

    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import Json
    import psycopg2.extensions as ext
    ext.register_adapter(dict, Json)
    ext.register_adapter(list, Json)
    _db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
    print('[db] PostgreSQL connection pool initialized', flush=True)
    return True


def _get_db():
    if _db_pool is None:
        raise RuntimeError('DATABASE_URL is not configured; database is unavailable')
    return _db_pool.getconn()


def _release_db(conn):
    _db_pool.putconn(conn)


# ── 数据库初始化 ───────────────────────────────────────────────

def _init_db():
    """创建所有必要的数据库表（幂等操作）。"""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 用户表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id            SERIAL PRIMARY KEY,
                    email         VARCHAR(255) UNIQUE,
                    nickname      VARCHAR(100) NOT NULL DEFAULT '',
                    avatar        VARCHAR(500) DEFAULT '',
                    openid        VARCHAR(255) UNIQUE,
                    unionid       VARCHAR(255) UNIQUE,
                    login_type    VARCHAR(20) NOT NULL DEFAULT 'email',
                    password_hash VARCHAR(255) DEFAULT '',
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # 手机号字段迁移（幂等）
            cur.execute('''
                ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE
            ''')
            # daily_notes 表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS daily_notes (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    date       DATE NOT NULL,
                    title      VARCHAR(200) DEFAULT '',
                    content    TEXT DEFAULT '',
                    mood       VARCHAR(50) DEFAULT '',
                    tags       JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, date)
                )
            ''')

            # 安全审计日志表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS security_audit (
                    id          SERIAL PRIMARY KEY,
                    event_type  VARCHAR(50) NOT NULL,
                    email       VARCHAR(255),
                    ip_address  INET,
                    user_agent  TEXT DEFAULT '',
                    details     JSONB DEFAULT '{}',
                    success     BOOLEAN DEFAULT TRUE,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute(
                'CREATE INDEX IF NOT EXISTS idx_security_audit_email '
                'ON security_audit(email) WHERE email IS NOT NULL'
            )
            cur.execute(
                'CREATE INDEX IF NOT EXISTS idx_security_audit_created '
                'ON security_audit(created_at DESC)'
            )

            # Session token 表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_tokens (
                    token       VARCHAR(255) PRIMARY KEY,
                    email       VARCHAR(255) NOT NULL,
                    data        JSONB NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at  TIMESTAMP,
                    ip_address  INET
                )
            ''')
            cur.execute(
                'CREATE INDEX IF NOT EXISTS idx_user_tokens_email ON user_tokens(email)'
            )
            cur.execute(
                'CREATE INDEX IF NOT EXISTS idx_user_tokens_expires ON user_tokens(expires_at)'
            )

            # 代祷墙
            cur.execute('''
                CREATE TABLE IF NOT EXISTS prayers (
                    id           SERIAL PRIMARY KEY,
                    user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    nickname     VARCHAR(100) DEFAULT '',
                    content      TEXT NOT NULL,
                    is_anonymous BOOLEAN DEFAULT FALSE,
                    amen_count   INTEGER DEFAULT 0,
                    is_deleted   BOOLEAN DEFAULT FALSE,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_prayers_user ON prayers(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_prayers_created ON prayers(created_at DESC)')

            # 代祷点赞（防重复amen）
            cur.execute('''
                CREATE TABLE IF NOT EXISTS prayer_amens (
                    prayer_id  INTEGER REFERENCES prayers(id) ON DELETE CASCADE,
                    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (prayer_id, user_id)
                )
            ''')

            # 传福音祷告墙
            cur.execute('''
                CREATE TABLE IF NOT EXISTS evangelism_prayers (
                    id           SERIAL PRIMARY KEY,
                    user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    nickname     VARCHAR(100) DEFAULT '',
                    content      TEXT NOT NULL,
                    is_anonymous BOOLEAN DEFAULT FALSE,
                    amen_count   INTEGER DEFAULT 0,
                    is_deleted   BOOLEAN DEFAULT FALSE,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_evangelism_user ON evangelism_prayers(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_evangelism_created ON evangelism_prayers(created_at DESC)')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS evangelism_amens (
                    prayer_id  INTEGER REFERENCES evangelism_prayers(id) ON DELETE CASCADE,
                    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (prayer_id, user_id)
                )
            ''')

            # 灵修日记
            cur.execute('''
                CREATE TABLE IF NOT EXISTS devotion_journals (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    date       DATE NOT NULL,
                    title      VARCHAR(200) DEFAULT '',
                    content    TEXT DEFAULT '',
                    verse      VARCHAR(200) DEFAULT '',
                    reflection TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, date)
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_devotion_user ON devotion_journals(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_devotion_date ON devotion_journals(user_id, date DESC)')

            # 主日讲道笔记
            cur.execute('''
                CREATE TABLE IF NOT EXISTS sermon_journals (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    date       DATE NOT NULL,
                    title      VARCHAR(200) DEFAULT '',
                    preacher   VARCHAR(100) DEFAULT '',
                    verse      VARCHAR(200) DEFAULT '',
                    content    TEXT DEFAULT '',
                    reflection TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, date)
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_sermon_user ON sermon_journals(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_sermon_date ON sermon_journals(user_id, date DESC)')

            # 个人日记（私密）
            cur.execute('''
                CREATE TABLE IF NOT EXISTS personal_notes (
                    id         SERIAL PRIMARY KEY,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    date       DATE NOT NULL,
                    title      VARCHAR(200) DEFAULT '',
                    content    TEXT DEFAULT '',
                    mood       VARCHAR(50) DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, date)
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_personal_user ON personal_notes(user_id)')

            # 签到 / 分享墙
            cur.execute('''
                CREATE TABLE IF NOT EXISTS checkins (
                    id            SERIAL PRIMARY KEY,
                    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    nickname      VARCHAR(100) DEFAULT '',
                    emotion_label VARCHAR(100) DEFAULT '',
                    emotion_key   VARCHAR(200) DEFAULT '',
                    note          TEXT DEFAULT '',
                    is_anonymous  BOOLEAN DEFAULT FALSE,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_checkins_user ON checkins(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_checkins_created ON checkins(created_at DESC)')

            # DSS 决策支持系统表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS dss_decision_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    category VARCHAR(50) NOT NULL,
                    urgency INTEGER CHECK (urgency BETWEEN 1 AND 5) DEFAULT 3,
                    importance INTEGER CHECK (importance BETWEEN 1 AND 5) DEFAULT 3,
                    stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10) DEFAULT 5,
                    anxiety_level INTEGER CHECK (anxiety_level BETWEEN 0 AND 10) DEFAULT 5,
                    fatigue_level INTEGER CHECK (fatigue_level BETWEEN 0 AND 10) DEFAULT 5,
                    spiritual_dryness INTEGER CHECK (spiritual_dryness BETWEEN 0 AND 10) DEFAULT 5,
                    emotional_stability INTEGER CHECK (emotional_stability BETWEEN 0 AND 10) DEFAULT 5,
                    physical_health INTEGER CHECK (physical_health BETWEEN 0 AND 10) DEFAULT 5,
                    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10) DEFAULT 5,
                    social_connection INTEGER CHECK (social_connection BETWEEN 0 AND 10) DEFAULT 5,
                    financial_pressure INTEGER CHECK (financial_pressure BETWEEN 0 AND 10) DEFAULT 5,
                    cognitive_clarity INTEGER CHECK (cognitive_clarity BETWEEN 0 AND 10) DEFAULT 5,
                    identity_confusion INTEGER CHECK (identity_confusion BETWEEN 0 AND 10) DEFAULT 5,
                    moral_tension INTEGER CHECK (moral_tension BETWEEN 0 AND 10) DEFAULT 5,
                    motive_analysis JSONB,
                    discernment_result JSONB,
                    guidance JSONB,
                    emotion_logs JSONB DEFAULT '[]',
                    context_factors JSONB,
                    status VARCHAR(20) DEFAULT 'analyzing',
                    final_decision TEXT,
                    outcome_status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analyzed_at TIMESTAMP,
                    decided_at TIMESTAMP,
                    reviewed_at TIMESTAMP
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dss_decisions_user ON dss_decision_events(user_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dss_decisions_status ON dss_decision_events(status)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dss_decisions_created ON dss_decision_events(created_at DESC)')

            # DSS 回顾日志表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS dss_review_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    decision_id UUID REFERENCES dss_decision_events(id) ON DELETE CASCADE,
                    user_id VARCHAR(255) NOT NULL,
                    outcome_description TEXT NOT NULL,
                    peace_level INTEGER CHECK (peace_level BETWEEN -5 AND 5),
                    regret_level INTEGER CHECK (regret_level BETWEEN 0 AND 10),
                    lessons_learned TEXT,
                    growth_impact TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
    finally:
        _release_db(conn)

    print('[db] Database tables initialized ok', flush=True)


# ── FastAPI 生命周期 ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    has_database = _init_database()
    if has_database:
        _init_db()

    # 注入数据库函数到 auth 模块
    from backend.auth import init_db_functions
    init_db_functions(_get_db, _release_db)

    # 注入数据库函数到 shop / wxpay 模块，并初始化商店表
    if has_database and _db_pool:
        try:
            from backend.shop import init_db_functions as shop_init_db, init_shop_tables
            from backend.wxpay import init_db_functions as wxpay_init_db
            shop_init_db(_get_db, _release_db)
            wxpay_init_db(_get_db, _release_db)
            _conn = _get_db()
            try:
                init_shop_tables(_conn)
            finally:
                _release_db(_conn)
            print('[startup] Shop tables initialized', flush=True)
        except Exception as exc:
            print(f'[startup] Shop init skipped: {exc}', flush=True)

    # 初始化 DSS 决策支持系统
    if has_database and _db_pool:
        try:
            init_dss_storage(_db_pool)
            print('[startup] DSS storage initialized', flush=True)
        except Exception as exc:
            print(f'[startup] DSS init skipped: {exc}', flush=True)

    # 预热查询缓存（如果有）
    try:
        from query_emotion_verses import prewarm_cache
        await asyncio.to_thread(prewarm_cache)
        print('[startup] cache pre-warmed', flush=True)
    except Exception as exc:
        print(f'[startup] prewarm skipped: {exc}', flush=True)

    yield


# ── 标准化API响应模型 ─────────────────────────────────────────

class ApiMetadata(BaseModel):
    """API响应元数据"""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    request_id: Optional[str] = None
    version: str = "1.0.0"
    pagination: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-01-15T10:30:00",
                "version": "1.0.0",
                "pagination": {"page": 1, "per_page": 20, "total": 100}
            }
        }

class ApiResponse(BaseModel):
    """统一API响应格式"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    meta: ApiMetadata = Field(default_factory=ApiMetadata)
    error: Optional[Dict[str, Any]] = None
    
    @validator('error', always=True)
    def validate_error_on_failure(cls, v, values):
        if not values.get('success') and not v:
            return {"code": "UNKNOWN_ERROR", "message": "An unknown error occurred"}
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": 123, "name": "example"},
                "meta": {
                    "timestamp": "2026-01-15T10:30:00",
                    "version": "1.0.0"
                }
            }
        }

class ApiErrorResponse(BaseModel):
    """API错误响应格式"""
    success: bool = False
    error: Dict[str, Any] = Field(..., description="错误详情")
    meta: ApiMetadata = Field(default_factory=ApiMetadata)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {"field": "email", "issue": "Invalid format"}
                },
                "meta": {
                    "timestamp": "2026-01-15T10:30:00",
                    "version": "1.0.0"
                }
            }
        }

# ── FastAPI 应用 ───────────────────────────────────────────────

app = FastAPI(
    title='Emotion Sphere API',
    description='心理学引擎API - 支持人格塑造、习惯养成、执行力三大子系统',
    version='1.0.0',
    docs_url='/api/v1/docs',
    redoc_url='/api/v1/redoc',
    openapi_url='/api/v1/openapi.json',
    lifespan=lifespan
)

# 注册限流错误处理器
if limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
if '*' in ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['*'],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'X-Requested-With'],
    )


# 安全响应头
@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# ── 注册认证路由 ───────────────────────────────────────────────
from backend.auth import router as auth_router
app.include_router(auth_router)

# ── 注册决策支持路由 (DSS) ────────────────────────────────────
from backend.decision_support import router as dss_router, init_dss_storage
app.include_router(dss_router)

# ── 注册虚拟商店 + 微信支付路由 ──────────────────────────────
from backend.shop import router as shop_router
from backend.wxpay import router as wxpay_router
app.include_router(shop_router)
app.include_router(wxpay_router)


# ── 健康检查 ──────────────────────────────────────────────────

@app.get('/')
def root():
    return {'ok': True, 'service': 'emotion-sphere-backend'}


@app.get('/api/health')
def health():
    return {'ok': True, 'service': 'emotion-sphere-backend'}


# ── 静态数据接口 ───────────────────────────────────────────────

def _load_json(path: Path):
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.get('/api/layout')
def get_layout():
    items = _load_json(LAYOUT_FILE)
    return {'items': items, 'count': len(items)}


@app.get('/api/feature')
def get_feature(key: str = ''):
    if not key:
        raise HTTPException(status_code=400, detail='Missing feature key')
    matches = _load_json(MATCHES_FILE)
    match_map = {f"{m.get('layer')}:{m.get('feature_id')}": m for m in matches}
    item = match_map.get(key)
    if item is None:
        raise HTTPException(status_code=404, detail='Feature not found')
    return item


@app.post('/api/story')
async def generate_story(request: Request):
    body = await request.json()
    emotion = str(body.get('emotion', '')).strip()
    if not emotion:
        raise HTTPException(status_code=400, detail='Missing emotion')
    try:
        from query_emotion_verses import call_chat
        system_prompt = (
            '你是一位充满智慧与温暖的属灵故事讲述者。'
            '请根据用户提供的情绪，写一段200-300字的励志属灵小故事，'
            '故事要有具体场景、人物内心挣扎、转折与盼望，文字优美流畅，能触动人心。'
            '只输出故事正文，不加任何标题或说明。'
        )
        story = await asyncio.to_thread(call_chat, system_prompt, f'情绪：{emotion}')
        if not story:
            return {'story': f'愿在"{emotion}"中，你找到一丝平静与力量。', 'degraded': True}
        return {'story': story}
    except Exception as exc:
        print(f'[api/story] error: {exc}', flush=True)
        return {'story': f'愿在"{emotion}"中，你找到一丝平静与力量。', 'degraded': True}


@app.post('/api/guidance')
async def get_guidance(request: Request):
    body = await request.json()
    query = str(body.get('query', '')).strip()
    if not query:
        raise HTTPException(status_code=400, detail='Missing query')
    try:
        from query_emotion_verses import assess_psychological_state
        result = await asyncio.to_thread(assess_psychological_state, query)
        return result
    except Exception as exc:
        print(f'[api/guidance] error: {exc}', flush=True)
        return {
            'core_emotions': [],
            'psychological_assessment': '灵性引导服务暂时不可用，请稍后再试。',
            'coping_suggestions': [],
            'spiritual_guidance': '',
            'core_need': '',
            'service_unavailable': True,
        }


# ── 查询接口 ──────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    topFeatures: int = Field(default=5, ge=1, le=20)
    topVerses: int = Field(default=5, ge=1, le=20)
    languageFilter: str = Field(default='both')
    includeGuidance: bool = False
    enableRerank: bool = False
    rerankCandidates: int = Field(default=20, ge=1, le=100)
    rerankWeight: float = Field(default=0.3, ge=0.0, le=1.0)
    rerankMode: str = Field(default='llm')


@app.post('/api/query')
async def run_query(payload: QueryRequest):
    try:
        from query_emotion_verses import query_emotion_verses
        import time
        started_at = time.perf_counter()
        result = await asyncio.to_thread(
            query_emotion_verses,
            query_text=payload.query,
            top_features=payload.topFeatures,
            top_verses_per_language=payload.topVerses,
            include_guidance=payload.includeGuidance,
            enable_rerank=payload.enableRerank,
            rerank_candidates=payload.rerankCandidates,
            rerank_weight=payload.rerankWeight,
        )
        result['query_latency_ms'] = round((time.perf_counter() - started_at) * 1000, 2)
        # 保存历史（非关键，失败不影响响应）
        try:
            from web_emotion_query import save_history_entry
            save_history_entry(
                payload.query, payload.topFeatures, payload.topVerses,
                payload.languageFilter, result
            )
        except Exception:
            pass
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        err_msg = str(exc)
        print(f'[api/query] error: {err_msg}', flush=True)
        # 外部服务不可用时返回降级结果而非崩溃
        if any(kw in err_msg.lower() for kw in ('connection', 'timeout', 'ssl', '502', '503', '504', '429')):
            return {
                'query_text': payload.query,
                'selected_emotions': [],
                'verse_summary': {'cuv': [], 'esv': []},
                'rerank': {'enabled': False, 'applied': False},
                'degraded': True,
                'error': '向量检索服务暂时不可用，请稍后重试',
                'query_latency_ms': 0,
            }
        raise HTTPException(status_code=500, detail=err_msg)


@app.get('/api/history')
def get_history():
    try:
        from web_emotion_query import load_history
        return {'items': load_history()}
    except Exception:
        return {'items': [], 'total': 0}




# ── 访问统计 ──────────────────────────────────────────────────

def _load_stats() -> dict:
    if not STATS_FILE.exists():
        return {'page_views': 0, 'unique_visitors': 0, 'visitor_ids': []}
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'page_views': 0, 'unique_visitors': 0, 'visitor_ids': []}


def _save_stats(stats: dict):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False)


@app.get('/api/stats')
def get_stats():
    with STATS_LOCK:
        stats = _load_stats()
    return {'page_views': stats.get('page_views', 0),
            'unique_visitors': stats.get('unique_visitors', 0)}


class VisitTrackRequest(BaseModel):
    visitorId: str = Field(min_length=1, max_length=128)


@app.post('/api/stats/track')
def track_stats(payload: VisitTrackRequest):
    with STATS_LOCK:
        stats = _load_stats()
        stats['page_views'] = int(stats.get('page_views', 0)) + 1
        visitor_ids = set(stats.get('visitor_ids', []))
        visitor_ids.add(payload.visitorId.strip())
        stats['visitor_ids'] = sorted(visitor_ids)
        stats['unique_visitors'] = len(visitor_ids)
        _save_stats(stats)
    return {'page_views': stats['page_views'], 'unique_visitors': stats['unique_visitors']}


# ── 辅助：从请求中获取已登录用户 ID ──────────────────────────────

def _require_user(request: Request):
    from backend.auth import get_session_user
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    return user


def _optional_user(request: Request):
    from backend.auth import get_session_user
    return get_session_user(request)


# ── 用户资料 ──────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    nickname: str = Field(default='', max_length=64)
    avatar: str = Field(default='', max_length=500)


@app.put('/api/user/profile')
def update_user_profile(payload: UpdateProfileRequest, request: Request):
    user = _require_user(request)
    uid = user['id']
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET nickname=%s, avatar=%s, updated_at=NOW() WHERE id=%s '
                'RETURNING id, email, nickname, avatar, login_type',
                (payload.nickname.strip() or user.get('nickname', ''),
                 payload.avatar.strip() or user.get('avatar', ''), uid)
            )
            row = cur.fetchone()
            conn.commit()
        return {'ok': True, 'id': row[0], 'email': row[1],
                'nickname': row[2], 'avatar': row[3], 'login_type': row[4]}
    finally:
        _release_db(conn)


# ── 每日笔记 /api/daily/notes ────────────────────────────────
# 替代原有的 devotion/sermon/personal notes，去除圣经元素

class DailyNoteRequest(BaseModel):
    date: str = Field(..., regex=r'^\\d{4}-\\d{2}-\\d{2}$')
    title: str = Field(default='', max_length=200)
    content: str = Field(default='', max_length=5000)
    mood: str = Field(default='', max_length=50)
    tags: list = Field(default=[])


@app.get('/api/daily/notes')
def list_daily_notes(request: Request, limit: int = 50, offset: int = 0):
    """获取用户的每日笔记列表"""
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, date, title, content, mood, tags, created_at, updated_at
                   FROM daily_notes WHERE user_id=%s ORDER BY date DESC LIMIT %s OFFSET %s''',
                (user['id'], limit, offset)
            )
            rows = cur.fetchall()
        cols = ['id','date','title','content','mood','tags','created_at','updated_at']
        items = [dict(zip(cols, r)) for r in rows]
        for it in items:
            if it['created_at']: it['created_at'] = it['created_at'].isoformat()
            if it['updated_at']: it['updated_at'] = it['updated_at'].isoformat()
        return {'ok': True, 'items': items}
    finally:
        _release_db(conn)


@app.post('/api/daily/notes')
def save_daily_note(payload: DailyNoteRequest, request: Request):
    """保存每日笔记（有则更新，无则创建）"""
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO daily_notes (user_id, date, title, content, mood, tags)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (user_id, date) DO UPDATE
                   SET title=EXCLUDED.title, content=EXCLUDED.content,
                       mood=EXCLUDED.mood, tags=EXCLUDED.tags, updated_at=NOW()
                   RETURNING id''',
                (user['id'], payload.date, payload.title.strip(),
                 payload.content.strip(), payload.mood, payload.tags)
            )
            row = cur.fetchone()
            conn.commit()
        return {'ok': True, 'id': row[0]}
    finally:
        _release_db(conn)


@app.get('/api/daily/notes/{note_id}')
def get_daily_note(note_id: int, request: Request):
    """获取单条笔记详情"""
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, date, title, content, mood, tags, created_at, updated_at
                   FROM daily_notes WHERE id=%s AND user_id=%s''',
                (note_id, user['id'])
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='笔记不存在')
        cols = ['id','date','title','content','mood','tags','created_at','updated_at']
        item = dict(zip(cols, row))
        if item['created_at']: item['created_at'] = item['created_at'].isoformat()
        if item['updated_at']: item['updated_at'] = item['updated_at'].isoformat()
        return {'ok': True, 'item': item}
    finally:
        _release_db(conn)


@app.delete('/api/daily/notes/{note_id}')
def delete_daily_note(note_id: int, request: Request):
    """删除笔记"""
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM daily_notes WHERE id=%s AND user_id=%s',
                        (note_id, user['id']))
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


# ── 签到 / 分享墙 /api/user/checkin ──────────────────────────

class CheckinRequest(BaseModel):
    emotionLabel: str = Field(default='', max_length=100)
    emotionKey: str = Field(default='', max_length=200)
    note: str = Field(default='', max_length=500)
    isAnonymous: bool = False


@app.post('/api/user/checkin')
def submit_checkin(payload: CheckinRequest, request: Request):
    user = _optional_user(request)
    uid = user['id'] if user else None
    nick = user.get('nickname', '') if user else ''
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO checkins (user_id, nickname, emotion_label, emotion_key, note, is_anonymous) '
                'VALUES (%s,%s,%s,%s,%s,%s) RETURNING id, created_at',
                (uid, nick, payload.emotionLabel, payload.emotionKey,
                 payload.note, payload.isAnonymous)
            )
            row = cur.fetchone()
            conn.commit()
        return {'ok': True, 'id': row[0], 'tags_extracted': payload.emotionLabel,
                'created_at': row[1].isoformat()}
    finally:
        _release_db(conn)


@app.get('/api/user/checkins')
def list_checkins(limit: int = 40, offset: int = 0):
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT c.id, c.nickname, c.emotion_label, c.note, c.is_anonymous,
                          c.created_at, u.avatar
                   FROM checkins c LEFT JOIN users u ON u.id = c.user_id
                   ORDER BY c.created_at DESC LIMIT %s OFFSET %s''',
                (limit, offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM checkins')
            total = cur.fetchone()[0]
        items = [{'id': r[0],
                  'nickname': '匿名' if r[4] else (r[1] or '用户'),
                  'emotion_label': r[2], 'note': r[3], 'is_anonymous': r[4],
                  'created_at': r[5].isoformat() if r[5] else None,
                  'avatar': '' if r[4] else (r[6] or '')} for r in rows]
        return {'items': items, 'total': total}
    finally:
        _release_db(conn)


# ── 简单 AI 对话（流式） /api/chat ────────────────────────────

@app.post('/api/chat')
async def chat_endpoint(request: Request):
    from fastapi.responses import StreamingResponse
    body = await request.json()
    messages = body.get('messages', [])
    session_id = body.get('session_id', '')
    if not messages:
        raise HTTPException(status_code=400, detail='messages required')
    try:
        from query_emotion_verses import call_chat
        last_user = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), '')
        system_prompt = (
            '你是情感星球的属灵辅导助手，擅长用圣经原则回应用户的情感困惑与属灵问题。'
            '回应要温暖、简洁、有深度，适当引用圣经经文。'
        )
        reply = await asyncio.to_thread(call_chat, system_prompt, last_user)

        async def _stream():
            yield f'data: {json.dumps({"delta": reply, "session_id": session_id}, ensure_ascii=False)}\n\n'
            yield f'data: {json.dumps({"done": True, "session_id": session_id}, ensure_ascii=False)}\n\n'

        return StreamingResponse(_stream(), media_type='text/event-stream')
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 心理学引擎 API (L0-L4 架构) ─────────────────────────────────

class PsychologyAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    intensity: int = Field(default=5, ge=1, le=10)
    include_history: bool = Field(default=True)


class ExperimentSubmitRequest(BaseModel):
    experiment_id: str = Field(min_length=1)
    outcome: dict = Field(default_factory=dict)
    reflection: str = Field(default='', max_length=1000)


@app.post('/api/psychology/analyze')
def psychology_analyze(payload: PsychologyAnalyzeRequest, request: Request):
    """
    L0-L4 完整心理分析
    人格因果引擎 + 认知图式 + 状态机 + 身份认同 + 成长轨迹
    """
    user = _optional_user(request)
    user_id = user.get('id') if user else None
    
    # 获取历史日志（如果用户已登录且要求包含历史）
    history = None
    if user_id and payload.include_history:
        try:
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute(
                    '''SELECT raw_text, emotion_tags, intensity, occurred_at, context_json
                       FROM emotion_logs 
                       WHERE user_id = %s 
                       ORDER BY occurred_at DESC LIMIT 20''',
                    (user_id,)
                )
                rows = cur.fetchall()
                history = [{
                    'raw_text': r[0],
                    'emotion_tags': r[1] or [],
                    'intensity': r[2] or 5,
                    'occurred_at': r[3].isoformat() if r[3] else None,
                    'context_json': r[4] or {}
                } for r in rows]
            _release_db(conn)
        except Exception as e:
            print(f'[psychology] Failed to load history: {e}', flush=True)
    
    # 调用心理学引擎
    try:
        from backend.psychology_engine import analyze_emotion
        result = analyze_emotion(
            user_input=payload.text,
            user_id=user_id,
            history=history,
            intensity=payload.intensity
        )
        
        # 如果用户已登录，保存本次分析结果
        if user_id:
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    # 保存情绪日志
                    cur.execute(
                        '''INSERT INTO emotion_logs 
                           (user_id, raw_text, emotion_tags, intensity, occurred_at, context_json)
                           VALUES (%s, %s, %s, %s, NOW(), %s)
                           RETURNING id''',
                        (user_id, payload.text, 
                         result.get('layers', {}).get('L0_causal', {}).get('personality_driver', {}).get('personality_traits', []),
                         payload.intensity,
                         json.dumps({'analysis_id': result.get('analysis_id')})
                        )
                    )
                    log_id = cur.fetchone()[0]
                    
                    # 保存详细心理学分析结果到 L0-L4 结果表
                    try:
                        layers = result.get('layers', {})
                        l0 = layers.get('L0_causal', {}).get('personality_driver', {})
                        l1_schema = layers.get('L1_regulation', {}).get('cognitive_schema', {})
                        l1_exp = layers.get('L1_regulation', {}).get('behavioral_experiment', {})
                        l2 = layers.get('L2_execution', {}).get('current_state', {})
                        l3 = layers.get('L3_identity', {}).get('identity_narrative', {}) or {}
                        l4 = layers.get('L4_memory', {}).get('growth_metrics', {}) or {}
                        synthesis = result.get('synthesis', {})
                        
                        cur.execute(
                            '''INSERT INTO psychology_analysis_results 
                               (user_id, analysis_type, input_text, intensity,
                                l0_driver_category, l0_core_belief, l0_intervention_priority,
                                l1_distortion_type, l1_core_belief, l1_reframing_patch,
                                l1_experiment_title, l1_experiment_action,
                                l2_state_name, l2_state_level, l2_arousal_level,
                                l2_recommended_action,
                                l3_narrative_type, l3_coherence_score,
                                synthesis_immediate_action, synthesis_core_insight, synthesis_risk_level,
                                is_crisis)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                       %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                               RETURNING id''',
                            (user_id, 'emotion', payload.text, payload.intensity,
                             l0.get('driver_category'), l0.get('core_belief'), l0.get('intervention_priority'),
                             l1_schema.get('distortion_type'), l1_schema.get('core_belief'),
                             l1_schema.get('cognitive_reframing_patch'),
                             l1_exp.get('title'), l1_exp.get('counter_behavioral_action'),
                             l2.get('state_name'), l2.get('state_level'), l2.get('arousal_level'),
                             l2.get('recommended_action'),
                             l3.get('narrative_type'), l3.get('coherence_score'),
                             synthesis.get('immediate_action'), synthesis.get('core_insight'),
                             synthesis.get('risk_level'),
                             l2.get('state_name') == 'CRISIS')
                        )
                        analysis_id = cur.fetchone()[0]
                        result['saved_analysis_id'] = analysis_id
                    except Exception as e2:
                        print(f'[psychology] Failed to save detailed analysis: {e2}', flush=True)
                    
                    conn.commit()
                    result['saved_log_id'] = log_id

                    # Auto-extract persona tags from analysis
                    try:
                        from backend.persona_tag_engine import get_tag_engine
                        engine = get_tag_engine()
                        tags = engine.auto_extract_and_store(
                            conn, user_id, payload.text, 'emotion_log', str(log_id), result
                        )
                        result['extracted_tags'] = tags
                    except Exception as te:
                        print(f'[persona_tags] Extraction failed: {te}', flush=True)

                _release_db(conn)
            except Exception as e:
                print(f'[psychology] Failed to save log: {e}', flush=True)

        return result
        
    except Exception as exc:
        print(f'[psychology] Analysis failed: {exc}', flush=True)
        return {
            'error': '分析服务暂时不可用',
            'degraded': True,
            'fallback': {
                'immediate_action': '深呼吸，尝试4-7-8呼吸法',
                'core_insight': '当前无法生成深度分析，建议稍后重试或联系支持',
                'suggested_coping': ['grounding技巧', '与信任的人交谈']
            }
        }


@app.get('/api/psychology/dashboard')
def psychology_dashboard(request: Request):
    """
    用户心理仪表盘 - 汇总L0-L4各层数据
    """
    user = _require_user(request)
    user_id = user['id']
    
    try:
        conn = _get_db()
        with conn.cursor() as cur:
            # 使用仪表盘视图
            cur.execute(
                '''SELECT current_state, active_schemas_count, pending_experiments,
                          weekly_logs, latest_growth_scores, current_identity
                   FROM user_psychological_dashboard WHERE user_id = %s''',
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return {
                    'current_state': 'REGULATED',
                    'active_schemas': 0,
                    'pending_experiments': 0,
                    'weekly_logs': 0,
                    'growth_scores': None,
                    'current_identity': '正在探索中'
                }
            
            return {
                'current_state': row[0] or 'REGULATED',
                'active_schemas': row[1] or 0,
                'pending_experiments': row[2] or 0,
                'weekly_logs': row[3] or 0,
                'growth_scores': row[4],
                'current_identity': row[5] or '正在探索中'
            }
    except Exception as exc:
        print(f'[psychology_dashboard] Failed: {exc}', flush=True)
        return {
            'error': '仪表盘数据暂时不可用',
            'current_state': 'REGULATED',
            'active_schemas': 0,
            'pending_experiments': 0
        }
    finally:
        try:
            _release_db(conn)
        except:
            pass


@app.get('/api/psychology/experiments')
def list_experiments(status: str = 'all', limit: int = 20, request: Request = None):
    """获取用户的行为实验列表"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            if status == 'all':
                cur.execute(
                    '''SELECT id, experiment_id, title, status, scheduled_at, completed_at,
                              hypothesis_to_test, counter_behavioral_action, binary_telemetry_metric
                       FROM behavioral_experiments 
                       WHERE user_id = %s 
                       ORDER BY created_at DESC LIMIT %s''',
                    (user_id, limit)
                )
            else:
                cur.execute(
                    '''SELECT id, experiment_id, title, status, scheduled_at, completed_at,
                              hypothesis_to_test, counter_behavioral_action, binary_telemetry_metric
                       FROM behavioral_experiments 
                       WHERE user_id = %s AND status = %s
                       ORDER BY scheduled_at ASC LIMIT %s''',
                    (user_id, status, limit)
                )
            rows = cur.fetchall()
            
            items = [{
                'id': r[0],
                'experiment_id': r[1],
                'title': r[2],
                'status': r[3],
                'scheduled_at': r[4].isoformat() if r[4] else None,
                'completed_at': r[5].isoformat() if r[5] else None,
                'hypothesis': r[6],
                'action': r[7],
                'metric': r[8]
            } for r in rows]
            
            return {'items': items, 'total': len(items)}
    finally:
        _release_db(conn)


@app.post('/api/psychology/experiments/{experiment_id}/complete')
def complete_experiment(experiment_id: str, payload: ExperimentSubmitRequest, request: Request):
    """提交行为实验结果"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE behavioral_experiments 
                   SET status = 'completed', 
                       completed_at = NOW(),
                       actual_outcome = %s,
                       user_reflection = %s,
                       hypothesis_falsified = %s
                   WHERE user_id = %s AND experiment_id = %s
                   RETURNING id''',
                (json.dumps(payload.outcome), payload.reflection,
                 payload.outcome.get('hypothesis_falsified', False),
                 user_id, experiment_id)
            )
            row = cur.fetchone()
            conn.commit()
            
            if not row:
                raise HTTPException(status_code=404, detail='实验未找到')
            
            return {'ok': True, 'completed_id': row[0]}
    finally:
        _release_db(conn)


# ── 子系统三：执行力边缘引导 API ─────────────────────────────

class EdgeInterventionRequest(BaseModel):
    raw_task: str = Field(min_length=1, max_length=1000)
    edge_context: dict = Field(default_factory=dict)
    telemetry_signals: list = Field(default_factory=list)


class MicroChainRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    steps: int = Field(default=3, ge=1, le=10)


class InterventionLogRequest(BaseModel):
    paralysis_type: str = Field(default='')
    detected_signals: list = Field(default_factory=list)
    ignition_sequence: str = Field(default='')
    was_completed: bool = Field(default=False)
    completion_percentage: int = Field(default=0, ge=0, le=100)
    post_intervention_mood: int = Field(default=5, ge=1, le=10)


@app.post('/api/execution/detect-intervene')
def execution_detect_intervene(payload: EdgeInterventionRequest, request: Request):
    """
    执行力边缘干预 - 检测崩溃并生成2分钟点火序列
    
    实时微调度器：检测到系统抖动时发出中断信号
    """
    try:
        from backend.psychology_engine import detect_execution_paralysis
        result = detect_execution_paralysis(
            raw_task=payload.raw_task,
            context=payload.edge_context,
            signals=payload.telemetry_signals
        )
        
        # 如果检测到崩溃，记录到数据库
        user = _optional_user(request)
        if user and result.get('paralysis_type') != 'none':
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    cur.execute(
                        '''INSERT INTO execution_paralysis_logs 
                           (user_id, paralysis_type, detected_signals, raw_backlog_task,
                            edge_context, intervention_triggered, ignition_sequence_delivered)
                           VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                           RETURNING id''',
                        (user['id'], result.get('paralysis_type'), 
                         json.dumps(result.get('detected_signals', [])),
                         payload.raw_task,
                         json.dumps(payload.edge_context),
                         result.get('ignition_sequence'))
                    )
                    row = cur.fetchone()
                    conn.commit()
                    result['log_id'] = str(row[0])
                _release_db(conn)
            except Exception as e:
                print(f'[execution] Failed to log: {e}', flush=True)
        
        return result
        
    except Exception as exc:
        print(f'[execution_detect] Failed: {exc}', flush=True)
        return {
            'paralysis_type': 'system_error',
            'collapse_risk': 5,
            'ignition_sequence': '深呼吸3次，然后尝试任务的最小版本',
            'low_pressure_guide': '系统暂时无法分析，请温柔地对待自己',
            'error': str(exc)
        }


@app.post('/api/execution/micro-chain')
def execution_micro_chain(payload: MicroChainRequest):
    """
    生成任务微步骤链 - 降维解耦
    
    将大任务拆解为3个2分钟可完成的原子步骤
    """
    try:
        from backend.psychology_engine import generate_micro_chain
        chain = generate_micro_chain(payload.task, payload.steps)
        return {
            'task': payload.task,
            'decoupled_chain': chain,
            'total_duration_estimate': sum(s.get('duration_seconds', 120) for s in chain)
        }
    except Exception as exc:
        print(f'[execution_chain] Failed: {exc}', flush=True)
        return {
            'task': payload.task,
            'decoupled_chain': [
                {'step_id': '1', 'action': f'打开与{payload.task[:20]}相关的应用', 'duration_seconds': 60},
                {'step_id': '2', 'action': '执行第一个可见的小动作', 'duration_seconds': 120},
                {'step_id': '3', 'action': '标记完成或保存进度', 'duration_seconds': 60}
            ],
            'error': str(exc)
        }


@app.post('/api/execution/log-intervention')
def log_intervention(payload: InterventionLogRequest, request: Request):
    """
    记录干预执行结果和微动量
    """
    user = _optional_user(request)
    if not user:
        return {'ok': True, 'warning': 'Not logged in, not saved'}
    
    user_id = user['id']
    
    try:
        conn = _get_db()
        with conn.cursor() as cur:
            # 更新最近一条崩溃日志
            cur.execute(
                '''UPDATE execution_paralysis_logs 
                   SET user_responded = TRUE,
                       ignition_completed = %s,
                       completion_percentage = %s,
                       post_intervention_mood = %s,
                       completed_at = NOW()
                   WHERE user_id = %s AND user_responded = FALSE
                   ORDER BY detected_at DESC
                   LIMIT 1
                   RETURNING id''',
                (payload.was_completed, payload.completion_percentage, 
                 payload.post_intervention_mood, user_id)
            )
            row = cur.fetchone()
            conn.commit()
            
            # 计算微动量
            from backend.psychology_engine import calculate_micro_momentum
            momentum = calculate_micro_momentum(
                completed=1 if payload.was_completed else 0,
                total=3,  # 默认3步
                avg_time=120  # 默认120秒
            )
            
            return {
                'ok': True,
                'updated_log_id': str(row[0]) if row else None,
                'micro_momentum': momentum
            }
    except Exception as exc:
        print(f'[execution_log] Failed: {exc}', flush=True)
        return {'ok': False, 'error': str(exc)}
    finally:
        try:
            _release_db(conn)
        except:
            pass


@app.get('/api/execution/dashboard')
def execution_dashboard(request: Request):
    """
    执行力系统仪表盘 - 实时边缘引导状态
    """
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT today_paralysis_events, active_micro_sessions,
                          weekly_success_rate, top_paralysis_type,
                          current_momentum, active_intentions
                   FROM user_execution_dashboard 
                   WHERE user_id = %s''',
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return {
                    'today_paralysis_events': 0,
                    'active_micro_sessions': 0,
                    'weekly_success_rate': 0,
                    'top_paralysis_type': None,
                    'current_momentum': 50,
                    'active_intentions': 0
                }
            
            return {
                'today_paralysis_events': row[0] or 0,
                'active_micro_sessions': row[1] or 0,
                'weekly_success_rate': row[2] or 0,
                'top_paralysis_type': row[3],
                'current_momentum': row[4] or 50,
                'active_intentions': row[5] or 0
            }
    finally:
        _release_db(conn)


@app.get('/api/execution/active-sessions')
def active_micro_sessions(request: Request):
    """获取用户活跃的微调度器会话"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, original_task, decoupled_chain, current_step_index,
                          steps_completed, total_steps, micro_momentum_score,
                          started_at
                   FROM micro_scheduler_sessions 
                   WHERE user_id = %s AND session_status = 'active'
                   ORDER BY started_at DESC''',
                (user_id,)
            )
            rows = cur.fetchall()
            
            items = [{
                'id': str(r[0]),
                'original_task': r[1],
                'decoupled_chain': r[2],
                'current_step': r[3],
                'steps_completed': r[4],
                'total_steps': r[5],
                'momentum_score': r[6],
                'started_at': r[7].isoformat() if r[7] else None
            } for r in rows]
            
            return {'items': items, 'total': len(items)}
    finally:
        _release_db(conn)


# ── 执行力系统 - 前端兼容API端点 ─────────────────────────────

class CrashDetectRequest(BaseModel):
    task_attempts: int = Field(default=0, ge=0)
    escape_urges: int = Field(default=0, ge=0)
    last_session_minutes: int = Field(default=0, ge=0)


class IgniteRequest(BaseModel):
    resistance_type: str = Field(default='拖延')
    current_risk_score: float = Field(default=0.5, ge=0.0, le=1.0)


class CompleteSessionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    outcome: dict = Field(default_factory=dict)
    reflection: str = Field(default='')


@app.post('/api/execution/crash-detect')
def crash_detect(payload: CrashDetectRequest, request: Request):
    """
    崩溃检测 - 前端兼容端点
    基于遥测数据检测执行力崩溃风险
    """
    try:
        from backend.psychology_engine import detect_execution_paralysis, calculate_micro_momentum
        
        # 基于遥测计算风险分数
        telemetry = {
            'task_attempts': payload.task_attempts,
            'escape_urges': payload.escape_urges,
            'last_session_minutes': payload.last_session_minutes
        }
        
        # 风险评分算法
        risk_score = min(1.0, (
            (payload.escape_urges * 0.15) + 
            (max(0, 3 - payload.last_session_minutes) * 0.1) +
            (max(0, payload.task_attempts - 5) * 0.05)
        ))
        
        detected = risk_score >= 0.4
        
        # 检测到的崩溃模式
        crash_pattern = None
        core_resistance = None
        if detected:
            if payload.escape_urges >= 3:
                crash_pattern = '频繁逃避冲动'
                core_resistance = '焦虑回避'
            elif payload.last_session_minutes < 5:
                crash_pattern = '无法启动专注'
                core_resistance = '启动困难'
            elif payload.task_attempts >= 10:
                crash_pattern = '反复尝试失败'
                core_resistance = '完美主义瘫痪'
            else:
                crash_pattern = '一般性执行崩溃'
                core_resistance = '未知阻力'
        
        result = {
            'detected': detected,
            'risk_score': round(risk_score, 2),
            'crash_pattern': crash_pattern,
            'core_resistance': core_resistance,
            'escalation_needed': risk_score >= 0.7,
            'circuit_breaker_recommendations': [
                '暂停当前任务，进行5次深呼吸',
                '切换到2分钟微任务',
                '降低任务难度至当前能量可承受范围'
            ] if detected else [],
            'telemetry': telemetry
        }
        
        # 如果检测到崩溃，记录到数据库
        if detected:
            user = _optional_user(request)
            if user:
                try:
                    conn = _get_db()
                    with conn.cursor() as cur:
                        cur.execute(
                            '''INSERT INTO execution_paralysis_logs 
                               (user_id, paralysis_type, detected_signals, intervention_triggered)
                               VALUES (%s, %s, %s, TRUE)
                               RETURNING id''',
                            (user['id'], crash_pattern, json.dumps(telemetry))
                        )
                        row = cur.fetchone()
                        conn.commit()
                        result['log_id'] = str(row[0])
                    _release_db(conn)
                except Exception as e:
                    print(f'[crash_detect] Failed to log: {e}', flush=True)
        
        return result
        
    except Exception as exc:
        print(f'[crash_detect] Failed: {exc}', flush=True)
        return {
            'detected': False,
            'risk_score': 0.5,
            'crash_pattern': None,
            'core_resistance': None,
            'error': str(exc)
        }


@app.post('/api/execution/ignite')
def ignite_sequence(payload: IgniteRequest, request: Request):
    """
    生成点火序列 - 前端兼容端点
    根据阻力类型和风险分数生成2分钟恢复序列
    """
    try:
        from backend.psychology_engine import generate_ignition_sequence
        
        # 生成点火序列
        sequence_data = generate_ignition_sequence(
            resistance_type=payload.resistance_type,
            current_risk_score=payload.current_risk_score
        )
        
        # 创建会话ID
        import uuid
        session_id = str(uuid.uuid4())
        
        user = _optional_user(request)
        user_id = user['id'] if user else None
        
        # 保存会话到数据库
        if user_id:
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    cur.execute(
                        '''INSERT INTO micro_scheduler_sessions
                           (user_id, session_type, original_task, decoupled_chain, 
                            total_steps, micro_momentum_score, session_status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           RETURNING id''',
                        (user_id, 'ignition', f'点火恢复: {payload.resistance_type}',
                         json.dumps(sequence_data.get('steps', [])),
                         len(sequence_data.get('steps', [])),
                         max(20, int((1 - payload.current_risk_score) * 100)),
                         'active')
                    )
                    row = cur.fetchone()
                    conn.commit()
                    session_id = str(row[0])
                _release_db(conn)
            except Exception as e:
                print(f'[ignite] Failed to save session: {e}', flush=True)
        
        return {
            'session_id': session_id,
            'steps': sequence_data.get('steps', []),
            'resistance_type': payload.resistance_type,
            'estimated_total_duration': sum(s.get('duration_seconds', 120) for s in sequence_data.get('steps', []))
        }
        
    except Exception as exc:
        print(f'[ignite] Failed: {exc}', flush=True)
        # 返回默认点火序列
        return {
            'session_id': 'fallback-' + str(uuid.uuid4())[:8],
            'steps': [
                {'step_id': '1', 'step_type': 'GROUNDING', 'title': '深呼吸', 'instruction': '进行3次深呼吸，每次吸气4秒，呼气6秒', 'duration_seconds': 60},
                {'step_id': '2', 'step_type': 'TWO_MINUTE_START', 'title': '2分钟启动', 'instruction': '设置计时器2分钟，开始任务的最小版本', 'duration_seconds': 120},
                {'step_id': '3', 'step_type': 'REWARD', 'title': '自我肯定', 'instruction': '完成！认可自己的努力，无论结果如何', 'duration_seconds': 30}
            ],
            'resistance_type': payload.resistance_type,
            'estimated_total_duration': 210
        }


@app.get('/api/execution/micro-momentum')
def get_micro_momentum(request: Request):
    """
    获取微动量数据 - 前端兼容端点
    """
    user = _optional_user(request)
    user_id = user['id'] if user else None
    
    try:
        if user_id:
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    # 获取今日会话统计
                    cur.execute(
                        '''SELECT COUNT(*), 
                                  COUNT(*) FILTER (WHERE steps_completed > 0),
                                  AVG(micro_momentum_score)
                           FROM micro_scheduler_sessions
                           WHERE user_id = %s 
                             AND started_at >= CURRENT_DATE
                             AND session_status != 'cancelled' ''',
                        (user_id,)
                    )
                    row = cur.fetchone()
                    total_today = row[0] or 0
                    completed_today = row[1] or 0
                    avg_momentum = row[2] or 50
                    
                    # 获取最近会话历史
                    cur.execute(
                        '''SELECT id, original_task, steps_completed, total_steps,
                                  micro_momentum_score, started_at, session_status
                           FROM micro_scheduler_sessions
                           WHERE user_id = %s
                           ORDER BY started_at DESC
                           LIMIT 10''',
                        (user_id,)
                    )
                    history = [{
                        'session_id': str(r[0]),
                        'task': r[1],
                        'completed_steps': r[2] or 0,
                        'total_steps': r[3] or 1,
                        'momentum_score': r[4] or 50,
                        'started_at': r[5].isoformat() if r[5] else None,
                        'completed': r[6] == 'completed'
                    } for r in cur.fetchall()]
                    
                    # 计算动量等级 (1-5)
                    momentum_score = int(avg_momentum)
                    if momentum_score >= 80:
                        momentum_level = 5
                    elif momentum_score >= 60:
                        momentum_level = 4
                    elif momentum_score >= 40:
                        momentum_level = 3
                    elif momentum_score >= 20:
                        momentum_level = 2
                    else:
                        momentum_level = 1
                    
                    return {
                        'momentum_score': momentum_score,
                        'momentum_level': momentum_level,
                        'sessions_completed_today': completed_today,
                        'streak_days': 0,  # 可扩展计算
                        'total_focus_minutes': completed_today * 2,  # 估算
                        'velocity': (completed_today / max(total_today, 1) - 0.5) * 2,  # -1 到 1
                        'session_history': history
                    }
            finally:
                _release_db(conn)
        
        # 未登录用户返回默认值
        return {
            'momentum_score': 50,
            'momentum_level': 3,
            'sessions_completed_today': 0,
            'streak_days': 0,
            'total_focus_minutes': 0,
            'velocity': 0,
            'session_history': []
        }
        
    except Exception as exc:
        print(f'[micro_momentum] Failed: {exc}', flush=True)
        return {
            'momentum_score': 50,
            'momentum_level': 3,
            'sessions_completed_today': 0,
            'streak_days': 0,
            'total_focus_minutes': 0,
            'velocity': 0,
            'session_history': []
        }


@app.post('/api/execution/complete')
def complete_session(payload: CompleteSessionRequest, request: Request):
    """
    完成微会话 - 前端兼容端点
    """
    user = _optional_user(request)
    user_id = user['id'] if user else None
    
    try:
        success = payload.outcome.get('completed', False)
        actual_duration = payload.outcome.get('actual_duration_minutes', 2)
        
        if user_id:
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    # 更新会话状态
                    cur.execute(
                        '''UPDATE micro_scheduler_sessions
                           SET session_status = %s,
                               steps_completed = %s,
                               micro_momentum_score = %s,
                               completed_at = NOW()
                           WHERE id = %s AND user_id = %s
                           RETURNING id''',
                        ('completed' if success else 'abandoned',
                         payload.outcome.get('steps_completed', 0),
                         70 if success else 30,
                         payload.session_id, user_id)
                    )
                    row = cur.fetchone()
                    conn.commit()
                    
                    if row:
                        return {
                            'success': True,
                            'session_id': payload.session_id,
                            'completed': success,
                            'momentum_delta': 10 if success else -5
                        }
            finally:
                _release_db(conn)
        
        return {
            'success': True,
            'session_id': payload.session_id,
            'completed': success,
            'momentum_delta': 10 if success else -5,
            'note': 'Not logged in, session not persisted'
        }
        
    except Exception as exc:
        print(f'[complete_session] Failed: {exc}', flush=True)
        return {
            'success': False,
            'error': str(exc)
        }


# ── 子系统四：身份认同重塑 API ────────────────────────────────

class IdentityReinforcementRequest(BaseModel):
    recent_behaviors: list = Field(default_factory=list)
    emotion_state: dict = Field(default_factory=dict)


class DeconstructLabelRequest(BaseModel):
    negative_label: str = Field(min_length=1, max_length=200)


@app.post('/api/identity/reinforce')
def identity_reinforce(payload: IdentityReinforcementRequest, request: Request):
    """
    身份认同强化 - 生成新自我认知
    
    帮助用户形成："我是能够长期成长的人" 而非 "我必须永远完美"
    """
    try:
        from backend.psychology_engine import reinforce_identity
        
        user = _optional_user(request)
        user_id = user['id'] if user else None
        
        # 获取用户历史数据
        emotion_logs = []
        if user_id:
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    cur.execute(
                        '''SELECT emotion_summary, intensity, valence 
                           FROM emotion_logs 
                           WHERE user_id = %s 
                           ORDER BY created_at DESC LIMIT 7''',
                        (user_id,)
                    )
                    emotion_logs = [{
                        'summary': r[0],
                        'intensity': r[1],
                        'valence': r[2]
                    } for r in cur.fetchall()]
                _release_db(conn)
            except Exception as e:
                print(f'[identity] Failed to fetch history: {e}', flush=True)
        
        result = reinforce_identity(
            user_history=emotion_logs,
            behaviors=payload.recent_behaviors,
            emotion_state=payload.emotion_state
        )
        
        # 保存到数据库
        if user_id:
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    cur.execute(
                        '''INSERT INTO identity_reinforcement_logs 
                           (user_id, current_narrative, narrative_type, negative_identity_labels,
                            target_identity, identity_category, reinforcement_language,
                            reinforcement_strength, user_resonance, migration_direction, migration_progress)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING id''',
                        (user_id, result.get('current_narrative'), result.get('narrative_type'),
                         json.dumps(result.get('negative_labels', [])),
                         result.get('target_identity'), result.get('identity_category', 'growth_continuity'),
                         result.get('reinforcement_language'), 7, 7,
                         result.get('long_term_migration'), result.get('migration_progress', 50))
                    )
                    row = cur.fetchone()
                    reinforcement_id = str(row[0])
                    
                    # 更新或创建人格迁移记录
                    try:
                        cur.execute(
                            '''SELECT id FROM personality_migrations 
                               WHERE user_id = %s AND migration_dimension = %s 
                               AND migration_status = 'in_progress'
                               ORDER BY started_at DESC LIMIT 1''',
                            (user_id, result.get('identity_category', 'growth_continuity'))
                        )
                        existing = cur.fetchone()
                        
                        if existing:
                            # 更新现有迁移进度
                            cur.execute(
                                '''UPDATE personality_migrations 
                                   SET progress_percentage = %s,
                                       supporting_evidence = array_append(supporting_evidence, %s::jsonb),
                                       current_stage = CASE WHEN %s >= 80 THEN 3 
                                                           WHEN %s >= 50 THEN 2 
                                                           ELSE 1 END
                                   WHERE id = %s''',
                                (result.get('migration_progress', 50),
                                 json.dumps({
                                     'event_type': 'identity_reinforcement',
                                     'description': result.get('reinforcement_language', '')[:100],
                                     'impact_score': min(10, result.get('migration_progress', 50) // 10),
                                     'reinforcement_id': reinforcement_id
                                 }),
                                 result.get('migration_progress', 50),
                                 result.get('migration_progress', 50),
                                 existing[0])
                            )
                        else:
                            # 创建新的迁移记录
                            cur.execute(
                                '''INSERT INTO personality_migrations 
                                   (user_id, migration_dimension, starting_identity, target_identity,
                                    migration_path, current_stage, supporting_evidence, 
                                    progress_percentage, estimated_completion)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 
                                           CURRENT_TIMESTAMP + INTERVAL '90 days')''',
                                (user_id, result.get('identity_category', 'growth_continuity'),
                                 result.get('current_narrative', '')[:200],
                                 result.get('target_identity', '')[:200],
                                 json.dumps([{
                                     'stage': 1,
                                     'milestone': '身份强化开始',
                                     'achieved_at': 'NOW()'
                                 }]),
                                 1,
                                 json.dumps([{
                                     'event_type': 'migration_started',
                                     'description': result.get('long_term_migration', '')[:100],
                                     'impact_score': 5
                                 }]),
                                 result.get('migration_progress', 50))
                            )
                    except Exception as e2:
                        print(f'[identity] Failed to update migration: {e2}', flush=True)
                    
                    conn.commit()
                    result['saved_id'] = reinforcement_id
                _release_db(conn)
            except Exception as e:
                print(f'[identity] Failed to save: {e}', flush=True)
        
        return result
        
    except Exception as exc:
        print(f'[identity_reinforce] Failed: {exc}', flush=True)
        return {
            'current_narrative': '正在探索中的自我',
            'target_identity': '我是可以成长的人',
            'reinforcement_language': '你正在前进，这就是最重要的。',
            'migration_progress': 30
        }


@app.post('/api/identity/deconstruct')
def deconstruct_label(payload: DeconstructLabelRequest, request: Request):
    """
    解构负面身份标签
    
    将"我是懒惰的人"转化为"我只是在特定条件下需要调整节奏"
    """
    try:
        from backend.psychology_engine import identity_engine
        result = identity_engine.deconstruct_negative_label(payload.negative_label)
        return result
    except Exception as exc:
        print(f'[deconstruct] Failed: {exc}', flush=True)
        return {
            'distortion_type': 'overgeneralization',
            'counter_evidence': ['你曾成功完成过任务', '你在这个平台上寻求帮助'],
            'reframed_identity': '我是一个在特定条件下会放慢节奏的人'
        }


@app.get('/api/identity/migrations')
def personality_migrations(request: Request):
    """
    人格迁移进度追踪
    
    查询用户正在进行和已完成的人格迁移
    """
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 获取所有迁移记录
            cur.execute(
                '''SELECT id, migration_dimension, starting_identity, target_identity,
                          migration_status, progress_percentage, current_stage,
                          migration_path, supporting_evidence, started_at, estimated_completion, achieved_at
                   FROM personality_migrations
                   WHERE user_id = %s
                   ORDER BY started_at DESC''',
                (user_id,)
            )
            rows = cur.fetchall()
            
            migrations = []
            for row in rows:
                migrations.append({
                    'id': str(row[0]),
                    'migration_dimension': row[1],
                    'starting_identity': row[2],
                    'target_identity': row[3],
                    'status': row[4],
                    'progress_percentage': row[5],
                    'current_stage': row[6],
                    'migration_path': row[7] or [],
                    'supporting_evidence': row[8] or [],
                    'started_at': row[9].isoformat() if row[9] else None,
                    'estimated_completion': row[10].isoformat() if row[10] else None,
                    'achieved_at': row[11].isoformat() if row[11] else None
                })
            
            # 统计汇总
            cur.execute(
                '''SELECT 
                      COUNT(*) FILTER (WHERE migration_status = 'in_progress') as active,
                      COUNT(*) FILTER (WHERE migration_status = 'completed') as completed,
                      COUNT(*) FILTER (WHERE migration_status = 'paused') as paused,
                      ROUND(AVG(progress_percentage), 1) as avg_progress
                   FROM personality_migrations
                   WHERE user_id = %s''',
                (user_id,)
            )
            stats = cur.fetchone()
            
            return {
                'migrations': migrations,
                'summary': {
                    'total': len(migrations),
                    'active': stats[0] or 0,
                    'completed': stats[1] or 0,
                    'paused': stats[2] or 0,
                    'avg_progress': stats[3] or 0
                }
            }
    finally:
        _release_db(conn)


@app.get('/api/identity/dashboard')
def identity_dashboard(request: Request):
    """身份认同仪表盘"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT current_identity_narrative, active_negative_labels,
                          avg_migration_progress, weekly_reinforcements, identity_clarity_score
                   FROM user_identity_dashboard 
                   WHERE user_id = %s''',
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return {
                    'current_narrative': None,
                    'active_negative_labels': 0,
                    'migration_progress': 0,
                    'weekly_reinforcements': 0,
                    'identity_clarity': 50
                }
            
            return {
                'current_narrative': row[0],
                'active_negative_labels': row[1] or 0,
                'migration_progress': row[2] or 0,
                'weekly_reinforcements': row[3] or 0,
                'identity_clarity': row[4] or 50
            }
    finally:
        _release_db(conn)


# ── Personality OS 全局系统 API ─────────────────────────────

class PersonalityOSProcessRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=2000)
    telemetry: dict = Field(default_factory=dict)
    current_state: str = Field(default='NORMAL')


class TelemetryReportRequest(BaseModel):
    subsystem: str = Field(min_length=1)
    telemetry_data: dict = Field(default_factory=dict)


@app.post('/api/os/process')
def personality_os_process(payload: PersonalityOSProcessRequest, request: Request):
    """
    Personality OS 主入口 - 全局协调处理
    
    整合所有子系统，根据全局状态返回协调响应
    """
    try:
        from backend.psychology_engine import process_with_personality_os
        
        user = _require_user(request)
        user_id = user['id']
        
        result = process_with_personality_os(
            user_id=user_id,
            user_input=payload.user_input,
            telemetry=payload.telemetry,
            current_state=payload.current_state
        )
        
        return result
        
    except Exception as exc:
        print(f'[personality_os] Failed: {exc}', flush=True)
        return {
            'personality_os_version': '1.0-degraded',
            'system_state': {'current_state': payload.current_state},
            'cognitive_load': {'total': 5},
            'global_config': {'task_intensity': 'reduced'},
            'subsystem_results': {},
            'error': str(exc)
        }


@app.post('/api/os/telemetry')
def report_telemetry(payload: TelemetryReportRequest, request: Request):
    """
    遥测数据上报 - 触发数据总线信号
    
    例如：执行力模块报告点火成功 -> 广播给习惯模块结算代币
    """
    try:
        from backend.psychology_engine import personality_os
        
        user = _require_user(request)
        user_id = user['id']
        
        # 处理遥测反馈，生成信号
        signals = personality_os.data_bus.process_telemetry_feedback(
            user_id=user_id,
            subsystem=payload.subsystem,
            telemetry_data=payload.telemetry_data
        )
        
        # 持久化信号到 data_bus_events 表
        if signals:
            try:
                conn = _get_db()
                with conn.cursor() as cur:
                    for sig in signals:
                        payload_json = json.dumps({**sig.get('payload', {}), 'user_id': user_id})
                        cur.execute(
                            '''INSERT INTO data_bus_events 
                               (event_type, event_source, event_target, event_payload, priority)
                               VALUES (%s, %s, %s, %s, %s)''',
                            (sig.get('event_type'), sig.get('source'), 
                             sig.get('target'), payload_json, sig.get('priority', 5))
                        )
                conn.commit()
            except Exception as e:
                print(f'[telemetry] Failed to persist signals: {e}', flush=True)
            finally:
                _release_db(conn)
        
        return {
            'ok': True,
            'signals_generated': len(signals),
            'signals': signals
        }
        
    except Exception as exc:
        print(f'[telemetry] Failed: {exc}', flush=True)
        return {'ok': False, 'error': str(exc)}


@app.get('/api/os/dashboard')
def personality_os_dashboard(request: Request):
    """
    Personality OS 全局仪表盘
    
    展示：当前状态、认知载荷、各子系统健康度、熔断次数
    """
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT current_state, current_energy, system_energy_level,
                          cognitive_load, l0_l4_active, behavior_active, execution_active,
                          identity_active, weekly_circuit_breakers, identity_health,
                          execution_health, behavior_health
                   FROM personality_os_dashboard 
                   WHERE user_id = %s''',
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return {
                    'current_state': 'NORMAL',
                    'current_energy': 3,
                    'cognitive_load': 5,
                    'subsystem_health': {
                        'psychology': True,
                        'behavior': True,
                        'execution': True,
                        'identity': True
                    },
                    'circuit_breakers': 0,
                    'overall_health': 70
                }
            
            return {
                'current_state': row[0] or 'NORMAL',
                'current_energy': row[1] or 3,
                'system_energy_level': row[2] or 3,
                'cognitive_load': row[3] or 5,
                'subsystem_health': {
                    'psychology': row[4] if row[4] is not None else True,
                    'behavior': row[5] if row[5] is not None else True,
                    'execution': row[6] if row[6] is not None else True,
                    'identity': row[7] if row[7] is not None else True
                },
                'circuit_breakers': row[8] or 0,
                'health_scores': {
                    'identity': row[9] or 50,
                    'execution': row[10] or 50,
                    'behavior': row[11] or 0
                }
            }
    finally:
        _release_db(conn)


@app.post('/api/os/set-state')
def set_system_state(payload: dict, request: Request):
    """
    手动设置系统状态（用于测试或特殊场景）
    
    广播状态变更信号给所有子系统
    """
    user = _require_user(request)
    user_id = user['id']
    new_state = payload.get('state', 'NORMAL')
    
    try:
        conn = _get_db()
        with conn.cursor() as cur:
            # 获取当前状态
            cur.execute(
                'SELECT current_state_code FROM user_system_states WHERE user_id = %s',
                (user_id,)
            )
            row = cur.fetchone()
            old_state = row[0] if row else 'NORMAL'
            
            # 更新状态
            cur.execute(
                '''INSERT INTO user_system_states (user_id, current_state_code, previous_state_code, state_entered_at)
                   VALUES (%s, %s, %s, NOW())
                   ON CONFLICT (user_id) 
                   DO UPDATE SET 
                       previous_state_code = user_system_states.current_state_code,
                       current_state_code = %s,
                       state_entered_at = NOW()''',
                (user_id, new_state, old_state, new_state)
            )
            
            # 记录迁移日志
            cur.execute(
                '''INSERT INTO state_transition_logs 
                   (user_id, from_state_code, to_state_code, transition_trigger, signals_broadcast)
                   VALUES (%s, %s, %s, %s, %s)''',
                (user_id, old_state, new_state, 'manual_override', 
                 json.dumps([{'type': 'manual_state_change', 'by': 'user'}]))
            )
            
            conn.commit()
        _release_db(conn)
        
        # 广播信号
        from backend.psychology_engine import personality_os
        personality_os.data_bus.broadcast_event(
            event_type='command',
            source='system',
            target='all',
            payload={
                'user_id': user_id,
                'command': 'STATE_CHANGE',
                'new_state': new_state,
                'old_state': old_state,
                'reason': 'manual_override'
            },
            priority=1
        )
        
        return {'ok': True, 'new_state': new_state, 'old_state': old_state}
        
    except Exception as exc:
        print(f'[set_state] Failed: {exc}', flush=True)
        return {'ok': False, 'error': str(exc)}


# ============================================================
# 人格塑造、习惯养成、行为追踪系统 API
# ============================================================

# Pydantic 模型
class BehaviorRegulateRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    energy_level: int = Field(default=3, ge=1, le=5)
    motivation: int = Field(default=5, ge=1, le=10)


class HabitCreateRequest(BaseModel):
    habit_name: str = Field(min_length=1, max_length=200)
    anchor: str = Field(default='', max_length=200)
    energy_level: int = Field(default=3, ge=1, le=5)


class HabitExecuteRequest(BaseModel):
    habit_id: str = Field(min_length=1)
    energy_level: int = Field(default=3, ge=1, le=5)


class HabitLogRequest(BaseModel):
    habit_id: str = Field(min_length=1)
    tier_executed: str = Field(default='Yellow')
    was_completed: bool = Field(default=False)
    completion_percentage: int = Field(default=0, ge=0, le=100)
    mood_before: int = Field(default=5, ge=1, le=10)
    mood_after: int = Field(default=5, ge=1, le=10)


# ── 行为调节系统 API ─────────────────────────────────────────

@app.post('/api/behavior/regulate')
def behavior_regulate(payload: BehaviorRegulateRequest, request: Request):
    """
    行为调节引擎 - 动态行为工程学
    基于当前能量和动机水平，推荐最小可执行动作
    """
    user = _require_user(request)
    try:
        from backend.habit_behavior_engine import regulate_behavior
        result = regulate_behavior(payload.task, payload.energy_level)

        # 保存行为调节会话到数据库
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''INSERT INTO behavior_regulation_sessions
                       (user_id, session_type, target_habit, motivation_level,
                        energy_level, selected_tier, min_executable_action,
                        task_downgrade, emotional_compensation, continuity_advice)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (user['id'], 'habit_task', payload.task, payload.motivation,
                     payload.energy_level, result.get('selected_tier'),
                     result.get('min_executable_action'),
                     result.get('task_downgrade'),
                     result.get('emotional_compensation'),
                     result.get('continuity_advice'))
                )
                conn.commit()

                # Auto-extract persona tags from behavior regulation
                try:
                    from backend.persona_tag_engine import get_tag_engine
                    engine = get_tag_engine()
                    behavior_text = f"{payload.task} 能量{payload.energy_level} 动机{payload.motivation}"
                    engine.auto_extract_and_store(
                        conn, user['id'], behavior_text, 'behavior_regulation', None
                    )
                except Exception as te:
                    print(f'[persona_tags] Behavior extraction failed: {te}', flush=True)
        finally:
            _release_db(conn)

        return result
    except Exception as exc:
        print(f'[behavior_regulate] Failed: {exc}', flush=True)
        tier = "Red" if payload.energy_level <= 2 else ("Yellow" if payload.energy_level <= 3 else "Green")
        return {
            "degraded": True,
            "selected_tier": tier,
            "min_executable_action": f"尝试{payload.task}的最小版本" if tier == "Red" else f"开始{payload.task}",
            "emotional_compensation": "系统智能降级，保持连续性",
            "continuity_advice": "任何微小启动都算成功"
        }


@app.get('/api/behavior/history')
def get_behavior_history(user_id: str = None, limit: int = 30, request: Request = None):
    """获取用户的行为调节历史"""
    user = _require_user(request)
    target_user_id = user_id or user['id']
    
    if target_user_id != user['id']:
        raise HTTPException(status_code=403, detail='只能查看自己的数据')
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, target_habit, energy_level, motivation_level, selected_tier,
                          min_executable_action, was_completed, completion_percentage,
                          started_at
                   FROM behavior_regulation_sessions 
                   WHERE user_id = %s
                   ORDER BY started_at DESC
                   LIMIT %s''',
                (target_user_id, limit)
            )
            rows = cur.fetchall()
            
            items = [{
                'id': str(r[0]),
                'task': r[1],
                'energy_level': r[2],
                'motivation': r[3],
                'tier_executed': r[4],
                'min_executable_action': r[5],
                'was_completed': r[6],
                'completion_percentage': r[7],
                'executed_at': r[8].isoformat() if r[8] else None,
            } for r in rows]
            
        return {'items': items, 'count': len(items)}
    finally:
        _release_db(conn)


@app.get('/api/behavior/stats')
def get_behavior_stats(user_id: str = None, request: Request = None):
    """获取用户的行为调节统计"""
    user = _require_user(request)
    target_user_id = user_id or user['id']
    
    if target_user_id != user['id']:
        raise HTTPException(status_code=403, detail='只能查看自己的数据')
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 总体统计
            cur.execute(
                '''SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_completed THEN 1 ELSE 0 END) as completed,
                    AVG(completion_percentage) as avg_completion,
                    AVG(energy_level) as avg_energy
                   FROM behavior_regulation_sessions 
                   WHERE user_id = %s''',
                (target_user_id,)
            )
            row = cur.fetchone()
            
            total_regulations = row[0] or 0
            completed_regulations = row[1] or 0
            avg_completion_percentage = round(row[2] or 0, 1)
            avg_energy_level = round(row[3] or 3, 1)
            
            # 层级分布
            cur.execute(
                '''SELECT selected_tier, COUNT(*) 
                   FROM behavior_regulation_sessions 
                   WHERE user_id = %s
                   GROUP BY selected_tier''',
                (target_user_id,)
            )
            tier_distribution = {r[0]: r[1] for r in cur.fetchall()}
            
            # 最近7天统计
            cur.execute(
                '''SELECT COUNT(*) 
                   FROM behavior_regulation_sessions 
                   WHERE user_id = %s AND started_at > NOW() - INTERVAL '7 days' ''',
                (target_user_id,)
            )
            last_7_days = cur.fetchone()[0] or 0
            
        return {
            'total_regulations': total_regulations,
            'completed_regulations': completed_regulations,
            'completion_rate': round((completed_regulations / total_regulations * 100), 1) if total_regulations > 0 else 0,
            'avg_completion_percentage': avg_completion_percentage,
            'avg_energy_level': avg_energy_level,
            'tier_distribution': tier_distribution,
            'last_7_days_regulations': last_7_days
        }
    finally:
        _release_db(conn)


# ── 习惯养成状态机 API ───────────────────────────────────────

@app.post('/api/habits/create')
def create_habit_api(payload: HabitCreateRequest, request: Request):
    """
    创建习惯状态机 - 三层动态电路保护
    """
    user = _require_user(request)
    user_id = user['id']
    
    try:
        from backend.habit_behavior_engine import create_habit
        result = create_habit(payload.habit_name, payload.anchor, payload.energy_level)
        
        # 保存到数据库
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                fsm_config = result.get('habit_config', {})
                cur.execute(
                    '''INSERT INTO habit_state_machines 
                       (user_id, habit_name, deterministic_anchor, 
                        tier_green_config, tier_yellow_config, tier_red_config,
                        token_green_yield, token_yellow_yield, token_red_yield)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id''',
                    (user_id, payload.habit_name, fsm_config.get('deterministic_anchor', ''),
                     json.dumps(fsm_config.get('tier_configs', {}).get('green', {})),
                     json.dumps(fsm_config.get('tier_configs', {}).get('yellow', {})),
                     json.dumps(fsm_config.get('tier_configs', {}).get('red', {})),
                     10, 5, 1)
                )
                row = cur.fetchone()
                conn.commit()
                result['saved_habit_id'] = str(row[0])
        finally:
            _release_db(conn)
        
        return result
        
    except Exception as exc:
        print(f'[habits_create] Failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='创建习惯失败')


@app.get('/api/habits')
def list_habits(request: Request):
    """获取用户的习惯列表"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, habit_name, deterministic_anchor, is_active,
                          current_streak_days, total_executions, last_execution_at,
                          tier_green_config, tier_yellow_config, tier_red_config
                   FROM habit_state_machines 
                   WHERE user_id = %s AND is_active = TRUE
                   ORDER BY created_at DESC''',
                (user_id,)
            )
            rows = cur.fetchall()
            
            items = [{
                'id': str(r[0]),
                'habit_name': r[1],
                'anchor': r[2],
                'is_active': r[3],
                'current_streak': r[4],
                'total_executions': r[5],
                'last_execution': r[6].isoformat() if r[6] else None,
                'tier_configs': {
                    'green': r[7],
                    'yellow': r[8],
                    'red': r[9]
                }
            } for r in rows]
            
            return {'items': items, 'total': len(items)}
    finally:
        _release_db(conn)


@app.post('/api/habits/{habit_id}/execute')
def execute_habit(habit_id: str, payload: HabitExecuteRequest, request: Request):
    """
    执行习惯状态机 - 根据当前能量动态选择层级
    """
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        # 获取习惯配置
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT habit_name, deterministic_anchor,
                          tier_green_config, tier_yellow_config, tier_red_config
                   FROM habit_state_machines 
                   WHERE id = %s AND user_id = %s''',
                (habit_id, user_id)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail='习惯未找到')
            
            habit_config = {
                'habit_name': row[0],
                'deterministic_anchor': row[1],
                'tier_configs': {
                    'green': row[2],
                    'yellow': row[3],
                    'red': row[4]
                }
            }
        
        # 执行状态机
        from backend.habit_behavior_engine import habit_fsm
        execution = habit_fsm.execute_habit(habit_config, payload.energy_level)
        
        return execution.to_dict()
        
    finally:
        _release_db(conn)


@app.post('/api/habits/{habit_id}/log')
def log_habit_execution(habit_id: str, payload: HabitLogRequest, request: Request):
    """
    记录习惯执行结果，更新代币和连胜
    """
    user = _require_user(request)
    user_id = user['id']
    
    # 代币计算
    tier_tokens = {'Green': 10, 'Yellow': 5, 'Red': 1}
    tokens_earned = tier_tokens.get(payload.tier_executed, 5)
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # 记录执行日志
            cur.execute(
                '''INSERT INTO habit_execution_logs 
                   (user_id, habit_id, energy_level_at_execution, selected_tier,
                    tokens_earned, was_completed, completion_percentage,
                    circuit_breaker_triggered, mood_before, mood_after)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id''',
                (user_id, habit_id, 3, payload.tier_executed,
                 tokens_earned, payload.was_completed, payload.completion_percentage,
                 payload.tier_executed == 'Red',
                 payload.mood_before, payload.mood_after)
            )
            log_id = cur.fetchone()[0]
            
            # 更新习惯统计
            if payload.was_completed:
                cur.execute(
                    '''UPDATE habit_state_machines 
                       SET total_executions = total_executions + 1,
                           last_execution_at = NOW(),
                           current_streak_days = CASE 
                               WHEN last_execution_at >= CURRENT_DATE - INTERVAL '1 day' 
                               THEN current_streak_days + 1 
                               ELSE 1 
                           END
                       WHERE id = %s''',
                    (habit_id,)
                )
            
            # 更新代币账本
            cur.execute(
                '''INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (user_id) 
                   DO UPDATE SET 
                       current_balance = user_token_ledgers.current_balance + %s,
                       lifetime_earned = user_token_ledgers.lifetime_earned + %s,
                       last_updated = NOW()''',
                (user_id, tokens_earned, tokens_earned, tokens_earned, tokens_earned)
            )
            
            # 记录代币交易
            cur.execute(
                '''INSERT INTO token_transactions 
                   (user_id, transaction_type, amount, balance_after, habit_id, habit_log_id, description)
                   VALUES (%s, %s, %s, 
                       (SELECT current_balance FROM user_token_ledgers WHERE user_id = %s),
                       %s, %s, %s)''',
                (user_id, 'earn', tokens_earned, user_id, 
                 habit_id, log_id, f'{payload.tier_executed} tier execution')
            )
            
            conn.commit()
            
            return {
                'ok': True,
                'log_id': str(log_id),
                'tokens_earned': tokens_earned,
                'circuit_breaker_triggered': payload.tier_executed == 'Red',
                'anti_guilt_message': '系统已切换至保护模式。连胜保持。核心控制回路完整性100%。' 
                    if payload.tier_executed == 'Red' else None
            }
            
    finally:
        _release_db(conn)


@app.get('/api/habits/dashboard')
def habits_dashboard(request: Request):
    """习惯系统仪表盘"""
    user = _require_user(request)
    user_id = user['id']
    
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT active_habits, today_executions, max_current_streak,
                          token_balance, last_habit_name, circuit_breaker_count
                   FROM user_habit_dashboard 
                   WHERE user_id = %s''',
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row:
                return {
                    'active_habits': 0,
                    'today_executions': 0,
                    'current_streak': 0,
                    'token_balance': 0,
                    'circuit_breaker_count': 0
                }
            
            return {
                'active_habits': row[0] or 0,
                'today_executions': row[1] or 0,
                'current_streak': row[2] or 0,
                'token_balance': row[3] or 0,
                'last_habit_name': row[4],
                'circuit_breaker_count': row[5] or 0
            }
    finally:
        _release_db(conn)


# ── 人格塑造 API ─────────────────────────────────────────────

@app.get('/api/formation/profile')
async def get_formation_profile(user_id: str = None, request: Request = None):
    """获取人格塑造档案"""
    user = _require_user(request)
    target_user_id = user_id or user['id']
    
    if target_user_id != user['id']:
        raise HTTPException(status_code=403, detail='只能查看自己的数据')
    
    try:
        from backend.formation_engine import get_formation_engine
        engine = get_formation_engine()
        profile = await engine.get_profile(target_user_id)
        return profile
    except Exception as exc:
        print(f'[formation_profile] Failed: {exc}', flush=True)
        # Return baseline profile on error
        return {
            'user_id': target_user_id,
            'schema': 'v3.1',
            'state_vector': {
                'humility': 0.5, 'fear_tendency': 0.5, 'pride_tendency': 0.5,
                'emotional_stability': 0.5, 'truth_alignment': 0.5,
                'relational_health': 0.5, 'resilience': 0.5, 'inner_clarity': 0.5
            },
            'formation_arc': 'unknown',
            'trajectory_direction': 'unknown',
            'dominant_loop': 'none',
            'alignment_trend': 'stable',
            'current_trajectory': 'not yet determined',
            'data_points': 0,
            'note': 'Formation tracking begins with your first decision analysis.'
        }


# ── 人格画像标签系统 API ───────────────────────────────────────

class ExtractTagsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    context: str = Field(default='general')

class AddTagRequest(BaseModel):
    tag_name: str = Field(min_length=1, max_length=100)
    tag_category: str = Field(default='manual')
    weight: float = Field(default=1.0, ge=0.1, le=10.0)


@app.post('/api/persona/extract')
def extract_persona_tags(payload: ExtractTagsRequest, request: Request):
    """从文本中抽取人格标签"""
    user = _optional_user(request)
    try:
        from backend.persona_tag_engine import get_tag_engine
        engine = get_tag_engine()
        tags = engine.extract_tags_from_text(payload.text, payload.context)
        return {
            'tags': tags,
            'count': len(tags),
            'text_preview': payload.text[:50] + '...' if len(payload.text) > 50 else payload.text
        }
    except Exception as exc:
        print(f'[persona_extract] Failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='标签抽取失败')


@app.get('/api/persona/tags')
def get_persona_tags(category: str = None, limit: int = 50, request: Request = None):
    """获取用户的人格标签列表"""
    user = _require_user(request)
    user_id = user['id']
    conn = _get_db()
    try:
        from backend.persona_tag_engine import get_tag_engine
        engine = get_tag_engine()
        tags = engine.get_user_tags(conn, user_id, category, limit)
        return {
            'tags': tags,
            'category': category or 'all',
            'total': len(tags)
        }
    except Exception as exc:
        print(f'[persona_tags] Failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='获取标签失败')
    finally:
        _release_db(conn)


@app.post('/api/persona/tags')
def add_persona_tag(payload: AddTagRequest, request: Request):
    """手动添加用户标签"""
    user = _require_user(request)
    user_id = user['id']
    conn = _get_db()
    try:
        from backend.persona_tag_engine import get_tag_engine
        engine = get_tag_engine()
        engine.ensure_system_tags_in_db(conn)
        stored = engine.store_user_tags(conn, user_id, [{
            'tag_name': payload.tag_name,
            'tag_category': payload.tag_category,
            'weight': payload.weight,
            'confidence': 1.0
        }], source_type='manual')
        return {'success': True, 'tag': stored[0] if stored else None}
    except Exception as exc:
        print(f'[persona_add_tag] Failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='添加标签失败')
    finally:
        _release_db(conn)


@app.delete('/api/persona/tags/{tag_id}')
def delete_persona_tag(tag_id: str, request: Request):
    """删除用户标签关联"""
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'DELETE FROM user_persona_tags WHERE id = %s AND user_id = %s RETURNING id',
                (tag_id, user['id'])
            )
            row = cur.fetchone()
            conn.commit()
            if not row:
                raise HTTPException(status_code=404, detail='标签不存在或无权限')
        return {'success': True, 'deleted_id': tag_id}
    except HTTPException:
        raise
    except Exception as exc:
        print(f'[persona_delete_tag] Failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='删除标签失败')
    finally:
        _release_db(conn)


@app.get('/api/persona/profile')
def get_persona_profile(request: Request):
    """获取用户人格画像"""
    user = _require_user(request)
    user_id = user['id']
    conn = _get_db()
    try:
        from backend.persona_tag_engine import get_tag_engine
        engine = get_tag_engine()
        profile = engine.compute_user_profile(conn, user_id)
        return profile
    except Exception as exc:
        print(f'[persona_profile] Failed: {exc}', flush=True)
        # Return empty baseline profile
        return {
            'user_id': user_id,
            'tag_cloud': {},
            'emotion_dominance': {},
            'behavior_patterns': {},
            'habit_strength': {},
            'personality_vector': {},
            'stability_score': 5.0,
            'resilience_score': 5.0,
            'growth_trend': 'stable',
            'risk_level': 'low',
            'total_tags': 0,
            'note': '开始记录你的情绪和习惯，人格画像将逐渐成形。'
        }
    finally:
        _release_db(conn)


# ── 前端静态文件（SPA 回退）────────────────────────────────────

if FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse
    app.mount('/assets', StaticFiles(directory=str(FRONTEND_DIST / 'assets')), name='assets')

    @app.get('/{full_path:path}')
    def spa_fallback(full_path: str):
        index = FRONTEND_DIST / 'index.html'
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({'error': 'Frontend not built'}, status_code=404)
