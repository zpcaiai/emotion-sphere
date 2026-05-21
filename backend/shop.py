"""
shop.py — 情感星球虚拟商品 + 订单子系统

提供:
  GET  /api/shop/products               商品列表（分类可筛选）
  GET  /api/shop/products/{sku}         商品详情
  POST /api/shop/orders                 创建订单（发起支付）
  GET  /api/shop/orders                 用户订单列表
  GET  /api/shop/orders/{order_no}      订单详情
  POST /api/shop/orders/{order_no}/cancel  取消待付款订单
  GET  /api/shop/entitlements           用户当前权益/积分
  GET  /api/shop/credits/ledger         积分流水

内部辅助函数（供 wxpay.py 回调使用）:
  fulfill_order(conn, order_no) -> dict
"""

from __future__ import annotations

import json
import os
import random
import string
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator

# ── 依赖注入（由 main.py 注入）────────────────────────────────

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


# ── 工具函数 ──────────────────────────────────────────────────

def _now_ts() -> datetime:
    return datetime.now(timezone.utc)


def _gen_order_no() -> str:
    """生成业务订单号: ES{yyyyMMddHHmmss}{6位大写随机}"""
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'ES{ts}{rand}'


def _require_user(request: Request) -> dict:
    from backend.auth import get_session_user
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='请先登录')
    return user


# ── Pydantic 模型 ─────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1, le=99)
    pay_method: str = Field(default='miniprogram')   # jsapi / miniprogram / native / h5
    platform: str = Field(default='miniprogram')     # web / miniprogram / h5
    remark: str = Field(default='', max_length=200)


class CancelOrderRequest(BaseModel):
    reason: str = Field(default='用户主动取消', max_length=200)


# ── 数据库辅助 ────────────────────────────────────────────────

def _get_product_by_sku(conn, sku: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            '''SELECT p.id, p.category_id, p.sku, p.name, p.description,
                      p.product_type, p.price_fen, p.original_price_fen,
                      p.credits_grant, p.duration_days, p.feature_keys,
                      p.metadata, p.stock, p.sold_count, p.is_active,
                      p.sort_order, c.name AS category_name
               FROM shop_products p
               LEFT JOIN shop_categories c ON c.id = p.category_id
               WHERE p.sku = %s''',
            (sku,)
        )
        row = cur.fetchone()
    if not row:
        return None
    cols = ['id', 'category_id', 'sku', 'name', 'description', 'product_type',
            'price_fen', 'original_price_fen', 'credits_grant', 'duration_days',
            'feature_keys', 'metadata', 'stock', 'sold_count', 'is_active',
            'sort_order', 'category_name']
    return dict(zip(cols, row))


def _get_order_by_no(conn, order_no: str, user_id: int | None = None) -> dict | None:
    with conn.cursor() as cur:
        if user_id is not None:
            cur.execute(
                '''SELECT id, order_no, user_id, product_id, product_sku,
                          product_name, product_type, quantity, unit_price_fen,
                          total_price_fen, credits_grant, duration_days, feature_keys,
                          pay_channel, pay_method, wx_prepay_id, wx_transaction_id,
                          wx_out_trade_no, status, paid_at, fulfilled_at,
                          cancelled_at, expired_at, refunded_at, refund_reason,
                          refund_amount_fen, client_ip, platform, remark, extra,
                          created_at, updated_at
                   FROM shop_orders
                   WHERE order_no = %s AND user_id = %s''',
                (order_no, user_id)
            )
        else:
            cur.execute(
                '''SELECT id, order_no, user_id, product_id, product_sku,
                          product_name, product_type, quantity, unit_price_fen,
                          total_price_fen, credits_grant, duration_days, feature_keys,
                          pay_channel, pay_method, wx_prepay_id, wx_transaction_id,
                          wx_out_trade_no, status, paid_at, fulfilled_at,
                          cancelled_at, expired_at, refunded_at, refund_reason,
                          refund_amount_fen, client_ip, platform, remark, extra,
                          created_at, updated_at
                   FROM shop_orders WHERE order_no = %s''',
                (order_no,)
            )
        row = cur.fetchone()
    if not row:
        return None
    cols = ['id', 'order_no', 'user_id', 'product_id', 'product_sku',
            'product_name', 'product_type', 'quantity', 'unit_price_fen',
            'total_price_fen', 'credits_grant', 'duration_days', 'feature_keys',
            'pay_channel', 'pay_method', 'wx_prepay_id', 'wx_transaction_id',
            'wx_out_trade_no', 'status', 'paid_at', 'fulfilled_at',
            'cancelled_at', 'expired_at', 'refunded_at', 'refund_reason',
            'refund_amount_fen', 'client_ip', 'platform', 'remark', 'extra',
            'created_at', 'updated_at']
    d = dict(zip(cols, row))
    # 序列化 datetime
    for k in ('paid_at', 'fulfilled_at', 'cancelled_at', 'expired_at',
              'refunded_at', 'created_at', 'updated_at'):
        if d[k] is not None:
            d[k] = d[k].isoformat()
    return d


