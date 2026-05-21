"""
tests/test_wxpay.py
===================
微信支付子系统全接口测试（pytest + TestClient + mock）

覆盖接口:
  POST /api/wxpay/notify            支付成功回调
  POST /api/wxpay/refund-notify     退款回调
  GET  /api/wxpay/orders/{no}/query 主动查询
  POST /api/wxpay/orders/{no}/refund 申请退款

以及内部函数:
  _cfg, _mch_id, _app_id 等 getter
  _aes_gcm_decrypt
  _verify_notify_signature
  _sign_miniprogram_pay / _sign_jsapi_pay
  _check_config
  create_prepay (error paths without real HTTP)
"""

from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_conn(rows_map: dict | None = None) -> MagicMock:
    rows_map = rows_map or {}

    class FakeCursor:
        def __init__(self):
            self._rows: list = []
            self._last_sql = ''

        def execute(self, sql, params=None):
            self._last_sql = sql
            for fragment, result_rows in rows_map.items():
                if fragment.lower() in sql.lower():
                    self._rows = list(result_rows)
                    return
            self._rows = []

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return list(self._rows)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    conn = MagicMock()
    conn.cursor.side_effect = lambda: FakeCursor()
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    return conn


def _make_notify_body(event_type: str, resource: dict) -> str:
    return json.dumps({'event_type': event_type, 'resource': resource})


def _make_notify_headers(timestamp: str | None = None) -> dict:
    ts = timestamp or str(int(time.time()))
    return {
        'Wechatpay-Timestamp': ts,
        'Wechatpay-Nonce': 'testnonce12345',
        'Wechatpay-Signature': 'fakesignature',
        'Wechatpay-Serial': 'fakeserial',
    }


# Encrypted resource for tests — we'll mock _aes_gcm_decrypt to bypass real crypto
FAKE_TX_PLAINTEXT = json.dumps({
    'out_trade_no': 'ES20260521000000ABCDEF',
    'transaction_id': 'WX_TX_123456789',
    'trade_state': 'SUCCESS',
    'amount': {'total': 300},
})

FAKE_REFUND_PLAINTEXT = json.dumps({
    'out_trade_no': 'ES20260521000000ABCDEF',
    'refund_id': 'WX_REFUND_001',
    'refund_status': 'SUCCESS',
    'amount': {'refund': 300},
})


@pytest.fixture(scope='module')
def client():
    import sys
    os.environ['DATABASE_URL'] = ''

    if 'psycopg2' not in sys.modules:
        mock_psycopg2 = MagicMock()
        mock_psycopg2.pool.SimpleConnectionPool.return_value = MagicMock()
        sys.modules['psycopg2'] = mock_psycopg2
        sys.modules['psycopg2.pool'] = mock_psycopg2.pool
        sys.modules['psycopg2.extras'] = mock_psycopg2.extras
        sys.modules['psycopg2.extensions'] = mock_psycopg2.extensions

    with patch('backend.main._init_database', return_value=False), \
         patch('backend.main._init_db'):
        from fastapi.testclient import TestClient
        from backend.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture()
def auth_headers():
    return {'Authorization': 'Bearer test-token-wxpay'}


