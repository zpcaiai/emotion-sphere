"""
Tests for Persona Tag, Identity, and Execution system endpoints.
These tests cover the newer subsystems added to the application.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ── Helper ────────────────────────────────────────────────────

def _auth_header(token='test-token-for-testing'):
    """Return auth header (requires a valid token in the DB for full integration)"""
    return {'Authorization': f'Bearer {token}'}


# ── Persona Tag System ─────────────────────────────────────────

class TestPersonaTagEndpoints:
    """Test persona tag extraction and profile endpoints"""

    def test_extract_tags_no_auth(self):
        """Extracting tags without auth should fail"""
        resp = client.post('/api/persona/extract', json={
            'text': '我今天很焦虑',
            'context': 'emotion'
        })
        assert resp.status_code in [401, 403, 500]

    def test_get_tags_no_auth(self):
        """Getting persona tags without auth should fail"""
        resp = client.get('/api/persona/tags')
        assert resp.status_code in [401, 403, 500]

    def test_get_profile_no_auth(self):
        """Getting persona profile without auth should fail"""
        resp = client.get('/api/persona/profile')
        assert resp.status_code in [401, 403, 500]

    def test_add_tag_validation(self):
        """Adding a tag requires proper payload"""
        resp = client.post('/api/persona/tags', json={})
        assert resp.status_code in [401, 422, 500]

    def test_delete_tag_no_auth(self):
        """Deleting a tag without auth should fail"""
        resp = client.delete('/api/persona/tags/00000000-0000-0000-0000-000000000001')
        assert resp.status_code in [401, 403, 500]


# ── Identity System ────────────────────────────────────────────

class TestIdentityEndpoints:
    """Test identity reinforcement and deconstruction endpoints"""

    def test_reinforce_identity_no_auth(self):
        """Identity reinforcement without auth should fail"""
        resp = client.post('/api/identity/reinforce', json={
            'recentBehaviors': ['completed morning prayer'],
            'emotionState': 'hopeful'
        })
        assert resp.status_code in [401, 403, 422, 500]

    def test_deconstruct_label_no_auth(self):
        """Label deconstruction without auth should fail"""
        resp = client.post('/api/identity/deconstruct', json={
            'negativeLabel': '我是懒惰的人'
        })
        assert resp.status_code in [401, 403, 422, 500]

    def test_identity_dashboard_no_auth(self):
        """Identity dashboard without auth should fail"""
        resp = client.get('/api/identity/dashboard')
        assert resp.status_code in [401, 403, 500]

    def test_personality_migrations_no_auth(self):
        """Personality migrations without auth should fail"""
        resp = client.get('/api/identity/migrations')
        assert resp.status_code in [401, 403, 500]


# ── Execution System ───────────────────────────────────────────

class TestExecutionEndpoints:
    """Test execution paralysis detection and intervention endpoints"""

    def test_detect_intervene_no_auth(self):
        """Edge detection without auth should fail"""
        resp = client.post('/api/execution/detect-intervene', json={
            'raw_task': '写论文',
            'edge_context': {},
            'telemetry_signals': []
        })
        assert resp.status_code in [401, 403, 500]

    def test_micro_chain_validation(self):
        """Micro chain requires valid task"""
        resp = client.post('/api/execution/micro-chain', json={
            'task': '',
            'steps': 3
        })
        assert resp.status_code == 422

    def test_micro_chain_steps_range(self):
        """Micro chain steps must be 1-10"""
        resp = client.post('/api/execution/micro-chain', json={
            'task': '写论文',
            'steps': 99
        })
        assert resp.status_code == 422

    def test_crash_detect_no_auth(self):
        """Crash detection without auth should fail"""
        resp = client.post('/api/execution/crash-detect', json={
            'telemetry': {'delay': 300, 'switches': 5}
        })
        assert resp.status_code in [401, 403, 422, 500]

    def test_ignite_no_auth(self):
        """Ignition sequence without auth should fail"""
        resp = client.post('/api/execution/ignite', json={
            'resistance': 'perfectionism',
            'risk_score': 7
        })
        assert resp.status_code in [401, 403, 422, 500]

    def test_micro_momentum_no_auth(self):
        """Micro momentum dashboard without auth should fail"""
        resp = client.get('/api/execution/micro-momentum')
        assert resp.status_code in [401, 403, 500]

    def test_execution_dashboard_no_auth(self):
        """Execution dashboard without auth should fail"""
        resp = client.get('/api/execution/dashboard')
        assert resp.status_code in [401, 403, 500]

    def test_complete_session_validation(self):
        """Complete session requires valid payload"""
        resp = client.post('/api/execution/complete', json={})
        assert resp.status_code in [401, 422, 500]


# ── Behavior & Habits System ──────────────────────────────────

class TestBehaviorHabitEndpoints:
    """Test behavior regulation and habit endpoints"""

    def test_behavior_regulate_no_auth(self):
        """Behavior regulation without auth should fail"""
        resp = client.post('/api/behavior/regulate', json={
            'task': '整理房间',
            'energy_level': 3,
            'motivation': 5
        })
        assert resp.status_code in [401, 403, 500]

    def test_behavior_regulate_validation(self):
        """Behavior regulation validates energy level range"""
        resp = client.post('/api/behavior/regulate', json={
            'task': '整理房间',
            'energy_level': 99,
            'motivation': 5
        })
        assert resp.status_code in [401, 422, 500]

    def test_create_habit_no_auth(self):
        """Creating habit without auth should fail"""
        resp = client.post('/api/habits/create', json={
            'habit_name': '每日跑步',
            'anchor': '起床后',
            'energy_level': 3
        })
        assert resp.status_code in [401, 403, 500]

    def test_list_habits_no_auth(self):
        """Listing habits without auth should fail"""
        resp = client.get('/api/habits')
        assert resp.status_code in [401, 403, 500]

    def test_habits_dashboard_no_auth(self):
        """Habits dashboard without auth should fail"""
        resp = client.get('/api/habits/dashboard')
        assert resp.status_code in [401, 403, 500]

    def test_behavior_history_no_auth(self):
        """Behavior history without auth should fail"""
        resp = client.get('/api/behavior/history')
        assert resp.status_code in [401, 403, 500]

    def test_behavior_stats_no_auth(self):
        """Behavior stats without auth should fail"""
        resp = client.get('/api/behavior/stats')
        assert resp.status_code in [401, 403, 500]


# ── Personality OS System ──────────────────────────────────────

class TestPersonalityOSEndpoints:
    """Test Personality OS state machine endpoints"""

    def test_os_process_no_auth(self):
        """OS process without auth should fail"""
        resp = client.post('/api/os/process', json={
            'userInput': 'I feel stuck',
            'telemetry': {},
            'currentState': 'NORMAL'
        })
        assert resp.status_code in [401, 403, 422, 500]

    def test_os_dashboard_no_auth(self):
        """OS dashboard without auth should fail"""
        resp = client.get('/api/os/dashboard')
        assert resp.status_code in [401, 403, 500]

    def test_set_state_no_auth(self):
        """Set state without auth should fail"""
        resp = client.post('/api/os/set-state', json={
            'new_state': 'LOW_ENERGY'
        })
        assert resp.status_code in [401, 403, 500]


# ── Public Endpoints (should work without auth) ────────────────

class TestPublicEndpoints:
    """Test endpoints that should work without authentication"""

    def test_health_check(self):
        """Health check should always return 200"""
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('status') == 'ok'

    def test_root(self):
        """Root endpoint returns API info"""
        resp = client.get('/')
        assert resp.status_code == 200

    def test_layout_endpoint(self):
        """Layout endpoint should return data or fallback"""
        resp = client.get('/api/layout')
        assert resp.status_code == 200

    def test_stats_endpoint(self):
        """Stats endpoint should return visit statistics"""
        resp = client.get('/api/stats')
        assert resp.status_code == 200
