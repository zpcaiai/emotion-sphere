"""
backend/main.py — 情感星球 FastAPI 后端
包含认证（/api/auth/*）及核心查询接口
"""

import asyncio
import json
import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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

    # 预热查询缓存（如果有）
    try:
        from query_emotion_verses import prewarm_cache
        await asyncio.to_thread(prewarm_cache)
        print('[startup] cache pre-warmed', flush=True)
    except Exception as exc:
        print(f'[startup] prewarm skipped: {exc}', flush=True)

    yield


# ── FastAPI 应用 ───────────────────────────────────────────────

app = FastAPI(title='Emotion Sphere API', lifespan=lifespan)

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