def _ensure_entitlement(conn, user_id: int):
    """确保用户权益行存在（幂等）。"""
    with conn.cursor() as cur:
        cur.execute(
            '''INSERT INTO user_entitlements (user_id, credits_balance)
               VALUES (%s, 0)
               ON CONFLICT (user_id) DO NOTHING''',
            (user_id,)
        )


def _add_credits_ledger(conn, user_id: int, order_id: int | None,
                        event_type: str, delta: int, note: str) -> int:
    """
    记一笔积分流水，同时更新 user_entitlements.credits_balance。
    返回最新余额。
    """
    with conn.cursor() as cur:
        cur.execute(
            '''UPDATE user_entitlements
               SET credits_balance = credits_balance + %s,
                   updated_at = NOW()
               WHERE user_id = %s
               RETURNING credits_balance''',
            (delta, user_id)
        )
        row = cur.fetchone()
        balance_after = row[0] if row else 0
        cur.execute(
            '''INSERT INTO credits_ledger (user_id, order_id, event_type, delta, balance_after, note)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (user_id, order_id, event_type, delta, balance_after, note)
        )
    return balance_after


# ── 订单履约（核心：支付成功后调用）──────────────────────────

def fulfill_order(conn, order_no: str) -> dict:
    """
    将订单状态推进到 fulfilled，并发放权益/积分。
    幂等：若已 fulfilled 则直接返回。
    由 wxpay.py 回调处理器调用（在同一事务内）。
    """
    with conn.cursor() as cur:
        cur.execute(
            '''SELECT id, user_id, product_type, credits_grant, duration_days,
                      feature_keys, total_price_fen, status
               FROM shop_orders WHERE order_no = %s FOR UPDATE''',
            (order_no,)
        )
        row = cur.fetchone()

    if not row:
        raise ValueError(f'Order not found: {order_no}')

    (order_id, user_id, product_type, credits_grant,
     duration_days, feature_keys, total_price_fen, status) = row

    if status == 'fulfilled':
        return {'order_no': order_no, 'already_fulfilled': True}

    if status not in ('paid', 'pending_payment'):
        raise ValueError(f'Cannot fulfill order in status={status}: {order_no}')

    now = _now_ts()

    # ── 更新订单状态 ──────────────────────────────────────────
    with conn.cursor() as cur:
        cur.execute(
            '''UPDATE shop_orders
               SET status = 'fulfilled', fulfilled_at = %s, updated_at = %s
               WHERE id = %s''',
            (now, now, order_id)
        )

    # ── 确保权益行存在 ────────────────────────────────────────
    _ensure_entitlement(conn, user_id)

    # ── 赠送积分 ──────────────────────────────────────────────
    if credits_grant and credits_grant > 0:
        _add_credits_ledger(
            conn, user_id, order_id,
            event_type='purchase_grant',
            delta=credits_grant,
            note=f'购买订单 {order_no} 赠送 {credits_grant} 星星币'
        )

    # ── 更新订阅/功能解锁 ─────────────────────────────────────
    if product_type in ('subscription', 'feature_unlock'):
        with conn.cursor() as cur:
            if product_type == 'subscription' and duration_days > 0:
                cur.execute(
                    '''UPDATE user_entitlements
                       SET subscription_expires_at =
                             GREATEST(
                               COALESCE(subscription_expires_at, NOW()),
                               NOW()
                             ) + (%s || ' days')::INTERVAL,
                           subscription_plan = (
                               SELECT product_sku FROM shop_orders WHERE id = %s
                           ),
                           updated_at = NOW()
                       WHERE user_id = %s''',
                    (str(duration_days), order_id, user_id)
                )
            if feature_keys:
                cur.execute(
                    '''UPDATE user_entitlements
                       SET unlocked_features = (
                           SELECT jsonb_agg(DISTINCT elem)
                           FROM (
                               SELECT jsonb_array_elements_text(
                                   COALESCE(unlocked_features, '[]'::jsonb)
                               ) AS elem
                               UNION
                               SELECT unnest(%s::text[])
                           ) t
                       ),
                       updated_at = NOW()
                       WHERE user_id = %s''',
                    (feature_keys, user_id)
                )

    # ── 商品销量计数 ──────────────────────────────────────────
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE shop_products SET sold_count = sold_count + 1 WHERE id = ('
            '  SELECT product_id FROM shop_orders WHERE id = %s'
            ')',
            (order_id,)
        )

    print(f'[shop] order fulfilled: {order_no} user={user_id} type={product_type}',
          flush=True)
    return {
        'order_no': order_no,
        'already_fulfilled': False,
        'credits_granted': credits_grant or 0,
    }


# ── FastAPI 路由 ──────────────────────────────────────────────

router = APIRouter(prefix='/api/shop', tags=['shop'])


@router.get('/products')
def list_products(
    category: Optional[str] = None,
    product_type: Optional[str] = None,
    active_only: bool = True,
):
    """商品列表，支持按分类/类型筛选。"""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            where_clauses = []
            params: list = []
            if active_only:
                where_clauses.append('p.is_active = TRUE')
            if category:
                where_clauses.append('c.name = %s')
                params.append(category)
            if product_type:
                where_clauses.append('p.product_type = %s')
                params.append(product_type)
            where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
            cur.execute(
                f'''SELECT p.id, p.sku, p.name, p.description, p.product_type,
                           p.price_fen, p.original_price_fen, p.credits_grant,
                           p.duration_days, p.feature_keys, p.metadata,
                           p.stock, p.sold_count, p.sort_order,
                           c.name AS category_name, c.icon AS category_icon
                    FROM shop_products p
                    LEFT JOIN shop_categories c ON c.id = p.category_id
                    {where_sql}
                    ORDER BY p.sort_order ASC, p.id ASC''',
                params
            )
            rows = cur.fetchall()
        cols = ['id', 'sku', 'name', 'description', 'product_type',
                'price_fen', 'original_price_fen', 'credits_grant',
                'duration_days', 'feature_keys', 'metadata',
                'stock', 'sold_count', 'sort_order',
                'category_name', 'category_icon']
        products = [dict(zip(cols, r)) for r in rows]
        return {'ok': True, 'products': products}
    finally:
        _release_db(conn)


@router.get('/products/{sku}')
def get_product(sku: str):
    """商品详情。"""
    conn = _get_db()
    try:
        product = _get_product_by_sku(conn, sku)
        if not product or not product['is_active']:
            raise HTTPException(status_code=404, detail='商品不存在或已下架')
        return {'ok': True, 'product': product}
    finally:
        _release_db(conn)


@router.post('/orders')
def create_order(request: Request, payload: CreateOrderRequest):
    """
    创建订单。
    对于非零价商品，返回 wx_prepay_id / code_url 供前端调起支付。
    对于零价商品（price_fen=0），直接 fulfill。
    """
    user = _require_user(request)
    user_id = int(user['id'])
    client_ip = request.client.host if request.client else ''

    conn = _get_db()
    try:
        product = _get_product_by_sku(conn, payload.sku)
        if not product or not product['is_active']:
            raise HTTPException(status_code=404, detail='商品不存在或已下架')

        # 库存检查（-1=不限）
        if product['stock'] != -1 and product['stock'] <= 0:
            raise HTTPException(status_code=409, detail='商品库存不足')

        total_fen = product['price_fen'] * payload.quantity
        order_no = _gen_order_no()
        wx_out_trade_no = order_no  # 微信商户订单号直接复用

        # ── 扣减库存（乐观锁）────────────────────────────────
        if product['stock'] != -1:
            with conn.cursor() as cur:
                cur.execute(
                    '''UPDATE shop_products
                       SET stock = stock - %s
                       WHERE id = %s AND stock >= %s
                       RETURNING stock''',
                    (payload.quantity, product['id'], payload.quantity)
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=409, detail='商品库存不足（并发）')

        # ── 插入订单 ──────────────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                '''INSERT INTO shop_orders (
                       order_no, user_id, product_id, product_sku, product_name,
                       product_type, quantity, unit_price_fen, total_price_fen,
                       credits_grant, duration_days, feature_keys,
                       pay_method, wx_out_trade_no,
                       status, expired_at, client_ip, platform, remark
                   ) VALUES (
                       %s, %s, %s, %s, %s,
                       %s, %s, %s, %s,
                       %s, %s, %s,
                       %s, %s,
                       %s, NOW() + INTERVAL '30 minutes', %s, %s, %s
                   ) RETURNING id''',
                (
                    order_no, user_id, product['id'], product['sku'], product['name'],
                    product['product_type'], payload.quantity,
                    product['price_fen'], total_fen,
                    product['credits_grant'], product['duration_days'],
                    product['feature_keys'] or [],
                    payload.pay_method, wx_out_trade_no,
                    'pending_payment', client_ip, payload.platform, payload.remark
                )
            )
            order_id = cur.fetchone()[0]
        conn.commit()

        # ── 零价商品直接履约 ──────────────────────────────────
        if total_fen == 0:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE shop_orders SET status=%s, paid_at=NOW() WHERE id=%s',
                    ('paid', order_id)
                )
            conn.commit()
            fulfill_result = fulfill_order(conn, order_no)
            conn.commit()
            return {
                'ok': True,
                'order_no': order_no,
                'status': 'fulfilled',
                'pay_required': False,
                'fulfill': fulfill_result,
            }

        # ── 非零价：发起微信支付预下单 ──────────────────────────
        from backend.wxpay import create_prepay
        try:
            prepay_result = create_prepay(
                out_trade_no=wx_out_trade_no,
                total_fee=total_fen,
                description=product['name'],
                pay_method=payload.pay_method,
                openid=user.get('openid', ''),
                client_ip=client_ip,
            )
        except Exception as exc:
            print(f'[shop] wxpay create_prepay failed: {exc}', flush=True)
            # 订单保持 pending_payment，前端可重试
            return {
                'ok': False,
                'order_no': order_no,
                'status': 'pending_payment',
                'error': str(exc),
                'pay_required': True,
            }

        # 保存 prepay_id
        wx_prepay_id = prepay_result.get('prepay_id', '')
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE shop_orders SET wx_prepay_id=%s, updated_at=NOW() WHERE id=%s',
                (wx_prepay_id, order_id)
            )
        conn.commit()

        return {
            'ok': True,
            'order_no': order_no,
            'status': 'pending_payment',
            'pay_required': True,
            'pay_params': prepay_result,
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f'[shop] create_order error: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='创建订单失败，请稍后重试')
    finally:
        _release_db(conn)


@router.get('/orders')
def list_orders(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """用户订单列表，按创建时间倒序。"""
    user = _require_user(request)
    user_id = int(user['id'])
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            params: list = [user_id]
            status_filter = ''
            if status:
                status_filter = 'AND status = %s'
                params.append(status)
            cur.execute(
                f'''SELECT id, order_no, product_sku, product_name, product_type,
                           quantity, unit_price_fen, total_price_fen, credits_grant,
                           pay_method, wx_transaction_id, status,
                           paid_at, fulfilled_at, cancelled_at, expired_at,
                           platform, remark, created_at
                    FROM shop_orders
                    WHERE user_id = %s {status_filter}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s''',
                params + [page_size, offset]
            )
            rows = cur.fetchall()
            cur.execute(
                f'SELECT COUNT(*) FROM shop_orders WHERE user_id = %s {status_filter}',
                [user_id] + ([status] if status else [])
            )
            total = cur.fetchone()[0]

        cols = ['id', 'order_no', 'product_sku', 'product_name', 'product_type',
                'quantity', 'unit_price_fen', 'total_price_fen', 'credits_grant',
                'pay_method', 'wx_transaction_id', 'status',
                'paid_at', 'fulfilled_at', 'cancelled_at', 'expired_at',
                'platform', 'remark', 'created_at']
        orders = []
        for r in rows:
            d = dict(zip(cols, r))
            for k in ('paid_at', 'fulfilled_at', 'cancelled_at', 'expired_at', 'created_at'):
                if d[k] is not None:
                    d[k] = d[k].isoformat()
            orders.append(d)

        return {
            'ok': True,
            'orders': orders,
            'total': total,
            'page': page,
            'page_size': page_size,
        }
    finally:
        _release_db(conn)


@router.get('/orders/{order_no}')
def get_order(order_no: str, request: Request):
    """订单详情。"""
    user = _require_user(request)
    conn = _get_db()
    try:
        order = _get_order_by_no(conn, order_no, user_id=int(user['id']))
        if not order:
            raise HTTPException(status_code=404, detail='订单不存在')
        return {'ok': True, 'order': order}
    finally:
        _release_db(conn)


@router.post('/orders/{order_no}/cancel')
def cancel_order(order_no: str, request: Request, payload: CancelOrderRequest):
    """取消待付款订单（已支付订单走退款流程）。"""
    user = _require_user(request)
    user_id = int(user['id'])

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, status, product_id, quantity, wx_prepay_id
                   FROM shop_orders
                   WHERE order_no = %s AND user_id = %s
                   FOR UPDATE''',
                (order_no, user_id)
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail='订单不存在')

        order_id, status, product_id, quantity, wx_prepay_id = row

        if status not in ('pending_payment', 'payment_failed'):
            raise HTTPException(
                status_code=409,
                detail=f'当前订单状态 [{status}] 不可取消，已支付请申请退款'
            )

        with conn.cursor() as cur:
            cur.execute(
                '''UPDATE shop_orders
                   SET status = 'cancelled', cancelled_at = NOW(),
                       refund_reason = %s, updated_at = NOW()
                   WHERE id = %s''',
                (payload.reason, order_id)
            )
            # 回滚库存
            cur.execute(
                '''UPDATE shop_products
                   SET stock = CASE WHEN stock = -1 THEN -1 ELSE stock + %s END
                   WHERE id = %s''',
                (quantity, product_id)
            )
        conn.commit()

        return {'ok': True, 'order_no': order_no, 'status': 'cancelled'}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        print(f'[shop] cancel_order error: {exc}', flush=True)
        raise HTTPException(status_code=500, detail='取消订单失败')
    finally:
        _release_db(conn)