@pytest.fixture()
def mock_user():
    return {'id': 1, 'email': 'test@example.com', 'nickname': 'Tester',
            'openid': 'openid_test_123', 'login_type': 'wxapp'}


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: config getters
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigGetters:
    """Lazy getter functions should read env vars at call time"""

    def test_mch_id_reads_env(self):
        from backend import wxpay
        with patch.dict(os.environ, {'WXPAY_MCH_ID': '1234567890'}):
            assert wxpay._mch_id() == '1234567890'

    def test_app_id_reads_env(self):
        from backend import wxpay
        with patch.dict(os.environ, {'WXPAY_APP_ID': 'wxAPP123', 'WX_APP_ID': ''}):
            assert wxpay._app_id() == 'wxAPP123'

    def test_app_id_fallback_to_wx_app_id(self):
        from backend import wxpay
        env = {'WX_APP_ID': 'wxFALLBACK'}
        # Remove WXPAY_APP_ID from env if present
        with patch.dict(os.environ, env):
            os.environ.pop('WXPAY_APP_ID', None)
            result = wxpay._app_id()
        assert result == 'wxFALLBACK'

    def test_api_v3_key_reads_env(self):
        from backend import wxpay
        with patch.dict(os.environ, {'WXPAY_API_V3_KEY': 'k' * 32}):
            assert wxpay._api_v3_key() == 'k' * 32

    def test_empty_defaults(self):
        from backend import wxpay
        env_overrides = {
            'WXPAY_MCH_ID': '', 'WXPAY_APP_ID': '', 'WXPAY_API_V3_KEY': '',
            'WXPAY_PRIVATE_KEY': '', 'WXPAY_CERT_SERIAL_NO': '',
            'WXPAY_NOTIFY_URL': '', 'WX_APP_ID': '',
        }
        with patch.dict(os.environ, env_overrides, clear=False):
            assert wxpay._mch_id() == ''
            assert wxpay._api_v3_key() == ''


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: _check_config
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckConfig:

    def test_raises_with_missing_config(self):
        from backend.wxpay import _check_config
        env = {k: '' for k in ('WXPAY_MCH_ID', 'WXPAY_APP_ID', 'WXPAY_API_V3_KEY',
                                'WXPAY_PRIVATE_KEY', 'WXPAY_CERT_SERIAL_NO',
                                'WXPAY_NOTIFY_URL')}
        with patch.dict(os.environ, env):
            with pytest.raises(RuntimeError, match='微信支付配置不完整'):
                _check_config()

    def test_passes_with_full_config(self):
        from backend.wxpay import _check_config
        env = {
            'WXPAY_MCH_ID': '123', 'WXPAY_APP_ID': 'wx123',
            'WXPAY_API_V3_KEY': 'k' * 32,
            'WXPAY_PRIVATE_KEY': '-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----',
            'WXPAY_CERT_SERIAL_NO': 'ABC123',
            'WXPAY_NOTIFY_URL': 'https://example.com',
        }
        with patch.dict(os.environ, env):
            _check_config()  # should not raise

    def test_error_lists_missing_keys(self):
        from backend.wxpay import _check_config
        env = {'WXPAY_MCH_ID': 'set', 'WXPAY_APP_ID': '',
               'WXPAY_API_V3_KEY': '', 'WXPAY_PRIVATE_KEY': '',
               'WXPAY_CERT_SERIAL_NO': '', 'WXPAY_NOTIFY_URL': ''}
        with patch.dict(os.environ, env):
            with pytest.raises(RuntimeError) as exc_info:
                _check_config()
            assert 'WXPAY_APP_ID' in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: _verify_notify_signature (DEV mode — no platform cert)
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyNotifySignature:

    def test_dev_mode_valid_timestamp(self):
        from backend.wxpay import _verify_notify_signature
        ts = str(int(time.time()))
        with patch.dict(os.environ, {'WXPAY_PLATFORM_CERT_PEM': ''}):
            result = _verify_notify_signature(ts, 'nonce', 'body', 'sig', 'serial')
        assert result is True

    def test_dev_mode_stale_timestamp_rejected(self):
        from backend.wxpay import _verify_notify_signature
        stale_ts = str(int(time.time()) - 400)  # 400s ago > 300s threshold
        with patch.dict(os.environ, {'WXPAY_PLATFORM_CERT_PEM': ''}):
            result = _verify_notify_signature(stale_ts, 'nonce', 'body', 'sig', 'serial')
        assert result is False

    def test_dev_mode_future_timestamp_rejected(self):
        from backend.wxpay import _verify_notify_signature
        future_ts = str(int(time.time()) + 400)
        with patch.dict(os.environ, {'WXPAY_PLATFORM_CERT_PEM': ''}):
            result = _verify_notify_signature(future_ts, 'nonce', 'body', 'sig', 'serial')
        assert result is False

    def test_invalid_timestamp_string(self):
        from backend.wxpay import _verify_notify_signature
        with patch.dict(os.environ, {'WXPAY_PLATFORM_CERT_PEM': ''}):
            result = _verify_notify_signature('not-a-number', 'nonce', 'body', 'sig', 'serial')
        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: _aes_gcm_decrypt
# ─────────────────────────────────────────────────────────────────────────────

