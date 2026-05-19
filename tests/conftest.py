"""
Pytest configuration and fixtures
"""

import pytest
import os

# Set test environment
os.environ['ENVIRONMENT'] = 'testing'
os.environ['ENCRYPTION_KEY'] = 'test-key-for-development-only-do-not-use-in-production'

@pytest.fixture(scope='session')
def test_db():
    """Setup test database"""
    # This would setup a test database
    yield
    # Cleanup

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {
        'id': 1,
        'email': 'test@example.com',
        'nickname': 'Test User'
    }