@router.get('/entitlements')
def get_entitlements(request: Request):
    """获取当前用户权益、积分余额、订阅信息。"""
    user = _require_user(request)
    user_id = int(user['id'])

    conn = _get_db()
    try:
        _ensure_entitlement(conn, user_id)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT credits_balance, unlocked_features,
                          subscription_expires_at, subscription_plan, updated_at
                   FROM user_entitlements WHERE user_id = %s''',
                (user_id,)
            )
            row = cur.fetchone()
        if not row:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO user_entitlements (user_id) VALUES (%s) ON CONFLICT DO NOTHING',
                    (user_id,)
                )
            conn.commit()
            return {
                'ok': True,
                'credits_balance': 0,
                'unlocked_features': [],
                'subscription_expires_at': None,
                'subscription_plan': '',
                'is_subscribed': False,
            }

        credits_balance, unlocked_features, sub_expires, sub_plan, updated_at = row
        is_subscribed = (
            sub_expires is not None and
            sub_expires.replace(tzinfo=timezone.utc) > _now_ts()
        )
        return {
            'ok': True,
            'credits_balance': credits_balance,
            'unlocked_features': unlocked_features or [],
            'subscription_expires_at': sub_expires.isoformat() if sub_expires else None,
            'subscription_plan': sub_plan or '',
            'is_subscribed': is_subscribed,
        }
    finally:
        _release_db(conn)


@router.get('/credits/ledger')
def get_credits_ledger(
    request: Request,
    page: int = 1,
    page_size: int = 30,
):
    """用户积分流水。"""
    user = _require_user(request)
    user_id = int(user['id'])
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT id, order_id, event_type, delta, balance_after, note, created_at
                   FROM credits_ledger
                   WHERE user_id = %s
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s''',
                (user_id, page_size, offset)
            )
            rows = cur.fetchall()
            cur.execute(
                'SELECT COUNT(*) FROM credits_ledger WHERE user_id = %s', (user_id,)
            )
            total = cur.fetchone()[0]

        cols = ['id', 'order_id', 'event_type', 'delta', 'balance_after', 'note', 'created_at']
        ledger = []
        for r in rows:
            d = dict(zip(cols, r))
            if d['created_at']:
                d['created_at'] = d['created_at'].isoformat()
            ledger.append(d)

        return {'ok': True, 'ledger': ledger, 'total': total,
                'page': page, 'page_size': page_size}
    finally:
        _release_db(conn)


# ── DB 初始化（在 main.py lifespan 中调用）──────────────────

def init_shop_tables(conn):
    """从 shop_schema.sql 文件执行建表语句（幂等）。"""
    import pathlib
    schema_path = pathlib.Path(__file__).parent / 'shop_schema.sql'
    sql = schema_path.read_text(encoding='utf-8')
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print('[shop] shop tables initialized', flush=True)
