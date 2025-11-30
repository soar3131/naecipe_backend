"""Pytest configuration and fixtures"""

import pytest
from fastapi.testclient import TestClient

from ai_agent_service.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)
