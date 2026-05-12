"""
auth.py — 情感星球后端认证模块
提供邮箱注册、登录、验证码发送、重置密码等接口
"""

import asyncio
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import smtplib
import threading
import time
from email.mime.text import MIMEText

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

# ── 配置 ──────────────────────────────────────────────────────

# WeChat Mini Program 配置
WX_APP_ID = os.getenv('WX_APP_ID', '')
WX_APP_SECRET = os.getenv('WX_APP_SECRET', '')

# Email SMTP 配置
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.sina.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465') or '465')
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USER or 'noreply@emotion-sphere.com')
RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')

EMAIL_RE = re.compile(r'^[\w.+\-]+@[\w\-]+\.[\w.\-]+$')

# ── In-memory stores ──────────────────────────────────────────

# 验证码存储：email -> {code, expires}
_CODE_STORE: dict[str, dict] = {}
_CODE_LOCK = threading.Lock()
CODE_TTL_SECONDS = 600  # 10 分钟

# Session 存储：token -> user info
_SESSION_STORE: dict[str, dict] = {}
_SESSION_LOCK = threading.Lock()

# 安全审计锁
_AUDIT_LOCK = threading.Lock()


# ── 依赖注入：数据库获取函数（由 main.py 注入）─────────────────

_get_db_fn = None
_release_db_fn = None


def init_db_functions(get_db, release_db):
    """由 main.py 调用，注入数据库连接函数。"""
    global _get_db_fn, _release_db_fn
    _get_db_fn = get_db
    _release_db_fn = release_db


def _get_db():
    return _get_db_fn()


def _release_db(conn):
    return _release_db_fn(conn)


# ── 密码哈希 ──────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码（若可用），否则使用 SHA256+salt。"""
    if BCRYPT_AVAILABLE:
        return 'bcrypt:' + bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f'sha256:{salt}:{digest}'


def _verify_password(password: str, stored: str) -> bool:
    """验证密码，支持 bcrypt 和旧版 SHA256。"""
    try:
        if not stored or stored.strip() == '':
            return False
        if stored.startswith('bcrypt:'):
            if not BCRYPT_AVAILABLE:
                return False
            hash_value = stored[7:]
            return bcrypt.checkpw(password.encode('utf-8'), hash_value.encode('utf-8'))
        elif stored.startswith('sha256:'):
            _, salt, digest = stored.split(':', 2)
            return hmac.compare_digest(
                hashlib.sha256((salt + password).encode()).hexdigest(),
                digest
            )
        elif ':' in stored:
            salt, digest = stored.split(':', 1)
            return hmac.compare_digest(
                hashlib.sha256((salt + password).encode()).hexdigest(),
                digest
            )
        return False
    except Exception as exc:
        print(f'[auth] verify_password error: {exc}', flush=True)
        return False


# ── 安全审计 ──────────────────────────────────────────────────

def _security_audit(event_type: str, email: str = None, ip: str = None,
                    details: dict = None, success: bool = True):
    with _AUDIT_LOCK:
        status = 'SUCCESS' if success else 'FAILED'
        print(f'[SECURITY] [{status}] {event_type} | email={email} | ip={ip} | details={details}',
              flush=True)
        try:
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        '''INSERT INTO security_audit
                           (event_type, email, ip_address, details, success, created_at)
                           VALUES (%s, %s, %s, %s, %s, NOW())''',
                        (event_type, email, ip[:45] if ip else None,
                         json.dumps(details) if details else '{}', success)
                    )
                    conn.commit()
            finally:
                _release_db(conn)
        except Exception as exc:
            print(f'[SECURITY] Failed to write audit log: {exc}', flush=True)


# ── 用户数据库操作 ─────────────────────────────────────────────

def _get_user(email: str) -> dict | None:
    """通过邮箱获取用户（不区分大小写）。"""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, email, nickname, avatar, openid, unionid,
                          login_type, password_hash, created_at
                   FROM users WHERE LOWER(email) = LOWER(%s)''',
                (email,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'email': row[1], 'nickname': row[2],
                'avatar': row[3], 'openid': row[4], 'unionid': row[5],
                'login_type': row[6], 'password_hash': row[7] or '',
                'created_at': row[8].timestamp() if row[8] else None,
            }
    finally:
        _release_db(conn)


def _get_user_by_email_public(email: str) -> dict | None:
    """获取用户公开信息（不含密码哈希）。"""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, email, nickname, avatar, login_type, created_at
                   FROM users WHERE LOWER(email) = LOWER(%s)''',
                (email,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'email': row[1], 'nickname': row[2],
                'avatar': row[3], 'login_type': row[4],
                'created_at': row[5].timestamp() if row[5] else None,
            }
    finally:
        _release_db(conn)