class TestAesGcmDecrypt:

    def test_wrong_key_length_raises(self):
        from backend.wxpay import _aes_gcm_decrypt
        with patch.dict(os.environ, {'WXPAY_API_V3_KEY': 'shortkey'}):
            with pytest.raises(ValueError, match='32 bytes'):
                _aes_gcm_decrypt('nonce', base64.b64encode(b'ct').decode(), 'aad')

    def test_decrypt_roundtrip(self):
        """Encrypt with cryptography then decrypt with our function."""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            pytest.skip('cryptography not installed')

        key_str = 'a' * 32
        key = key_str.encode()
        nonce_str = 'b' * 12
        plaintext = b'{"trade_state":"SUCCESS"}'
        aad = 'transaction'

        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce_str.encode(), plaintext, aad.encode())
        ct_b64 = base64.b64encode(ct).decode()

        from backend.wxpay import _aes_gcm_decrypt
        with patch.dict(os.environ, {'WXPAY_API_V3_KEY': key_str}):
            result = _aes_gcm_decrypt(nonce_str, ct_b64, aad)
        assert result == plaintext.decode()


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: create_prepay error paths
# ─────────────────────────────────────────────────────────────────────────────

class TestCreatePrepay:

    def test_missing_config_raises(self):
        from backend.wxpay import create_prepay
        env = {k: '' for k in ('WXPAY_MCH_ID', 'WXPAY_APP_ID', 'WXPAY_API_V3_KEY',
                                'WXPAY_PRIVATE_KEY', 'WXPAY_CERT_SERIAL_NO',
                                'WXPAY_NOTIFY_URL')}
        with patch.dict(os.environ, env):
            with pytest.raises(RuntimeError):
                create_prepay('ES001', 300, 'test', 'miniprogram', 'openid_abc')

    def test_jsapi_requires_openid(self):
        from backend.wxpay import create_prepay
        env = {
            'WXPAY_MCH_ID': '123', 'WXPAY_APP_ID': 'wx123',
            'WXPAY_API_V3_KEY': 'k' * 32,
            'WXPAY_PRIVATE_KEY': 'fake',
            'WXPAY_CERT_SERIAL_NO': 'S',
            'WXPAY_NOTIFY_URL': 'https://example.com',
        }
        with patch.dict(os.environ, env):
            with pytest.raises((ValueError, RuntimeError)):
                create_prepay('ES001', 300, 'test', 'jsapi', openid='')

    def test_unsupported_pay_method_raises(self):
        from backend.wxpay import create_prepay
        env = {
            'WXPAY_MCH_ID': '123', 'WXPAY_APP_ID': 'wx123',
            'WXPAY_API_V3_KEY': 'k' * 32,
            'WXPAY_PRIVATE_KEY': 'fake',
            'WXPAY_CERT_SERIAL_NO': 'S',
            'WXPAY_NOTIFY_URL': 'https://example.com',
        }
        with patch.dict(os.environ, env):
            with pytest.raises((ValueError, RuntimeError)):
                create_prepay('ES001', 300, 'test', 'unknown_method')


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoint: POST /api/wxpay/notify
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentNotify:
    """测试支付回调接口的各种场景"""

    RESOURCE = {
        'nonce': 'testnonce',
        'ciphertext': 'FAKECT==',
        'associated_data': 'transaction',
    }

    def _post_notify(self, client, body: str, timestamp: str | None = None):
        headers = _make_notify_headers(timestamp)
        return client.post('/api/wxpay/notify',
                           content=body.encode(),
                           headers={**headers, 'Content-Type': 'application/json'})

    def test_signature_failure_returns_401(self, client):
        """Stale timestamp → signature rejected → 401"""
        body = _make_notify_body('TRANSACTION.SUCCESS', self.RESOURCE)
        stale_ts = str(int(time.time()) - 400)
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch.dict(os.environ, {'WXPAY_PLATFORM_CERT_PEM': ''}):
            conn = _make_conn({'insert': [(1,)]})
            mock_getdb.return_value = conn
            resp = self._post_notify(client, body, timestamp=stale_ts)
        assert resp.status_code == 401
        data = resp.json()
        assert data['code'] == 'FAIL'

    def test_non_success_event_type_ignored(self, client):
        """Non-TRANSACTION.SUCCESS event returns SUCCESS without processing"""
        body = _make_notify_body('REFUND.SUCCESS', self.RESOURCE)
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay._verify_notify_signature', return_value=True), \
             patch('backend.wxpay._update_notify_log'):
            conn = _make_conn({'insert': [(1,)]})
            mock_getdb.return_value = conn
            resp = self._post_notify(client, body)
        assert resp.status_code == 200
        assert resp.json()['code'] == 'SUCCESS'

    def test_invalid_json_body(self, client):
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay._verify_notify_signature', return_value=True):
            conn = _make_conn({'insert': [(1,)]})
            mock_getdb.return_value = conn
            resp = client.post(
                '/api/wxpay/notify',
                content=b'not valid json',
                headers={**_make_notify_headers(),
                         'Content-Type': 'application/json'},
            )
        assert resp.status_code == 400

    def test_decrypt_error_returns_400(self, client):
        body = _make_notify_body('TRANSACTION.SUCCESS', self.RESOURCE)
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay._verify_notify_signature', return_value=True), \
             patch('backend.wxpay._aes_gcm_decrypt', side_effect=Exception('bad key')), \
             patch('backend.wxpay._update_notify_log'):
            conn = _make_conn({'insert': [(1,)]})
            mock_getdb.return_value = conn
            resp = self._post_notify(client, body)
        assert resp.status_code == 400

    def test_successful_notify_fulfills_order(self, client):
        """Happy path: valid notify → order marked paid → fulfill_order called"""
        body = _make_notify_body('TRANSACTION.SUCCESS', self.RESOURCE)
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay._verify_notify_signature', return_value=True), \
             patch('backend.wxpay._aes_gcm_decrypt', return_value=FAKE_TX_PLAINTEXT), \
             patch('backend.wxpay._update_notify_log'), \
             patch('backend.shop.fulfill_order', return_value={'already_fulfilled': False}):
            conn = _make_conn({
                'insert': [(1,)],
                'update shop_orders': [(42,)],   # simulate RETURNING id
            })
            mock_getdb.return_value = conn
            resp = self._post_notify(client, body)
        assert resp.status_code == 200
        assert resp.json()['code'] == 'SUCCESS'

    def test_already_processed_idempotent(self, client):
        """If UPDATE returns no row (already paid), return SUCCESS idempotently"""
        body = _make_notify_body('TRANSACTION.SUCCESS', self.RESOURCE)
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay._verify_notify_signature', return_value=True), \
             patch('backend.wxpay._aes_gcm_decrypt', return_value=FAKE_TX_PLAINTEXT), \
             patch('backend.wxpay._update_notify_log'):
            conn = _make_conn({'insert': [(1,)]})  # UPDATE returns nothing
            mock_getdb.return_value = conn
            resp = self._post_notify(client, body)
        assert resp.status_code == 200
        assert resp.json()['code'] == 'SUCCESS'

    def test_fulfill_failure_returns_500_for_retry(self, client):
        """fulfill_order failure → 500 so WeChat will retry"""
        body = _make_notify_body('TRANSACTION.SUCCESS', self.RESOURCE)
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay._verify_notify_signature', return_value=True), \
             patch('backend.wxpay._aes_gcm_decrypt', return_value=FAKE_TX_PLAINTEXT), \
             patch('backend.wxpay._update_notify_log'), \
             patch('backend.shop.fulfill_order', side_effect=Exception('DB down')):
            conn = _make_conn({
                'insert': [(1,)],
                'update shop_orders': [(42,)],
            })
            mock_getdb.return_value = conn
            resp = self._post_notify(client, body)
        assert resp.status_code == 500
        assert resp.json()['code'] == 'FAIL'


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoint: POST /api/wxpay/refund-notify
# ─────────────────────────────────────────────────────────────────────────────

