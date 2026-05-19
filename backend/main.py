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


# ── 代祷墙 /api/prayers ────────────────────────────────────────

@app.get('/api/prayers')
def list_prayers(limit: int = 40, offset: int = 0, request: Request = None):
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT p.id, p.user_id, p.nickname, p.content, p.is_anonymous,
                          p.amen_count, p.created_at,
                          u.nickname as real_nickname, u.avatar
                   FROM prayers p LEFT JOIN users u ON u.id = p.user_id
                   WHERE p.is_deleted = FALSE
                   ORDER BY p.created_at DESC LIMIT %s OFFSET %s''',
                (limit, offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM prayers WHERE is_deleted=FALSE')
            total = cur.fetchone()[0]
        items = []
        for r in rows:
            nick = '匿名' if r[4] else (r[7] or r[2] or '用户')
            avatar = '' if r[4] else (r[8] or '')
            items.append({'id': r[0], 'user_id': r[1], 'nickname': nick,
                          'content': r[3], 'is_anonymous': r[4],
                          'amen_count': r[5],
                          'created_at': r[6].isoformat() if r[6] else None,
                          'avatar': avatar})
        return {'items': items, 'total': total}
    finally:
        _release_db(conn)


class PrayerSubmitRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    is_anonymous: bool = False


@app.post('/api/prayers')
def submit_prayer(payload: PrayerSubmitRequest, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO prayers (user_id, nickname, content, is_anonymous) '
                'VALUES (%s, %s, %s, %s) RETURNING id, created_at',
                (user['id'], user.get('nickname', ''),
                 payload.content.strip(), payload.is_anonymous)
            )
            row = cur.fetchone()
            conn.commit()
        return {'ok': True, 'id': row[0], 'created_at': row[1].isoformat()}
    finally:
        _release_db(conn)


@app.post('/api/prayers/{prayer_id}/amen')
def amen_prayer(prayer_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO prayer_amens (prayer_id, user_id) VALUES (%s,%s) '
                'ON CONFLICT DO NOTHING',
                (prayer_id, user['id'])
            )
            cur.execute(
                'UPDATE prayers SET amen_count = (SELECT COUNT(*) FROM prayer_amens WHERE prayer_id=%s) WHERE id=%s RETURNING amen_count',
                (prayer_id, prayer_id)
            )
            row = cur.fetchone()
            conn.commit()
        return {'ok': True, 'amen_count': row[0] if row else 0}
    finally:
        _release_db(conn)


@app.put('/api/prayers/{prayer_id}')
def update_prayer(prayer_id: int, payload: PrayerSubmitRequest, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE prayers SET content=%s, updated_at=NOW() WHERE id=%s AND user_id=%s',
                (payload.content.strip(), prayer_id, user['id'])
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@app.delete('/api/prayers/{prayer_id}')
def delete_prayer(prayer_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE prayers SET is_deleted=TRUE WHERE id=%s AND user_id=%s',
                (prayer_id, user['id'])
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@app.post('/api/prayers/{prayer_id}/restore')
def restore_prayer(prayer_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE prayers SET is_deleted=FALSE WHERE id=%s AND user_id=%s',
                (prayer_id, user['id'])
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


# ── 传福音祷告墙 /api/evangelism ──────────────────────────────

@app.get('/api/evangelism')
def list_evangelism(limit: int = 40, offset: int = 0):
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT p.id, p.user_id, p.nickname, p.content, p.is_anonymous,
                          p.amen_count, p.created_at,
                          u.nickname as real_nickname, u.avatar
                   FROM evangelism_prayers p LEFT JOIN users u ON u.id = p.user_id
                   WHERE p.is_deleted = FALSE
                   ORDER BY p.created_at DESC LIMIT %s OFFSET %s''',
                (limit, offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM evangelism_prayers WHERE is_deleted=FALSE')
            total = cur.fetchone()[0]
        items = []
        for r in rows:
            nick = '匿名' if r[4] else (r[7] or r[2] or '用户')
            avatar = '' if r[4] else (r[8] or '')
            items.append({'id': r[0], 'user_id': r[1], 'nickname': nick,
                          'content': r[3], 'is_anonymous': r[4],
                          'amen_count': r[5],
                          'created_at': r[6].isoformat() if r[6] else None,
                          'avatar': avatar})
        return {'items': items, 'total': total}
    finally:
        _release_db(conn)


@app.post('/api/evangelism')
def submit_evangelism(payload: PrayerSubmitRequest, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO evangelism_prayers (user_id, nickname, content, is_anonymous) '
                'VALUES (%s,%s,%s,%s) RETURNING id, created_at',
                (user['id'], user.get('nickname', ''),
                 payload.content.strip(), payload.is_anonymous)
            )
            row = cur.fetchone()
            conn.commit()
        return {'ok': True, 'id': row[0], 'created_at': row[1].isoformat()}
    finally:
        _release_db(conn)


@app.post('/api/evangelism/{prayer_id}/amen')
def amen_evangelism(prayer_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO evangelism_amens (prayer_id, user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                (prayer_id, user['id'])
            )
            cur.execute(
                'UPDATE evangelism_prayers SET amen_count=(SELECT COUNT(*) FROM evangelism_amens WHERE prayer_id=%s) WHERE id=%s RETURNING amen_count',
                (prayer_id, prayer_id)
            )
            row = cur.fetchone()
            conn.commit()
        return {'ok': True, 'amen_count': row[0] if row else 0}
    finally:
        _release_db(conn)


@app.put('/api/evangelism/{prayer_id}')
def update_evangelism(prayer_id: int, payload: PrayerSubmitRequest, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE evangelism_prayers SET content=%s, updated_at=NOW() WHERE id=%s AND user_id=%s',
                (payload.content.strip(), prayer_id, user['id'])
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@app.delete('/api/evangelism/{prayer_id}')
def delete_evangelism(prayer_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE evangelism_prayers SET is_deleted=TRUE WHERE id=%s AND user_id=%s',
                (prayer_id, user['id'])
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


@app.post('/api/evangelism/{prayer_id}/restore')
def restore_evangelism(prayer_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE evangelism_prayers SET is_deleted=FALSE WHERE id=%s AND user_id=%s',
                (prayer_id, user['id'])
            )
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


# ── 灵修日记 /api/devotion/journals ──────────────────────────

class DevotionJournalRequest(BaseModel):
    date: str = Field(min_length=1, max_length=20)
    title: str = Field(default='', max_length=200)
    content: str = Field(default='')
    verse: str = Field(default='', max_length=200)
    reflection: str = Field(default='')


@app.get('/api/devotion/journals')
def list_devotion_journals(limit: int = 50, offset: int = 0, request: Request = None):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, date, title, content, verse, reflection, created_at, updated_at '
                'FROM devotion_journals WHERE user_id=%s ORDER BY date DESC LIMIT %s OFFSET %s',
                (user['id'], limit, offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM devotion_journals WHERE user_id=%s', (user['id'],))
            total = cur.fetchone()[0]
        items = [{'id': r[0], 'date': str(r[1]), 'title': r[2], 'content': r[3],
                  'verse': r[4], 'reflection': r[5],
                  'created_at': r[6].isoformat() if r[6] else None,
                  'updated_at': r[7].isoformat() if r[7] else None} for r in rows]
        return {'items': items, 'total': total}
    finally:
        _release_db(conn)


@app.post('/api/devotion/journals')
def save_devotion_journal(payload: DevotionJournalRequest, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO devotion_journals (user_id, date, title, content, verse, reflection)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (user_id, date) DO UPDATE
                   SET title=EXCLUDED.title, content=EXCLUDED.content,
                       verse=EXCLUDED.verse, reflection=EXCLUDED.reflection, updated_at=NOW()
                   RETURNING id, date, title, content, verse, reflection, created_at, updated_at''',
                (user['id'], payload.date, payload.title, payload.content,
                 payload.verse, payload.reflection)
            )
            r = cur.fetchone()
            conn.commit()
        journal = {'id': r[0], 'date': str(r[1]), 'title': r[2], 'content': r[3],
                   'verse': r[4], 'reflection': r[5],
                   'created_at': r[6].isoformat() if r[6] else None,
                   'updated_at': r[7].isoformat() if r[7] else None}
        return {'ok': True, 'journal': journal}
    finally:
        _release_db(conn)


@app.delete('/api/devotion/journals/{journal_id}')
def delete_devotion_journal(journal_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM devotion_journals WHERE id=%s AND user_id=%s',
                        (journal_id, user['id']))
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


# ── 主日讲道笔记 /api/sermon/journals ────────────────────────

class SermonJournalRequest(BaseModel):
    date: str = Field(min_length=1, max_length=20)
    title: str = Field(default='', max_length=200)
    preacher: str = Field(default='', max_length=100)
    verse: str = Field(default='', max_length=200)
    content: str = Field(default='')
    reflection: str = Field(default='')


@app.get('/api/sermon/journals')
def list_sermon_journals(limit: int = 50, offset: int = 0, request: Request = None):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, date, title, preacher, verse, content, reflection, created_at, updated_at '
                'FROM sermon_journals WHERE user_id=%s ORDER BY date DESC LIMIT %s OFFSET %s',
                (user['id'], limit, offset)
            )
            rows = cur.fetchall()
            cur.execute('SELECT COUNT(*) FROM sermon_journals WHERE user_id=%s', (user['id'],))
            total = cur.fetchone()[0]
        items = [{'id': r[0], 'date': str(r[1]), 'title': r[2], 'preacher': r[3],
                  'verse': r[4], 'content': r[5], 'reflection': r[6],
                  'created_at': r[7].isoformat() if r[7] else None,
                  'updated_at': r[8].isoformat() if r[8] else None} for r in rows]
        return {'items': items, 'total': total}
    finally:
        _release_db(conn)


@app.post('/api/sermon/journals')
def save_sermon_journal(payload: SermonJournalRequest, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO sermon_journals (user_id, date, title, preacher, verse, content, reflection)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (user_id, date) DO UPDATE
                   SET title=EXCLUDED.title, preacher=EXCLUDED.preacher,
                       verse=EXCLUDED.verse, content=EXCLUDED.content,
                       reflection=EXCLUDED.reflection, updated_at=NOW()
                   RETURNING id, date, title, preacher, verse, content, reflection, created_at, updated_at''',
                (user['id'], payload.date, payload.title, payload.preacher,
                 payload.verse, payload.content, payload.reflection)
            )
            r = cur.fetchone()
            conn.commit()
        journal = {'id': r[0], 'date': str(r[1]), 'title': r[2], 'preacher': r[3],
                   'verse': r[4], 'content': r[5], 'reflection': r[6],
                   'created_at': r[7].isoformat() if r[7] else None,
                   'updated_at': r[8].isoformat() if r[8] else None}
        return {'ok': True, 'journal': journal}
    finally:
        _release_db(conn)


@app.delete('/api/sermon/journals/{journal_id}')
def delete_sermon_journal(journal_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM sermon_journals WHERE id=%s AND user_id=%s',
                        (journal_id, user['id']))
            conn.commit()
        return {'ok': True}
    finally:
        _release_db(conn)


# ── 个人日记 /api/personal/notes ─────────────────────────────

class PersonalNoteRequest(BaseModel):
    id: str = Field(default='')   # 前端本地生成的 uuid
    date: str = Field(min_length=1, max_length=20)
    title: str = Field(default='', max_length=200)
    content: str = Field(default='')
    mood: str = Field(default='', max_length=50)


@app.get('/api/personal/notes')
def list_personal_notes(request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, date, title, content, mood, created_at, updated_at '
                'FROM personal_notes WHERE user_id=%s ORDER BY date DESC',
                (user['id'],)
            )
            rows = cur.fetchall()
        items = [{'id': r[0], 'date': str(r[1]), 'title': r[2], 'content': r[3],
                  'mood': r[4], 'created_at': r[5].isoformat() if r[5] else None,
                  'updated_at': r[6].isoformat() if r[6] else None} for r in rows]
        return {'items': items}
    finally:
        _release_db(conn)


@app.post('/api/personal/notes')
def save_personal_note(payload: PersonalNoteRequest, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO personal_notes (user_id, date, title, content, mood)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (user_id, date) DO UPDATE
                   SET title=EXCLUDED.title, content=EXCLUDED.content,
                       mood=EXCLUDED.mood, updated_at=NOW()
                   RETURNING id, date, title, content, mood, created_at, updated_at''',
                (user['id'], payload.date, payload.title, payload.content, payload.mood)
            )
            r = cur.fetchone()
            conn.commit()
        note = {'id': r[0], 'date': str(r[1]), 'title': r[2], 'content': r[3],
                'mood': r[4], 'created_at': r[5].isoformat() if r[5] else None,
                'updated_at': r[6].isoformat() if r[6] else None}
        return {'ok': True, 'note': note}
    finally:
        _release_db(conn)


@app.delete('/api/personal/notes/{note_id}')
def delete_personal_note(note_id: int, request: Request):
    user = _require_user(request)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM personal_notes WHERE id=%s AND user_id=%s',
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
                    conn.commit()
                    result['saved_log_id'] = log_id
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


# ── 行为调节系统 API ─────────────────────────────────────────

class BehaviorRegulateRequest(BaseModel):
    task: str = Field(min_length=1, max_length=500)
    energy_level: int = Field(default=3, ge=1, le=5)
    motivation: int = Field(default=5, ge=1, le=10)


@app.post('/api/behavior/regulate')
def behavior_regulate(payload: BehaviorRegulateRequest, request: Request):
    """
    行为调节引擎 - 动态行为工程学
    基于当前能量和动机水平，推荐最小可执行动作
    """
    try:
        from backend.psychology_engine import regulate_behavior
        result = regulate_behavior(payload.task, payload.energy_level)
        return result
    except Exception as exc:
        print(f'[behavior_regulate] Failed: {exc}', flush=True)
        # 降级响应
        tier = "Red" if payload.energy_level <= 2 else ("Yellow" if payload.energy_level <= 3 else "Green")
        return {
            "degraded": True,
            "selected_tier": tier,
            "min_executable_action": f"尝试{payload.task}的最小版本" if tier == "Red" else f"开始{payload.task}",
            "emotional_compensation": "系统智能降级，保持连续性",
            "continuity_advice": "任何微小启动都算成功"
        }


# ── 习惯养成状态机 API ───────────────────────────────────────

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


@app.post('/api/habits/create')
def create_habit(payload: HabitCreateRequest, request: Request):
    """
    创建习惯状态机 - 三层动态电路保护
    """
    user = _require_user(request)
    user_id = user['id']
    
    try:
        from backend.psychology_engine import create_habit
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
        from backend.psychology_engine import habit_fsm
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