def _create_user(email: str | None, nickname: str, avatar: str,
                 openid: str | None, password_hash: str, login_type: str = 'email') -> dict:
    print(f'[auth] creating user email={email} openid={openid} nickname={nickname}', flush=True)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO users (email, nickname, avatar, openid, login_type, password_hash)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
                (email, nickname, avatar, openid, login_type, password_hash),
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        return {
            'id': user_id, 'email': email, 'nickname': nickname,
            'avatar': avatar, 'openid': openid, 'unionid': None,
            'login_type': login_type, 'created_at': time.time(),
        }
    finally:
        _release_db(conn)


# ── Session 管理 ──────────────────────────────────────────────

def _make_session(user_record: dict) -> str:
    token = secrets.token_urlsafe(32)
    email = user_record.get('email', '')
    data_json = json.dumps(user_record, ensure_ascii=False)
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO user_tokens (token, email, data, created_at, expires_at)
                   VALUES (%s, %s, %s, NOW(), NOW() + INTERVAL '30 days')
                   ON CONFLICT (token) DO UPDATE
                   SET email = EXCLUDED.email, data = EXCLUDED.data,
                       created_at = EXCLUDED.created_at, expires_at = EXCLUDED.expires_at''',
                (token, email, data_json)
            )
            conn.commit()
    finally:
        _release_db(conn)
    with _SESSION_LOCK:
        _SESSION_STORE[token] = user_record
    return token


def get_session_user(request: Request) -> dict | None:
    """从 Authorization header 或 query param 中提取用户信息。"""
    auth = request.headers.get('Authorization', '')
    token = auth[7:].strip() if auth.startswith('Bearer ') else \
        request.query_params.get('token', '')
    if not token:
        return None
    with _SESSION_LOCK:
        user = _SESSION_STORE.get(token)
    if user is not None:
        return user
    # 冷启动 fallback：从数据库恢复
    try:
        conn = _get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''SELECT data FROM user_tokens
                       WHERE token = %s AND (expires_at IS NULL OR expires_at > NOW())''',
                    (token,)
                )
                row = cur.fetchone()
                if row:
                    user = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    with _SESSION_LOCK:
                        _SESSION_STORE[token] = user
                    return user
        finally:
            _release_db(conn)
    except Exception as exc:
        print(f'[auth] session DB fallback failed: {exc}', flush=True)
    return None


# ── 邮件发送 ──────────────────────────────────────────────────

def _send_email(to: str, subject: str, body: str) -> None:
    """通过 SendGrid / Resend / SMTP 发送邮件（按顺序尝试）。"""
    # 1. SendGrid
    if SENDGRID_API_KEY:
        try:
            resp = httpx.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={'Authorization': f'Bearer {SENDGRID_API_KEY}',
                         'Content-Type': 'application/json'},
                json={
                    'personalizations': [{'to': [{'email': to}]}],
                    'from': {'email': SMTP_FROM or 'noreply@emotion-sphere.com'},
                    'subject': subject,
                    'content': [{'type': 'text/plain', 'value': body}],
                },
                timeout=20,
            )
            resp.raise_for_status()
            print(f'[email] SendGrid OK to {to}', flush=True)
            return
        except Exception as exc:
            print(f'[email] SendGrid failed: {exc}', flush=True)

    # 2. Resend
    if RESEND_API_KEY:
        from_addr = SMTP_FROM if SMTP_FROM else 'onboarding@resend.dev'
        try:
            resp = httpx.post(
                'https://api.resend.com/emails',
                headers={'Authorization': f'Bearer {RESEND_API_KEY}',
                         'Content-Type': 'application/json'},
                json={'from': from_addr, 'to': [to], 'subject': subject, 'text': body},
                timeout=20,
            )
            resp.raise_for_status()
            print(f'[email] Resend OK to {to}', flush=True)
            return
        except Exception as exc:
            print(f'[email] Resend failed: {exc}', flush=True)

    # 3. SMTP fallback
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_FROM):
        raise RuntimeError('No email service configured (SendGrid/Resend/SMTP all unavailable)')
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_FROM, [to], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                s.ehlo()
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_FROM, [to], msg.as_string())
        print(f'[email] SMTP OK to {to}', flush=True)
    except smtplib.SMTPException as exc:
        print(f'[email] SMTP failed: {exc}', flush=True)
        raise


