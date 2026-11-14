import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["TEACHER_INVITE_CODE"] = "teacher-secret"
os.environ["DEEPSEEK_API_KEY"] = "test-key"
os.environ["INTERVIEW_WORKER_ENABLED"] = "false"
os.environ["RESUME_EXPORT_WORKER_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.db import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
