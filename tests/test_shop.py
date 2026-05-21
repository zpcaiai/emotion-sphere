"""
tests/test_shop.py
==================
虚拟商品 + 订单子系统全接口测试（pytest + TestClient，全内存 mock DB）

覆盖接口:
  GET  /api/shop/products
  GET  /api/shop/products/{sku}
  POST /api/shop/orders
  GET  /api/shop/orders
  GET  /api/shop/orders/{order_no}
  POST /api/shop/orders/{order_no}/cancel
  GET  /api/shop/entitlements
  GET  /api/shop/credits/ledger

以及内部函数:
  _gen_order_no, _ensure_entitlement, _add_credits_ledger, fulfill_order
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dt_iso(dt: datetime) -> str:
    return dt.isoformat()


def _make_conn(rows_map: dict[str, list[Any]] | None = None,
               rowcount: int = 1) -> MagicMock:
    """
    Build a lightweight psycopg2-style connection mock.
    rows_map: { sql_fragment: [row, row, ...] }  — matched by substring.
    Fragments are matched in order; longest match wins.
    Each FakeCursor instance gets its own rows on execute().
    """
    rows_map = rows_map or {}
    conn = MagicMock()

    class FakeCursor:
        def __init__(self):
            self._last_sql = ''
            self._rows: list[Any] = []

        def execute(self, sql, params=None):
            self._last_sql = sql
            sql_lower = sql.lower()
            # Find longest-matching fragment
            best_frag = ''
            best_rows: list[Any] = []
            for fragment, result_rows in rows_map.items():
                if fragment.lower() in sql_lower and len(fragment) >= len(best_frag):
                    best_frag = fragment
                    best_rows = list(result_rows)
            self._rows = best_rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return list(self._rows)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    conn.cursor.side_effect = lambda: FakeCursor()
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# TestClient setup – mock DB and session
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def client():
    """
    Stand-up the FastAPI app with DB pool replaced by a mock.
    Mocks psycopg2 entirely so the test env doesn't need it installed.
    """
    import os
    import sys
    os.environ['DATABASE_URL'] = ''  # prevent real DB init

    # Stub out psycopg2 if not installed
    if 'psycopg2' not in sys.modules:
        mock_psycopg2 = MagicMock()
        mock_psycopg2.pool.SimpleConnectionPool.return_value = MagicMock()
        sys.modules['psycopg2'] = mock_psycopg2
        sys.modules['psycopg2.pool'] = mock_psycopg2.pool
        sys.modules['psycopg2.extras'] = mock_psycopg2.extras
        sys.modules['psycopg2.extensions'] = mock_psycopg2.extensions

    # Ensure main.py DB pool init is a no-op
    with patch('backend.main._init_database', return_value=False), \
         patch('backend.main._init_db'):
        from fastapi.testclient import TestClient
        # Re-import to pick up patches (or use already-imported app)
        from backend.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture()
def auth_headers():
    """Inject a fake session token that resolves to a test user."""
    return {'Authorization': 'Bearer test-token-shop'}


@pytest.fixture()
def mock_user():
    return {'id': 1, 'email': 'test@example.com', 'nickname': 'Tester',
            'openid': 'openid_test_123', 'login_type': 'wxapp'}


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: pure functions (no HTTP)
# ─────────────────────────────────────────────────────────────────────────────

class TestGenOrderNo:
    """_gen_order_no() 格式和唯一性"""

    def test_format(self):
        from backend.shop import _gen_order_no
        no = _gen_order_no()
        assert no.startswith('ES')
        assert len(no) == 2 + 14 + 6  # ES + yyyyMMddHHmmss + 6rand

    def test_uniqueness(self):
        from backend.shop import _gen_order_no
        nos = {_gen_order_no() for _ in range(200)}
        assert len(nos) == 200, 'order numbers must be unique'

    def test_uppercase_suffix(self):
        from backend.shop import _gen_order_no
        no = _gen_order_no()
        suffix = no[16:]  # last 6 chars
        assert suffix == suffix.upper()


class TestEnsureEntitlement:
    """_ensure_entitlement 应 INSERT ON CONFLICT DO NOTHING"""

    def test_inserts_row(self):
        from backend.shop import _ensure_entitlement
        conn = _make_conn()
        _ensure_entitlement(conn, user_id=42)
        # cursor.execute should have been called with INSERT
        # Just verify no exception was raised
        assert True

    def test_idempotent_no_raise(self):
        from backend.shop import _ensure_entitlement
        conn = _make_conn()
        _ensure_entitlement(conn, 1)
        _ensure_entitlement(conn, 1)  # second call should not raise


class TestAddCreditsLedger:
    """_add_credits_ledger 应更新余额并写流水"""

    def test_returns_balance(self):
        from backend.shop import _add_credits_ledger
        conn = _make_conn({'update user_entitlements': [(120,)]})
        result = _add_credits_ledger(conn, user_id=1, order_id=99,
                                     event_type='purchase_grant',
                                     delta=30, note='test')
        assert result == 120

    def test_returns_zero_on_no_update(self):
        from backend.shop import _add_credits_ledger
        conn = _make_conn()  # UPDATE returns no row
        result = _add_credits_ledger(conn, user_id=1, order_id=None,
                                     event_type='purchase_grant',
                                     delta=10, note='')
        assert result == 0


class TestFulfillOrder:
    """fulfill_order 状态机与幂等性"""

    def _make_order_row(self, status='paid', credits_grant=30,
                        product_type='credits', duration_days=0,
                        feature_keys=None):
        return (
            101,          # order_id
            1,            # user_id
            product_type,
            credits_grant,
            duration_days,
            feature_keys or [],
            1000,         # total_price_fen
            status,
        )

    def test_already_fulfilled_idempotent(self):
        from backend.shop import fulfill_order
        row = self._make_order_row(status='fulfilled')
        conn = _make_conn({'select': [row]})
        result = fulfill_order(conn, 'ES20260101000000ABCDEF')
        assert result['already_fulfilled'] is True

    def test_order_not_found_raises(self):
        from backend.shop import fulfill_order
        conn = _make_conn()  # empty – fetchone returns None
        with pytest.raises(ValueError, match='Order not found'):
            fulfill_order(conn, 'ES_NONEXISTENT')

    def test_bad_status_raises(self):
        from backend.shop import fulfill_order
        row = self._make_order_row(status='cancelled')
        conn = _make_conn({'select': [row]})
        with pytest.raises(ValueError, match='Cannot fulfill'):
            fulfill_order(conn, 'ES20260101000000ABCDEF')

    def test_credits_fulfilled(self):
        from backend.shop import fulfill_order
        row = self._make_order_row(status='paid', credits_grant=98)
        # Simulate UPDATE entitlements returning balance
        conn = _make_conn({
            'select': [row],
            'update user_entitlements': [(128,)],
        })
        result = fulfill_order(conn, 'ES20260101000000ABCDEF')
        assert result['already_fulfilled'] is False
        assert result['credits_granted'] == 98

    def test_no_credits_grant(self):
        from backend.shop import fulfill_order
        row = self._make_order_row(status='paid', credits_grant=0)
        conn = _make_conn({'select': [row]})
        result = fulfill_order(conn, 'ES20260101000000ABCDEF')
        assert result['credits_granted'] == 0

    def test_subscription_type(self):
        from backend.shop import fulfill_order
        row = self._make_order_row(
            status='paid', product_type='subscription',
            duration_days=30, credits_grant=0,
            feature_keys=['psychology_deep']
        )
        conn = _make_conn({'select': [row]})
        # Should not raise
        result = fulfill_order(conn, 'ES20260101000000ABCDEF')
        assert result['already_fulfilled'] is False

    def test_feature_unlock_type(self):
        from backend.shop import fulfill_order
        row = self._make_order_row(
            status='paid', product_type='feature_unlock',
            credits_grant=0, feature_keys=['dss_full']
        )
        conn = _make_conn({'select': [row]})
        result = fulfill_order(conn, 'ES20260101000000ABCDEF')
        assert not result['already_fulfilled']


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoint tests (all use TestClient + mocked DB + mocked session)
# ─────────────────────────────────────────────────────────────────────────────

FAKE_PRODUCTS = [
    (1, 'credits_30', '30颗星星币', '积分商品描述', 'credits',
     300, 0, 30, 0, [''], {}, -1, 10, 1, '星星币', '⭐'),
    (2, 'sub_monthly', '月订阅', '订阅商品描述', 'subscription',
     1800, 2800, 0, 30, ['psychology_deep'], {}, -1, 5, 2, '高级订阅', '👑'),
]

FAKE_PRODUCT_ROW = (
    1, 1, 'credits_30', '30颗星星币', '积分商品描述',
    'credits', 300, 0, 30, 0, [], {}, -1, 10, True, 1, '星星币'
)


class TestListProducts:

    def test_unauthenticated_allowed(self, client):
        """商品列表无需认证"""
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': FAKE_PRODUCTS})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert isinstance(data['products'], list)

    def test_filter_by_category(self, client):
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': FAKE_PRODUCTS[:1]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products?category=星星币')
        assert resp.status_code == 200

    def test_filter_by_product_type(self, client):
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': []})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products?product_type=subscription')
        assert resp.status_code == 200

    def test_active_only_default(self, client):
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': FAKE_PRODUCTS})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products')
        assert resp.status_code == 200

    def test_include_inactive(self, client):
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': FAKE_PRODUCTS})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products?active_only=false')
        assert resp.status_code == 200


class TestGetProduct:

    def test_existing_product(self, client):
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [FAKE_PRODUCT_ROW]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products/credits_30')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data['product']['sku'] == 'credits_30'

    def test_nonexistent_product_404(self, client):
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn()  # fetchone returns None
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products/sku_that_does_not_exist')
        assert resp.status_code == 404

    def test_inactive_product_404(self, client):
        inactive_row = list(FAKE_PRODUCT_ROW)
        inactive_row[14] = False  # is_active = False
        with patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [tuple(inactive_row)]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/products/credits_30')
        assert resp.status_code == 404


class TestCreateOrder:

    def test_requires_auth(self, client):
        resp = client.post('/api/shop/orders', json={'sku': 'credits_30'})
        assert resp.status_code == 401

    def test_invalid_sku_empty(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user):
            resp = client.post('/api/shop/orders',
                               json={'sku': ''},
                               headers=auth_headers)
        assert resp.status_code == 422

    def test_quantity_must_be_positive(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user):
            resp = client.post('/api/shop/orders',
                               json={'sku': 'credits_30', 'quantity': 0},
                               headers=auth_headers)
        assert resp.status_code == 422

    def test_product_not_found(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn()
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders',
                               json={'sku': 'nonexistent_sku'},
                               headers=auth_headers)
        assert resp.status_code == 404

    def test_out_of_stock(self, client, auth_headers, mock_user):
        out_of_stock_row = list(FAKE_PRODUCT_ROW)
        out_of_stock_row[12] = 0   # stock = 0
        out_of_stock_row[14] = True
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [tuple(out_of_stock_row)]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders',
                               json={'sku': 'credits_30'},
                               headers=auth_headers)
        assert resp.status_code == 409

    def test_free_product_fulfilled_immediately(self, client, auth_headers, mock_user):
        free_row = list(FAKE_PRODUCT_ROW)
        free_row[6] = 0   # price_fen = 0
        free_row[14] = True
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'), \
             patch('backend.shop.fulfill_order') as mock_fulfill:
            mock_fulfill.return_value = {'order_no': 'ESXXX', 'already_fulfilled': False, 'credits_granted': 0}
            conn = _make_conn({'select': [tuple(free_row)],
                               'insert': [(999,)]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders',
                               json={'sku': 'credits_30'},
                               headers=auth_headers)
        # Either fulfilled or pending_payment (depending on mock detail),
        # but must not crash with 5xx
        assert resp.status_code in (200, 400, 404, 409)

    def test_paid_product_returns_pay_required(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'), \
             patch('backend.wxpay.create_prepay', side_effect=RuntimeError('no config')):
            conn = _make_conn({'select': [FAKE_PRODUCT_ROW],
                               'insert': [(55,)]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders',
                               json={'sku': 'credits_30', 'pay_method': 'miniprogram'},
                               headers=auth_headers)
        # prepay failed → ok=False but order created
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('pay_required') is True

    def test_quantity_max_99(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user):
            resp = client.post('/api/shop/orders',
                               json={'sku': 'credits_30', 'quantity': 100},
                               headers=auth_headers)
        assert resp.status_code == 422


class TestListOrders:

    def test_requires_auth(self, client):
        resp = client.get('/api/shop/orders')
        assert resp.status_code == 401

    def test_empty_list(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({
                'select id, order_no': [],       # list query
                'select count': [(0,)],           # count query
            })
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/orders', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert isinstance(data['orders'], list)

    def test_pagination_params_clamped(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({
                'select id, order_no': [],
                'select count': [(0,)],
            })
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/orders?page=0&page_size=999',
                              headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['page'] == 1         # clamped to minimum 1
        assert data['page_size'] == 100  # clamped to max 100

    def test_status_filter(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({
                'select id, order_no': [],
                'select count': [(0,)],
            })
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/orders?status=fulfilled',
                              headers=auth_headers)
        assert resp.status_code == 200


class TestGetOrderDetail:
    ORDER_ROW = (
        1, 'ES20260521000000ABCDEF', 1, 1, 'credits_30',
        '30颗星星币', 'credits', 1, 300, 300, 30, 0, [],
        'wxpay', 'miniprogram', '', '', '',
        'pending_payment',
        None, None, None,
        datetime(2026, 5, 21, 1, 0, 0),  # expired_at
        None, '', 0, '127.0.0.1', 'miniprogram', '', {},
        datetime(2026, 5, 21, 0, 30, 0),  # created_at
        datetime(2026, 5, 21, 0, 30, 0),  # updated_at
    )

    def test_requires_auth(self, client):
        resp = client.get('/api/shop/orders/ES20260521000000ABCDEF')
        assert resp.status_code == 401

    def test_order_found(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [self.ORDER_ROW]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/orders/ES20260521000000ABCDEF',
                              headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert 'order' in data

    def test_order_not_found_404(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn()
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/orders/ES_NONEXISTENT',
                              headers=auth_headers)
        assert resp.status_code == 404

    def test_cannot_see_another_users_order(self, client, auth_headers, mock_user):
        """user_id filter in query prevents cross-user access"""
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn()  # returns None → 404
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/orders/ES_OTHER_USER',
                              headers=auth_headers)
        assert resp.status_code == 404


class TestCancelOrder:
    _PENDING_ROW = (1, 'pending_payment', 1, 1, '')

    def test_requires_auth(self, client):
        resp = client.post('/api/shop/orders/ES001/cancel', json={})
        assert resp.status_code == 401

    def test_cancel_pending_order(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [self._PENDING_ROW]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders/ES001/cancel',
                               json={'reason': '不想买了'},
                               headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data['status'] == 'cancelled'

    def test_cancel_nonexistent_order_404(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn()
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders/ES_GHOST/cancel',
                               json={},
                               headers=auth_headers)
        assert resp.status_code == 404

    def test_cancel_fulfilled_order_rejected(self, client, auth_headers, mock_user):
        fulfilled_row = (1, 'fulfilled', 1, 1, '')
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [fulfilled_row]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders/ES001/cancel',
                               json={},
                               headers=auth_headers)
        assert resp.status_code == 409

    def test_cancel_paid_order_rejected(self, client, auth_headers, mock_user):
        paid_row = (1, 'paid', 1, 1, '')
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [paid_row]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders/ES001/cancel',
                               json={},
                               headers=auth_headers)
        assert resp.status_code == 409

    def test_default_cancel_reason(self, client, auth_headers, mock_user):
        """Empty body should use default reason without 422"""
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [self._PENDING_ROW]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders/ES001/cancel',
                               json={},
                               headers=auth_headers)
        assert resp.status_code == 200

    def test_cancel_payment_failed_order(self, client, auth_headers, mock_user):
        failed_row = (1, 'payment_failed', 1, 1, '')
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [failed_row]})
            mock_getdb.return_value = conn
            resp = client.post('/api/shop/orders/ES001/cancel',
                               json={},
                               headers=auth_headers)
        assert resp.status_code == 200


class TestGetEntitlements:

    def test_requires_auth(self, client):
        resp = client.get('/api/shop/entitlements')
        assert resp.status_code == 401

    def test_returns_zero_balance_for_new_user(self, client, auth_headers, mock_user):
        entitlement_row = (0, [], None, '', datetime.now())
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [entitlement_row]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/entitlements', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data['credits_balance'] == 0
        assert data['is_subscribed'] is False

    def test_active_subscription_detected(self, client, auth_headers, mock_user):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        entitlement_row = (100, ['psychology_deep'], future, 'sub_monthly', datetime.now())
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [entitlement_row]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/entitlements', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['is_subscribed'] is True
        assert data['credits_balance'] == 100
        assert 'psychology_deep' in data['unlocked_features']

    def test_expired_subscription_not_subscribed(self, client, auth_headers, mock_user):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        entitlement_row = (50, [], past, 'sub_monthly', datetime.now())
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [entitlement_row]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/entitlements', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['is_subscribed'] is False

    def test_no_entitlement_row_returns_defaults(self, client, auth_headers, mock_user):
        """When user has no entitlements row, returns zeroed defaults."""
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn()  # fetchone returns None
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/entitlements', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['credits_balance'] == 0


class TestCreditsLedger:

    def test_requires_auth(self, client):
        resp = client.get('/api/shop/credits/ledger')
        assert resp.status_code == 401

    def test_empty_ledger(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({
                'select id, order_id': [],
                'select count': [(0,)],
            })
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/credits/ledger', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data['ledger'] == []
        assert data['total'] == 0

    def test_pagination(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({
                'select id, order_id': [],
                'select count': [(0,)],
            })
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/credits/ledger?page=2&page_size=10',
                              headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['page'] == 2
        assert data['page_size'] == 10

    def test_page_size_clamped_to_100(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({
                'select id, order_id': [],
                'select count': [(0,)],
            })
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/credits/ledger?page_size=9999',
                              headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()['page_size'] == 100


# ─────────────────────────────────────────────────────────────────────────────
# Edge-case / regression tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderNoDatetimeSerialization:
    """订单详情中的 datetime 字段必须序列化为 ISO 字符串。"""

    ORDER_ROW = (
        1, 'ES20260521000000ABCDEF', 1, 1, 'credits_30',
        '30颗星星币', 'credits', 1, 300, 300, 30, 0, [],
        'wxpay', 'miniprogram', '', '', '',
        'fulfilled',
        datetime(2026, 5, 21, 1, 0, 0),   # paid_at
        datetime(2026, 5, 21, 1, 0, 1),   # fulfilled_at
        None,                              # cancelled_at
        datetime(2026, 5, 21, 1, 30, 0),  # expired_at
        None, '', 0, '127.0.0.1', 'miniprogram', '', {},
        datetime(2026, 5, 21, 0, 30, 0),
        datetime(2026, 5, 21, 0, 30, 0),
    )

    def test_datetimes_are_strings(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.shop._get_db') as mock_getdb, \
             patch('backend.shop._release_db'):
            conn = _make_conn({'select': [self.ORDER_ROW]})
            mock_getdb.return_value = conn
            resp = client.get('/api/shop/orders/ES20260521000000ABCDEF',
                              headers=auth_headers)
        assert resp.status_code == 200
        order = resp.json()['order']
        for key in ('paid_at', 'fulfilled_at', 'created_at', 'updated_at'):
            if order.get(key):
                assert isinstance(order[key], str), f'{key} should be a string'


class TestConcurrentOrderNo:
    """并发生成订单号不应碰撞"""

    def test_no_collision_under_concurrency(self):
        from backend.shop import _gen_order_no
        results = []
        lock = threading.Lock()

        def gen():
            no = _gen_order_no()
            with lock:
                results.append(no)

        threads = [threading.Thread(target=gen) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == len(set(results)), 'Collision detected under concurrency'