# ── Pydantic 模型 ──────────────────────────────────────────────

class EmailSendCodeRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class EmailRegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(default='', max_length=64)


class EmailLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class EmailResetPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    code: str = Field(min_length=4, max_length=10)
    password: str = Field(min_length=6, max_length=128)


class WxappLoginRequest(BaseModel):
    code: str = Field(min_length=1)
    nickname: str = Field(default='')
    avatar: str = Field(default='')


# ── 路由 ──────────────────────────────────────────────────────

router = APIRouter(prefix='/api/auth', tags=['auth'])


@router.post('/wxapp/login')
async def wxapp_login(request: Request, payload: WxappLoginRequest):
    """微信小程序登录（使用 wx.login 获取的 code）"""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] wxapp login attempt code={payload.code[:10]}...', flush=True)
    
    if not WX_APP_ID or not WX_APP_SECRET:
        raise HTTPException(status_code=500, detail='WeChat Mini Program credentials not configured')
        
    url = 'https://api.weixin.qq.com/sns/jscode2session'
    params = {
        'appid': WX_APP_ID,
        'secret': WX_APP_SECRET,
        'js_code': payload.code,
        'grant_type': 'authorization_code'
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        _security_audit('WXAPP_LOGIN_FAILED', ip=client_ip, details={'reason': 'timeout', 'error': str(exc)}, success=False)
        raise HTTPException(status_code=503, detail='微信服务请求超时，请稍后重试')
    except httpx.NetworkError as exc:
        _security_audit('WXAPP_LOGIN_FAILED', ip=client_ip, details={'reason': 'network_error', 'error': str(exc)}, success=False)
        raise HTTPException(status_code=503, detail='无法连接微信服务，请检查网络后重试')
    except Exception as exc:
        _security_audit('WXAPP_LOGIN_FAILED', ip=client_ip, details={'reason': 'request_failed', 'error': str(exc)}, success=False)
        raise HTTPException(status_code=503, detail='微信登录服务暂时不可用，请稍后重试')

    if not isinstance(data, dict):
        _security_audit('WXAPP_LOGIN_FAILED', ip=client_ip, details={'reason': 'invalid_response'}, success=False)
        raise HTTPException(status_code=503, detail='微信服务返回异常，请稍后重试')

    if 'errcode' in data and data['errcode'] != 0:
        _security_audit('WXAPP_LOGIN_FAILED', ip=client_ip, details={'reason': 'wechat_error', 'errcode': data['errcode']}, success=False)
        raise HTTPException(status_code=401, detail=f"微信登录失败：{data.get('errmsg', str(data['errcode']))}")

    openid = data.get('openid')
    if not openid:
        raise HTTPException(status_code=401, detail='未能从微信获取用户标识，请重试')

    conn = _get_db()
    user_record = None
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, email, nickname, avatar, openid, unionid,
                          login_type, password_hash, created_at
                   FROM users WHERE openid = %s''',
                (openid,)
            )
            row = cur.fetchone()
            if row:
                user_record = {
                    'id': row[0], 'email': row[1], 'nickname': row[2],
                    'avatar': row[3], 'openid': row[4], 'unionid': row[5],
                    'login_type': row[6], 'password_hash': row[7] or '',
                    'created_at': row[8].timestamp() if row[8] else None,
                }
                # 如果传入了新的昵称或头像则更新
                if (payload.nickname and payload.nickname != row[2]) or (payload.avatar and payload.avatar != row[3]):
                    new_nick = payload.nickname or row[2]
                    new_avatar = payload.avatar or row[3]
                    cur.execute(
                        'UPDATE users SET nickname = %s, avatar = %s WHERE id = %s',
                        (new_nick, new_avatar, row[0])
                    )
                    conn.commit()
                    user_record['nickname'] = new_nick
                    user_record['avatar'] = new_avatar
    finally:
        _release_db(conn)

    if not user_record:
        nickname = payload.nickname or f"用户_{str(openid)[-4:]}"
        avatar = payload.avatar or ""
        user_record = _create_user(
            email=None, 
            nickname=nickname, 
            avatar=avatar, 
            openid=openid, 
            password_hash='', 
            login_type='wxapp'
        )

    public = {k: v for k, v in user_record.items() if k != 'password_hash'}
    token = _make_session(public)
    
    _security_audit('WXAPP_LOGIN_SUCCESS', ip=client_ip, details={'openid': openid, 'nickname': public['nickname']}, success=True)
    return {'ok': True, 'token': token, 'user': public}


@router.get('/me')
def auth_me(request: Request):
    """验证 session token，返回用户信息。"""
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid or expired session')
    return {'ok': True, 'user': user}


@router.post('/logout')
def auth_logout(request: Request):
    """注销 session token。"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header[7:].strip() if auth_header.startswith('Bearer ') else ''
    if token:
        with _SESSION_LOCK:
            _SESSION_STORE.pop(token, None)
        try:
            conn = _get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM user_tokens WHERE token = %s', (token,))
                    conn.commit()
            finally:
                _release_db(conn)
        except Exception:
            pass
    return {'ok': True}


@router.post('/email/send-code')
async def email_send_code(request: Request, payload: EmailSendCodeRequest):
    """向指定邮箱发送 6 位注册验证码。"""
    print(f'[auth] send-code request for email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail='Invalid email address')

    # 检查是否已注册
    existing_user = _get_user_by_email_public(email)
    if existing_user:
        print(f'[auth] email already registered: {email}', flush=True)
        return {'ok': False, 'registered': True, 'message': '该邮箱已注册，请直接登录'}

    # 频率限制：60 秒内只发一次
    with _CODE_LOCK:
        existing = _CODE_STORE.get(email)
        if existing and existing['expires'] - 240 > time.time():
            raise HTTPException(status_code=429, detail='Please wait before requesting another code')

    code = f'{random.randint(0, 999999):06d}'
    expires = time.time() + 300  # 5 分钟有效
    with _CODE_LOCK:
        _CODE_STORE[email] = {'code': code, 'expires': expires}

    body = (
        f'您的情感星球验证码：\n\n'
        f'  {code}\n\n'
        f'验证码 5 分钟内有效，请勿转发给他人。\n\n'
        f'Bible Emotion Sphere'
    )

    has_email_service = bool(SENDGRID_API_KEY) or bool(RESEND_API_KEY) or \
                        (bool(SMTP_USER) and bool(SMTP_PASS))
    if not has_email_service:
        print(f'[auth][DEV] verification code for {email}: {code}', flush=True)
        return {'ok': True, 'dev_code': code}

    try:
        await asyncio.to_thread(_send_email, email, '情感星球 – 邮箱验证码', body)
        print(f'[auth] verification code sent to {email}', flush=True)
        return {'ok': True}
    except Exception as exc:
        import traceback
        print(f'[auth] email send failed to {email}: {exc}', flush=True)
        traceback.print_exc()
        # 邮件发送失败时返回 dev_code，方便本地调试
        return {'ok': True, 'dev_code': code,
                'warning': 'Email delivery failed. Use the code displayed below.'}


@router.post('/email/register')
def email_register(request: Request, payload: EmailRegisterRequest):
    """邮箱 + 验证码 + 密码 注册新用户。"""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] register attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        _security_audit('REGISTER_FAILED', email=email, ip=client_ip,
                        details={'reason': 'invalid_email'}, success=False)
        raise HTTPException(status_code=400, detail='Invalid email address')

    # 校验验证码
    with _CODE_LOCK:
        entry = _CODE_STORE.get(email)
        if not entry or entry['expires'] < time.time():
            _security_audit('REGISTER_FAILED', email=email, ip=client_ip,
                            details={'reason': 'code_expired'}, success=False)
            raise HTTPException(status_code=400,
                                detail='Verification code expired, please request a new one')
        if not hmac.compare_digest(entry['code'], payload.code.strip()):
            _security_audit('REGISTER_FAILED', email=email, ip=client_ip,
                            details={'reason': 'invalid_code'}, success=False)
            raise HTTPException(status_code=400, detail='Incorrect verification code')
        del _CODE_STORE[email]

    if _get_user(email):
        _security_audit('REGISTER_FAILED', email=email, ip=client_ip,
                        details={'reason': 'email_exists'}, success=False)
        raise HTTPException(status_code=409, detail='Email already registered')

    nickname = payload.nickname.strip() or email.split('@')[0]
    public = _create_user(email, nickname, '', None, _hash_password(payload.password))
    token = _make_session(public)
    _security_audit('REGISTER_SUCCESS', email=email, ip=client_ip,
                    details={'nickname': nickname}, success=True)
    print(f'[auth] register ok email={email} nickname={nickname}', flush=True)
    return {'ok': True, 'token': token, 'user': public}


@router.post('/email/login')
def email_login(request: Request, payload: EmailLoginRequest):
    """邮箱 + 密码 登录。"""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] login attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    user_record = _get_user(email)
    if not user_record:
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip,
                        details={'reason': 'user_not_found'}, success=False)
        raise HTTPException(status_code=401, detail='Invalid email or password')
    stored_hash = user_record.get('password_hash', '')
    if not _verify_password(payload.password, stored_hash):
        _security_audit('LOGIN_FAILED', email=email, ip=client_ip,
                        details={'reason': 'wrong_password'}, success=False)
        raise HTTPException(status_code=401, detail='Invalid email or password')
    public = {k: v for k, v in user_record.items() if k != 'password_hash'}
    token = _make_session(public)
    _security_audit('LOGIN_SUCCESS', email=email, ip=client_ip,
                    details={'nickname': public.get('nickname')}, success=True)
    print(f'[auth] login ok email={email} nickname={public.get("nickname")}', flush=True)
    return {'ok': True, 'token': token, 'user': public}


@router.post('/email/send-reset-code')
async def email_send_reset_code(request: Request, payload: EmailSendCodeRequest):
    """发送重置密码验证码（邮箱必须已注册）。"""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] send-reset-code request for email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail='Invalid email address')

    user = _get_user(email)
    if not user:
        print(f'[auth] send-reset-code failed: email not registered {email}', flush=True)
        raise HTTPException(status_code=404, detail='该邮箱未注册，请先注册')

    code = f'{random.randint(0, 999999):06d}'
    with _CODE_LOCK:
        _CODE_STORE[email] = {'code': code, 'expires': time.time() + CODE_TTL_SECONDS}

    body = (
        f'您好！\n\n'
        f'您正在重置情感星球账户的密码。验证码：{code}\n\n'
        f'请在 10 分钟内输入此验证码完成密码重置。如非本人操作，请忽略此邮件。\n\n'
        f'情感星球'
    )

    has_email_service = bool(SENDGRID_API_KEY) or bool(RESEND_API_KEY) or \
                        (bool(SMTP_USER) and bool(SMTP_PASS))
    if not has_email_service:
        print(f'[auth][DEV] reset verification code for {email}: {code}', flush=True)
        return {'ok': True, 'dev_code': code}

    try:
        await asyncio.to_thread(_send_email, email, '情感星球 – 密码重置验证码', body)
        print(f'[auth] reset verification code sent to {email}', flush=True)
        return {'ok': True}
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500,
                            detail='Failed to send email, please try again later')


@router.post('/email/reset-password')
def email_reset_password(request: Request, payload: EmailResetPasswordRequest):
    """使用验证码重置密码。"""
    client_ip = request.client.host if request.client else 'unknown'
    print(f'[auth] reset-password attempt email={payload.email}', flush=True)
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail='Invalid email address')

    # 校验验证码
    with _CODE_LOCK:
        entry = _CODE_STORE.get(email)
        if not entry or entry['expires'] < time.time():
            _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip,
                            details={'reason': 'code_expired'}, success=False)
            raise HTTPException(status_code=400,
                                detail='Verification code expired, please request a new one')
        if not hmac.compare_digest(entry['code'], payload.code.strip()):
            _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip,
                            details={'reason': 'invalid_code'}, success=False)
            raise HTTPException(status_code=400, detail='Incorrect verification code')
        del _CODE_STORE[email]

    user_record = _get_user(email)
    if not user_record:
        _security_audit('PASSWORD_RESET_FAILED', email=email, ip=client_ip,
                        details={'reason': 'user_not_found'}, success=False)
        raise HTTPException(status_code=404, detail='User not found')

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET password_hash = %s WHERE LOWER(email) = LOWER(%s)',
                (_hash_password(payload.password), email)
            )
            conn.commit()
    finally:
        _release_db(conn)

    _security_audit('PASSWORD_RESET_SUCCESS', email=email, ip=client_ip,
                    details={}, success=True)
    print(f'[auth] password reset ok email={email}', flush=True)
    return {'ok': True, 'message': 'Password reset successfully, please login with new password'}