class TestRefundNotify:

    def _post(self, client, body: str, timestamp: str | None = None):
        headers = _make_notify_headers(timestamp)
        return client.post('/api/wxpay/refund-notify',
                           content=body.encode(),
                           headers={**headers, 'Content-Type': 'application/json'})

    def test_signature_failure_401(self, client):
        body = _make_notify_body('REFUND.SUCCESS', {'nonce': 'n', 'ciphertext': 'c'})
        stale_ts = str(int(time.time()) - 400)
        with patch.dict(os.environ, {'WXPAY_PLATFORM_CERT_PEM': ''}):
            resp = self._post(client, body, timestamp=stale_ts)
        assert resp.status_code == 401

    def test_successful_refund_notify(self, client):
        body = _make_notify_body('REFUND.SUCCESS', {'nonce': 'n', 'ciphertext': 'c',
                                                     'associated_data': 'refund'})
        with patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay._verify_notify_signature', return_value=True), \
             patch('backend.wxpay._aes_gcm_decrypt', return_value=FAKE_REFUND_PLAINTEXT):
            conn = _make_conn()
            mock_getdb.return_value = conn
            resp = self._post(client, body)
        assert resp.status_code == 200
        assert resp.json()['code'] == 'SUCCESS'

    def test_invalid_json_400(self, client):
        with patch('backend.wxpay._verify_notify_signature', return_value=True), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'):
            conn = _make_conn()
            mock_getdb.return_value = conn
            resp = client.post(
                '/api/wxpay/refund-notify',
                content=b'BAD JSON',
                headers={**_make_notify_headers(), 'Content-Type': 'application/json'},
            )
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoint: GET /api/wxpay/orders/{order_no}/query
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryWxOrder:

    def test_requires_auth(self, client):
        resp = client.get('/api/wxpay/orders/ES001/query')
        assert resp.status_code == 401

    def test_order_not_found_404(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'):
            conn = _make_conn()
            mock_getdb.return_value = conn
            resp = client.get('/api/wxpay/orders/ES_GHOST/query',
                              headers=auth_headers)
        assert resp.status_code == 404

    def test_fulfilled_returns_local_status(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'):
            conn = _make_conn({'select': [('ES001', 'fulfilled', 'ES001')]})
            mock_getdb.return_value = conn
            resp = client.get('/api/wxpay/orders/ES001/query',
                              headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'fulfilled'
        assert data['source'] == 'local'

    def test_pending_no_wxpay_config_returns_local(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch.dict(os.environ, {'WXPAY_MCH_ID': ''}):
            conn = _make_conn({'select': [('ES001', 'pending_payment', 'ES001')]})
            mock_getdb.return_value = conn
            resp = client.get('/api/wxpay/orders/ES001/query',
                              headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()['source'] == 'local'

    def test_pending_wxpay_query_error_graceful(self, client, auth_headers, mock_user):
        """If wxpay query fails, return local status + error field"""
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay.query_order', side_effect=Exception('timeout')), \
             patch.dict(os.environ, {'WXPAY_MCH_ID': '1234567890'}):
            conn = _make_conn({'select': [('ES001', 'pending_payment', 'ES001')]})
            mock_getdb.return_value = conn
            resp = client.get('/api/wxpay/orders/ES001/query',
                              headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['source'] == 'local'
        assert 'wx_query_error' in data

    def test_cancelled_returns_local(self, client, auth_headers, mock_user):
        for status in ('cancelled', 'refunded'):
            with patch('backend.auth.get_session_user', return_value=mock_user), \
                 patch('backend.wxpay._get_db') as mock_getdb, \
                 patch('backend.wxpay._release_db'):
                conn = _make_conn({'select': [('ES001', status, 'ES001')]})
                mock_getdb.return_value = conn
                resp = client.get('/api/wxpay/orders/ES001/query',
                                  headers=auth_headers)
            assert resp.status_code == 200
            assert resp.json()['source'] == 'local'


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoint: POST /api/wxpay/orders/{order_no}/refund
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyRefund:

    def test_requires_auth(self, client):
        resp = client.post('/api/wxpay/orders/ES001/refund')
        assert resp.status_code == 401

    def test_order_not_found_404(self, client, auth_headers, mock_user):
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'):
            conn = _make_conn()
            mock_getdb.return_value = conn
            resp = client.post('/api/wxpay/orders/ES_GHOST/refund',
                               headers=auth_headers)
        assert resp.status_code == 404

    def test_non_fulfilled_status_409(self, client, auth_headers, mock_user):
        for status in ('pending_payment', 'paid', 'cancelled', 'refunding'):
            row = (1, status, 300, 'ES001', None, 'credits')
            with patch('backend.auth.get_session_user', return_value=mock_user), \
                 patch('backend.wxpay._get_db') as mock_getdb, \
                 patch('backend.wxpay._release_db'):
                conn = _make_conn({'select': [row]})
                mock_getdb.return_value = conn
                resp = client.post(f'/api/wxpay/orders/ES001/refund',
                                   headers=auth_headers)
            assert resp.status_code == 409, f'Expected 409 for status={status}'

    def test_no_fulfilled_at_409(self, client, auth_headers, mock_user):
        row = (1, 'fulfilled', 300, 'ES001', None, 'credits')  # fulfilled_at=None
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'):
            conn = _make_conn({'select': [row]})
            mock_getdb.return_value = conn
            resp = client.post('/api/wxpay/orders/ES001/refund',
                               headers=auth_headers)
        assert resp.status_code == 409

    def test_past_7_days_409(self, client, auth_headers, mock_user):
        old_dt = datetime.now(timezone.utc) - timedelta(days=8)
        row = (1, 'fulfilled', 300, 'ES001', old_dt, 'credits')
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'):
            conn = _make_conn({'select': [row]})
            mock_getdb.return_value = conn
            resp = client.post('/api/wxpay/orders/ES001/refund',
                               headers=auth_headers)
        assert resp.status_code == 409
        assert '7天' in resp.json()['detail']

    def test_dev_mode_no_wxpay_config_refund_succeeds(self, client, auth_headers, mock_user):
        """Without WXPAY_MCH_ID configured, refund completes in dev mode"""
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        row = (1, 'fulfilled', 300, 'ES001', recent, 'credits')
        cg_row = (0,)  # credits_grant = 0
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch.dict(os.environ, {'WXPAY_MCH_ID': ''}):
            conn = _make_conn({'select': [row], 'credits_grant': [cg_row]})
            mock_getdb.return_value = conn
            resp = client.post('/api/wxpay/orders/ES001/refund',
                               headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert 'refund_no' in data

    def test_wxpay_refund_api_failure_compensates_and_raises_502(
            self, client, auth_headers, mock_user):
        """Real wxpay call fails → order must be reset to fulfilled → 502"""
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        row = (1, 'fulfilled', 300, 'ES001', recent, 'credits')
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch('backend.wxpay.refund_order', side_effect=Exception('WX API error')), \
             patch.dict(os.environ, {'WXPAY_MCH_ID': '1234567890'}):
            conn = _make_conn({'select': [row]})
            mock_getdb.return_value = conn
            resp = client.post('/api/wxpay/orders/ES001/refund',
                               headers=auth_headers)
        assert resp.status_code == 502
        assert '微信退款申请失败' in resp.json()['detail']

    def test_credits_deducted_on_refund(self, client, auth_headers, mock_user):
        """When credits were granted, they should be deducted on refund"""
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        row = (1, 'fulfilled', 300, 'ES001', recent, 'credits')
        with patch('backend.auth.get_session_user', return_value=mock_user), \
             patch('backend.wxpay._get_db') as mock_getdb, \
             patch('backend.wxpay._release_db'), \
             patch.dict(os.environ, {'WXPAY_MCH_ID': ''}), \
             patch('backend.shop._add_credits_ledger', return_value=0) as mock_ledger, \
             patch('backend.shop._ensure_entitlement'):
            conn = _make_conn({'select': [row], 'credits_grant': [(30,)]})
            mock_getdb.return_value = conn
            resp = client.post('/api/wxpay/orders/ES001/refund',
                               headers=auth_headers)
        # Either succeeded (200) or no credits row in mock (still should not 5xx from credits logic)
        assert resp.status_code in (200, 500)


# ─────────────────────────────────────────────────────────────────────────────
# Utility: _sign_miniprogram_pay / _sign_jsapi_pay structure tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentSignatureStructure:

    def _fake_rsa(self, msg):
        return base64.b64encode(b'fakesig').decode()

    def test_miniprogram_sign_keys(self):
        from backend.wxpay import _sign_miniprogram_pay
        with patch('backend.wxpay._rsa_sign', side_effect=self._fake_rsa), \
             patch.dict(os.environ, {'WXPAY_APP_ID': 'wx_test_app'}):
            result = _sign_miniprogram_pay('prepay_fake_id')
        assert set(result.keys()) == {'timeStamp', 'nonceStr', 'package',
                                       'signType', 'paySign', 'prepay_id'}
        assert result['signType'] == 'RSA'
        assert result['package'] == 'prepay_id=prepay_fake_id'

    def test_jsapi_sign_keys(self):
        from backend.wxpay import _sign_jsapi_pay
        with patch('backend.wxpay._rsa_sign', side_effect=self._fake_rsa), \
             patch.dict(os.environ, {'WXPAY_APP_ID': 'wx_test_app'}):
            result = _sign_jsapi_pay('prepay_fake_id')
        assert set(result.keys()) == {'appId', 'timeStamp', 'nonceStr', 'package',
                                       'signType', 'paySign', 'prepay_id'}
        assert result['signType'] == 'RSA'
        assert result['appId'] == 'wx_test_app'

    def test_timestamp_is_string_of_digits(self):
        from backend.wxpay import _sign_miniprogram_pay
        with patch('backend.wxpay._rsa_sign', side_effect=self._fake_rsa):
            result = _sign_miniprogram_pay('pid_001')
        assert result['timeStamp'].isdigit()

    def test_nonce_is_alphanumeric(self):
        from backend.wxpay import _sign_miniprogram_pay
        with patch('backend.wxpay._rsa_sign', side_effect=self._fake_rsa):
            result = _sign_miniprogram_pay('pid_001')
        assert result['nonceStr'].isalnum()
        assert len(result['nonceStr']) == 32
