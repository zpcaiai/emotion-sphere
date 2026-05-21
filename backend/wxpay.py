"""
wxpay.py — 微信商户支付收款子系统
支持: 小程序支付 (JSAPI miniprogram) / H5支付 / Native扫码支付

遵循微信支付 APIv3 规范（RSA 非对称加密 + AEAD_AES_256_GCM 回调解密）

环境变量:
  WXPAY_MCH_ID          微信商户号
  WXPAY_APP_ID          微信 AppID（小程序 / 公众号）
  WXPAY_API_V3_KEY      APIv3 密钥（32字节）
  WXPAY_PRIVATE_KEY     商户私钥 PEM 内容（多行）
  WXPAY_CERT_SERIAL_NO  商户证书序列号
  WXPAY_NOTIFY_URL      回调地址

提供:
  create_prepay(...)      → 预下单（返回调起支付所需参数）
  query_order(order_no)   → 查询微信侧订单状态
  refund_order(...)       → 申请退款
  POST /api/wxpay/notify  → 微信支付回调（验签 + 履约）
  POST /api/wxpay/refund-notify → 微信退款回调
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import random
import string
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

# ── 微信支付配置（lazy getter，支持运行时覆盖环境变量）─────────

def _cfg(key: str, fallback: str = '') -> str:
    return os.getenv(key, fallback)


# 内部全部走 getter，避免模块导入时固化值
def _mch_id()         -> str: return _cfg('WXPAY_MCH_ID')
def _app_id()         -> str: return _cfg('WXPAY_APP_ID', _cfg('WX_APP_ID'))
def _api_v3_key()     -> str: return _cfg('WXPAY_API_V3_KEY')
def _private_key_pem()-> str: return _cfg('WXPAY_PRIVATE_KEY')
def _cert_serial_no() -> str: return _cfg('WXPAY_CERT_SERIAL_NO')
def _notify_url()     -> str: return _cfg('WXPAY_NOTIFY_URL')

# 向后兼容的模块级常量（反映导入时的值，仅用于外部读取检查）
WXPAY_MCH_ID         = _cfg('WXPAY_MCH_ID')
WXPAY_APP_ID         = _cfg('WXPAY_APP_ID', _cfg('WX_APP_ID'))
WXPAY_API_V3_KEY     = _cfg('WXPAY_API_V3_KEY')
WXPAY_PRIVATE_KEY_PEM = _cfg('WXPAY_PRIVATE_KEY')
WXPAY_CERT_SERIAL_NO = _cfg('WXPAY_CERT_SERIAL_NO')
WXPAY_NOTIFY_URL     = _cfg('WXPAY_NOTIFY_URL')

# 微信支付 APIv3 base URL
_WX_PAY_BASE = 'https://api.mch.weixin.qq.com'


# ── RSA / AES 工具（cryptography 库）─────────────────────────

def _load_private_key():
    """加载商户私钥（PEM）。"""
    try:
        from cryptography.hazmat.primitives import serialization
        pem = _private_key_pem().strip()
        if not pem:
            raise RuntimeError('WXPAY_PRIVATE_KEY is not configured')
        # 支持直接粘贴 \n 字面量
        if '\\n' in pem and '\n' not in pem:
            pem = pem.replace('\\n', '\n')
        return serialization.load_pem_private_key(pem.encode(), password=None)
    except ImportError:
        raise RuntimeError('cryptography package is required for wxpay (pip install cryptography)')


def _rsa_sign(message: str) -> str:
    """使用商户私钥对消息进行 SHA256withRSA 签名，返回 Base64 编码结果。"""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    private_key = _load_private_key()
    signature = private_key.sign(message.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode('utf-8')


def _build_authorization(method: str, url_path: str, body: str) -> str:
    """构建微信支付 Authorization 请求头。"""
    nonce_str = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    timestamp = str(int(time.time()))
    # 按微信规范拼接签名串
    sign_str = f'{method}\n{url_path}\n{timestamp}\n{nonce_str}\n{body}\n'
    signature = _rsa_sign(sign_str)
    return (
        f'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{_mch_id()}",'
        f'nonce_str="{nonce_str}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{_cert_serial_no()}",'
        f'signature="{signature}"'
    )


def _wx_post(path: str, payload: dict) -> dict:
    """向微信支付 APIv3 发 POST 请求。"""
    url = _WX_PAY_BASE + path
    body = json.dumps(payload, ensure_ascii=False)
    auth = _build_authorization('POST', path, body)
    resp = httpx.post(
        url,
        content=body.encode('utf-8'),
        headers={
            'Authorization': auth,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'EmotionSphere/1.0',
        },
        timeout=15,
    )
    if resp.status_code not in (200, 204):
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise RuntimeError(f'wxpay API error {resp.status_code}: {err}')
    return resp.json() if resp.content else {}


def _wx_get(path: str) -> dict:
    """向微信支付 APIv3 发 GET 请求。"""
    url = _WX_PAY_BASE + path
    auth = _build_authorization('GET', path, '')
    resp = httpx.get(
        url,
        headers={
            'Authorization': auth,
            'Accept': 'application/json',
            'User-Agent': 'EmotionSphere/1.0',
        },
        timeout=15,
    )
    if resp.status_code not in (200, 204):
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise RuntimeError(f'wxpay API error {resp.status_code}: {err}')
    return resp.json() if resp.content else {}


# ── AEAD_AES_256_GCM 解密（回调数据）─────────────────────────

def _aes_gcm_decrypt(nonce: str, ciphertext: str, associated_data: str) -> str:
    """解密微信回调中的加密资源（resource.ciphertext）。"""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise RuntimeError('cryptography package required for wxpay callback decryption')

    key = _api_v3_key().encode('utf-8')
    if len(key) != 32:
        raise ValueError('WXPAY_API_V3_KEY must be exactly 32 bytes')
    aesgcm = AESGCM(key)
    ciphertext_bytes = base64.b64decode(ciphertext)
    plaintext = aesgcm.decrypt(
        nonce.encode('utf-8'),
        ciphertext_bytes,
        associated_data.encode('utf-8'),
    )
    return plaintext.decode('utf-8')


# ── 回调签名验证 ──────────────────────────────────────────────

def _verify_notify_signature(
    timestamp: str,
    nonce: str,
    body: str,
    signature: str,
    serial: str,
) -> bool:
    """
    验证微信回调签名（RSA SHA256）。
    生产环境需要从微信下载并缓存平台证书来验证。
    此处实现：若已配置 WXPAY_PLATFORM_CERT_PEM 则严格验证，否则仅做时间戳校验（DEV模式）。
    """
    platform_cert_pem = _cfg('WXPAY_PLATFORM_CERT_PEM')
    if not platform_cert_pem:
        # DEV 模式：仅验证时间戳在合理范围内（5分钟）
        try:
            ts = int(timestamp)
            if abs(time.time() - ts) > 300:
                print('[wxpay] notify timestamp out of range', flush=True)
                return False
            print('[wxpay] WARN: WXPAY_PLATFORM_CERT_PEM not set, signature check skipped (DEV)', flush=True)
            return True
        except ValueError:
            return False

    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography import x509

        pem = platform_cert_pem.strip()
        if '\\n' in pem and '\n' not in pem:
            pem = pem.replace('\\n', '\n')

        cert = x509.load_pem_x509_certificate(pem.encode())
        pub_key = cert.public_key()
        sign_str = f'{timestamp}\n{nonce}\n{body}\n'
        sig_bytes = base64.b64decode(signature)
        pub_key.verify(sig_bytes, sign_str.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception as exc:
        print(f'[wxpay] signature verification failed: {exc}', flush=True)
        return False


# ── 小程序支付调起参数签名 ────────────────────────────────────

def _sign_miniprogram_pay(prepay_id: str) -> dict:
    """生成小程序端调起支付所需的签名参数（wx.requestPayment）。"""
    timestamp = str(int(time.time()))
    nonce_str = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    pkg = f'prepay_id={prepay_id}'
    sign_str = f'{_app_id()}\n{timestamp}\n{nonce_str}\n{pkg}\n'
    pay_sign = _rsa_sign(sign_str)
    return {
        'timeStamp': timestamp,
        'nonceStr': nonce_str,
        'package': pkg,
        'signType': 'RSA',
        'paySign': pay_sign,
        'prepay_id': prepay_id,
    }


def _sign_jsapi_pay(prepay_id: str) -> dict:
    """生成 JSAPI 网页端调起支付所需的签名参数（WeixinJSBridge.invoke）。"""
    timestamp = str(int(time.time()))
    nonce_str = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    pkg = f'prepay_id={prepay_id}'
    sign_str = f'{_app_id()}\n{timestamp}\n{nonce_str}\n{pkg}\n'
    pay_sign = _rsa_sign(sign_str)
    return {
        'appId': _app_id(),
        'timeStamp': timestamp,
        'nonceStr': nonce_str,
        'package': pkg,
        'signType': 'RSA',
        'paySign': pay_sign,
        'prepay_id': prepay_id,
    }


# ── 核心支付函数 ──────────────────────────────────────────────

def _check_config():
    missing = []
    for var in ('WXPAY_MCH_ID', 'WXPAY_APP_ID', 'WXPAY_API_V3_KEY',
                'WXPAY_PRIVATE_KEY', 'WXPAY_CERT_SERIAL_NO', 'WXPAY_NOTIFY_URL'):
        if not _cfg(var).strip():
            missing.append(var)
    if missing:
        raise RuntimeError(f'微信支付配置不完整，缺少: {", ".join(missing)}')


def create_prepay(
    out_trade_no: str,
    total_fee: int,
    description: str,
    pay_method: str,
    openid: str = '',
    client_ip: str = '127.0.0.1',
) -> dict:
    """
    发起微信支付预下单，返回前端调起支付所需参数。
    pay_method: miniprogram / jsapi / native / h5
    """
    _check_config()
    if not client_ip or client_ip == 'unknown':
        client_ip = '127.0.0.1'

    notify_url = _notify_url().rstrip('/') + '/api/wxpay/notify'

    base_payload: dict[str, Any] = {
        'appid': _app_id(),
        'mchid': _mch_id(),
        'description': description[:127],
        'out_trade_no': out_trade_no,
        'notify_url': notify_url,
        'amount': {'total': total_fee, 'currency': 'CNY'},
    }

    if pay_method in ('miniprogram', 'jsapi'):
        if not openid:
            raise ValueError('openid 为必填项（JSAPI/小程序支付）')
        base_payload['payer'] = {'openid': openid}
        path = '/v3/pay/transactions/jsapi'
        result = _wx_post(path, base_payload)
        prepay_id = result.get('prepay_id', '')
        if not prepay_id:
            raise RuntimeError(f'微信预下单未返回 prepay_id: {result}')
        if pay_method == 'miniprogram':
            return _sign_miniprogram_pay(prepay_id)
        return _sign_jsapi_pay(prepay_id)

    elif pay_method == 'native':
        path = '/v3/pay/transactions/native'
        result = _wx_post(path, base_payload)
        code_url = result.get('code_url', '')
        if not code_url:
            raise RuntimeError(f'微信预下单未返回 code_url: {result}')
        return {'code_url': code_url, 'pay_method': 'native'}

    elif pay_method == 'h5':
        base_payload['scene_info'] = {
            'payer_client_ip': client_ip,
            'h5_info': {'type': 'Wap', 'app_name': '情感星球'},
        }
        path = '/v3/pay/transactions/h5'
        result = _wx_post(path, base_payload)
        h5_url = result.get('h5_url', '')
        if not h5_url:
            raise RuntimeError(f'微信 H5 预下单未返回 h5_url: {result}')
        return {'h5_url': h5_url, 'pay_method': 'h5'}

    else:
        raise ValueError(f'不支持的支付方式: {pay_method}')


def query_order(out_trade_no: str) -> dict:
    """向微信查询订单实时状态。"""
    _check_config()
    path = f'/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={_mch_id()}'
    return _wx_get(path)


def refund_order(
    out_trade_no: str,
    refund_no: str,
    refund_amount: int,
    total_amount: int,
    reason: str = '用户申请退款',
) -> dict:
    """申请退款。refund_amount / total_amount 均为分。"""
    _check_config()
    notify_url = WXPAY_NOTIFY_URL.rstrip('/') + '/api/wxpay/refund-notify'
    payload = {
        'out_trade_no': out_trade_no,
        'out_refund_no': refund_no,
        'reason': reason[:80],
        'notify_url': notify_url,
        'amount': {
            'refund': refund_amount,
            'total': total_amount,
            'currency': 'CNY',
        },
    }
    return _wx_post('/v3/refund/domestic/refunds', payload)


# ── 依赖注入 ──────────────────────────────────────────────────

_get_db_fn = None
_release_db_fn = None


def init_db_functions(get_db, release_db):
    global _get_db_fn, _release_db_fn
    _get_db_fn = get_db
    _release_db_fn = release_db


def _get_db():
    return _get_db_fn()


def _release_db(conn):
    return _release_db_fn(conn)


# ── FastAPI 路由 ──────────────────────────────────────────────

router = APIRouter(prefix='/api/wxpay', tags=['wxpay'])


@router.post('/notify')
async def wxpay_payment_notify(request: Request):
    """
    微信支付成功回调。
    微信要求响应 200 {"code":"SUCCESS"} 或重试。
    """
    raw_body = await request.body()
    body_str = raw_body.decode('utf-8')

    # ── 读取微信回调签名头 ────────────────────────────────────
    timestamp    = request.headers.get('Wechatpay-Timestamp', '')
    nonce        = request.headers.get('Wechatpay-Nonce', '')
    signature    = request.headers.get('Wechatpay-Signature', '')
    serial       = request.headers.get('Wechatpay-Serial', '')
    headers_dict = dict(request.headers)

    conn = _get_db()
    log_id = None
    try:
        # ── 写入原始回调日志 ──────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO wxpay_notify_logs
                   (event_type, raw_body, headers, verified, processed)
                   VALUES (%s, %s, %s, FALSE, FALSE)
                   RETURNING id''',
                ('TRANSACTION.SUCCESS', body_str,
                 json.dumps({k: v for k, v in headers_dict.items()
                             if k.lower().startswith('wechatpay')}))
            )
            log_id = cur.fetchone()[0]
        conn.commit()

        # ── 验证签名 ──────────────────────────────────────────
        verified = _verify_notify_signature(timestamp, nonce, body_str, signature, serial)
        if not verified:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE wxpay_notify_logs SET verified=FALSE, error_msg=%s WHERE id=%s',
                    ('signature_failed', log_id)
                )
            conn.commit()
            return JSONResponse({'code': 'FAIL', 'message': 'signature verification failed'},
                                status_code=401)

        # ── 解析回调体 ────────────────────────────────────────
        try:
            notify_data = json.loads(body_str)
        except json.JSONDecodeError as exc:
            _update_notify_log(conn, log_id, verified=True, processed=False,
                               error=f'json_parse_error: {exc}')
            return JSONResponse({'code': 'FAIL', 'message': 'invalid json'}, status_code=400)

        event_type = notify_data.get('event_type', '')
        resource   = notify_data.get('resource', {})

        if event_type != 'TRANSACTION.SUCCESS':
            # 非支付成功事件，忽略
            _update_notify_log(conn, log_id, verified=True, processed=True,
                               error=f'ignored_event: {event_type}')
            return JSONResponse({'code': 'SUCCESS', 'message': 'ok'})

        # ── 解密资源体 ────────────────────────────────────────
        try:
            plaintext = _aes_gcm_decrypt(
                nonce=resource['nonce'],
                ciphertext=resource['ciphertext'],
                associated_data=resource.get('associated_data', ''),
            )
            tx_data = json.loads(plaintext)
        except Exception as exc:
            _update_notify_log(conn, log_id, verified=True, processed=False,
                               error=f'decrypt_error: {exc}')
            return JSONResponse({'code': 'FAIL', 'message': 'decrypt failed'}, status_code=400)

        out_trade_no    = tx_data.get('out_trade_no', '')
        transaction_id  = tx_data.get('transaction_id', '')
        trade_state     = tx_data.get('trade_state', '')
        amount_total    = tx_data.get('amount', {}).get('total', 0)

        # 更新日志中的订单号
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE wxpay_notify_logs SET order_no=%s, wx_transaction_id=%s, verified=TRUE WHERE id=%s',
                (out_trade_no, transaction_id, log_id)
            )
        conn.commit()

        if trade_state != 'SUCCESS':
            _update_notify_log(conn, log_id, verified=True, processed=False,
                               error=f'trade_state_not_success: {trade_state}')
            return JSONResponse({'code': 'SUCCESS', 'message': 'ok'})

        # ── 更新订单为 paid ───────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE shop_orders
                   SET status = 'paid',
                       wx_transaction_id = %s,
                       paid_at = NOW(),
                       updated_at = NOW()
                   WHERE order_no = %s
                     AND status IN ('pending_payment', 'payment_failed')
                   RETURNING id''',
                (transaction_id, out_trade_no)
            )
            updated = cur.fetchone()

        if not updated:
            # 已处理过，幂等返回
            _update_notify_log(conn, log_id, verified=True, processed=True,
                               error='already_processed')
            conn.commit()
            return JSONResponse({'code': 'SUCCESS', 'message': 'ok'})

        conn.commit()

        # ── 履约（赠积分/解锁权益）───────────────────────────
        from backend.shop import fulfill_order
        try:
            fulfill_order(conn, out_trade_no)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f'[wxpay] fulfill_order failed for {out_trade_no}: {exc}', flush=True)
            _update_notify_log(conn, log_id, verified=True, processed=False,
                               error=f'fulfill_error: {exc}')
            conn.commit()
            # 履约失败：返回 FAIL 让微信重试，避免丢单
            return JSONResponse(
                {'code': 'FAIL', 'message': 'fulfill failed, will retry'},
                status_code=500
            )

        _update_notify_log(conn, log_id, verified=True, processed=True, error='')
        conn.commit()
        print(f'[wxpay] payment notify OK: {out_trade_no} tx={transaction_id}', flush=True)
        return JSONResponse({'code': 'SUCCESS', 'message': 'ok'})

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f'[wxpay] notify handler error: {exc}', flush=True)
        if log_id:
            try:
                _update_notify_log(conn, log_id, verified=False, processed=False,
                                   error=f'handler_exception: {exc}')
                conn.commit()
            except Exception:
                pass
        return JSONResponse({'code': 'FAIL', 'message': 'internal error'}, status_code=500)
    finally:
        _release_db(conn)


@router.post('/refund-notify')
async def wxpay_refund_notify(request: Request):
    """微信退款回调，更新订单退款状态。"""
    raw_body = await request.body()
    body_str = raw_body.decode('utf-8')

    timestamp = request.headers.get('Wechatpay-Timestamp', '')
    nonce     = request.headers.get('Wechatpay-Nonce', '')
    signature = request.headers.get('Wechatpay-Signature', '')
    serial    = request.headers.get('Wechatpay-Serial', '')

    verified = _verify_notify_signature(timestamp, nonce, body_str, signature, serial)
    if not verified:
        return JSONResponse({'code': 'FAIL', 'message': 'signature failed'}, status_code=401)

    conn = _get_db()
    try:
        try:
            notify_data = json.loads(body_str)
        except json.JSONDecodeError:
            return JSONResponse({'code': 'FAIL', 'message': 'invalid json'}, status_code=400)

        resource = notify_data.get('resource', {})
        try:
            plaintext = _aes_gcm_decrypt(
                nonce=resource['nonce'],
                ciphertext=resource['ciphertext'],
                associated_data=resource.get('associated_data', ''),
            )
            refund_data = json.loads(plaintext)
        except Exception as exc:
            return JSONResponse({'code': 'FAIL', 'message': f'decrypt error: {exc}'}, status_code=400)

        out_trade_no   = refund_data.get('out_trade_no', '')
        wx_refund_id   = refund_data.get('refund_id', '')
        refund_status  = refund_data.get('refund_status', '')
        refund_amount  = refund_data.get('amount', {}).get('refund', 0)

        # 记录回调日志
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO wxpay_notify_logs
                   (order_no, wx_transaction_id, event_type, raw_body, headers, verified, processed)
                   VALUES (%s, %s, 'REFUND.SUCCESS', %s, '{}', TRUE, TRUE)''',
                (out_trade_no, wx_refund_id, body_str)
            )

        if refund_status == 'SUCCESS':
            with conn.cursor() as cur:
                cur.execute(
                    '''UPDATE shop_orders
                       SET status = 'refunded',
                           wx_refund_id = %s,
                           refund_amount_fen = %s,
                           refunded_at = NOW(),
                           updated_at = NOW()
                       WHERE order_no = %s AND status = 'refunding' ''',
                    (wx_refund_id, refund_amount, out_trade_no)
                )

        conn.commit()
        return JSONResponse({'code': 'SUCCESS', 'message': 'ok'})

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f'[wxpay] refund notify error: {exc}', flush=True)
        return JSONResponse({'code': 'FAIL', 'message': 'internal error'}, status_code=500)
    finally:
        _release_db(conn)


@router.get('/orders/{order_no}/query')
def query_wx_order(order_no: str, request: Request):
    """主动查询微信侧订单状态（可用于前端轮询确认支付结果）。"""
    from backend.auth import get_session_user
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT order_no, status, wx_out_trade_no FROM shop_orders WHERE order_no=%s AND user_id=%s',
                (order_no, int(user['id']))
            )
            row = cur.fetchone()
    finally:
        _release_db(conn)

    if not row:
        raise HTTPException(status_code=404, detail='订单不存在')

    db_order_no, db_status, wx_out_trade_no = row

    # 已完成的订单直接返回本地状态
    if db_status in ('fulfilled', 'cancelled', 'refunded'):
        return {'ok': True, 'order_no': order_no, 'status': db_status, 'source': 'local'}

    # 向微信查询
    if not _mch_id():
        return {'ok': True, 'order_no': order_no, 'status': db_status, 'source': 'local'}

    try:
        wx_result = query_order(wx_out_trade_no or order_no)
        return {
            'ok': True,
            'order_no': order_no,
            'status': db_status,
            'wx_trade_state': wx_result.get('trade_state'),
            'wx_trade_state_desc': wx_result.get('trade_state_desc'),
            'source': 'wxpay',
        }
    except Exception as exc:
        return {
            'ok': True,
            'order_no': order_no,
            'status': db_status,
            'source': 'local',
            'wx_query_error': str(exc),
        }


@router.post('/orders/{order_no}/refund')
def apply_refund(order_no: str, request: Request):
    """
    用户申请退款（仅 fulfilled 状态、7天内可退）。
    退款金额 = 全额退款。
    """
    from backend.auth import get_session_user
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    user_id = int(user['id'])

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, status, total_price_fen, wx_out_trade_no,
                          fulfilled_at, product_type
                   FROM shop_orders
                   WHERE order_no = %s AND user_id = %s
                   FOR UPDATE''',
                (order_no, user_id)
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail='订单不存在')

        order_id, status, total_fen, wx_out, fulfilled_at, product_type = row

        if status != 'fulfilled':
            raise HTTPException(status_code=409, detail=f'当前状态 [{status}] 不可退款')

        if fulfilled_at is None:
            raise HTTPException(status_code=409, detail='订单未履约，无法退款')

        # 7天退款窗口
        delta_seconds = (datetime.now(timezone.utc) - fulfilled_at.replace(tzinfo=timezone.utc)).total_seconds()
        if delta_seconds > 7 * 86400:
            raise HTTPException(status_code=409, detail='超过7天退款期限')

        import random, string
        refund_no = 'RF' + order_no[2:] + ''.join(random.choices(string.digits, k=4))

        # 标记订单退款中
        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE shop_orders
                   SET status = 'refunding', refund_reason = '用户申请退款',
                       refund_amount_fen = %s, updated_at = NOW()
                   WHERE id = %s''',
                (total_fen, order_id)
            )
        conn.commit()

        # 调用微信退款接口
        if _mch_id():
            try:
                refund_order(
                    out_trade_no=wx_out or order_no,
                    refund_no=refund_no,
                    refund_amount=total_fen,
                    total_amount=total_fen,
                    reason='用户申请退款',
                )
            except Exception as exc:
                # commit 已经执行过，用补偿更新而不是 rollback
                with conn.cursor() as cur:
                    cur.execute(
                        'UPDATE shop_orders SET status=%s, refund_amount_fen=0, refund_reason=%s WHERE id=%s',
                        ('fulfilled', f'微信退款失败回滚: {exc}', order_id)
                    )
                conn.commit()
                raise HTTPException(status_code=502, detail=f'微信退款申请失败: {exc}')
        else:
            # 无微信配置（开发环境），直接标记退款成功
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE shop_orders SET status=%s, refunded_at=NOW() WHERE id=%s',
                    ('refunded', order_id)
                )
            conn.commit()

        # 扣减已赠积分
        with conn.cursor() as cur:
            cur.execute(
                'SELECT credits_grant FROM shop_orders WHERE id=%s', (order_id,)
            )
            cg_row = cur.fetchone()
        credits_grant = cg_row[0] if cg_row else 0
        if credits_grant and credits_grant > 0:
            from backend.shop import _ensure_entitlement, _add_credits_ledger
            _ensure_entitlement(conn, user_id)
            _add_credits_ledger(
                conn, user_id, order_id,
                event_type='refund_deduct',
                delta=-credits_grant,
                note=f'退款订单 {order_no} 扣回 {credits_grant} 星星币'
            )
            conn.commit()

        return {'ok': True, 'order_no': order_no, 'status': 'refunding',
                'refund_no': refund_no}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f'[wxpay] apply_refund error: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='退款申请失败')
    finally:
        _release_db(conn)


# ── 内部工具 ──────────────────────────────────────────────────

def _update_notify_log(conn, log_id: int, verified: bool, processed: bool, error: str):
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE wxpay_notify_logs SET verified=%s, processed=%s, error_msg=%s WHERE id=%s',
            (verified, processed, error[:500] if error else '', log_id)
        )
