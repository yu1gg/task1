import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["TEACHER_INVITE_CODE"] = "teacher-secret"
os.environ["DEEPSEEK_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
