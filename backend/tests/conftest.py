import os
import sys
import tempfile
from pathlib import Path

# Isolated test environment: must be configured BEFORE importing the app.
# Set TEST_DATABASE_URL to run the suite against PostgreSQL, e.g.
#   TEST_DATABASE_URL=postgresql+psycopg2://prjhub:prjhub_secret@127.0.0.1:5432/prjhub_test pytest -q
import os
import sys
import tempfile
from pathlib import Path

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "")

if TEST_DB_URL:
    os.environ["DATABASE_URL"] = TEST_DB_URL
    # clean schema for a repeatable PG run
    from sqlalchemy import create_engine, text

    _pg_engine = create_engine(TEST_DB_URL)
    with _pg_engine.begin() as _conn:
        _conn.execute(text("DROP SCHEMA public CASCADE"))
        _conn.execute(text("CREATE SCHEMA public"))
    _pg_engine.dispose()
else:
    _TMP = tempfile.mkdtemp(prefix="prjhub-test-")
    os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
    os.environ["REPOS_DIR"] = f"{_TMP}/repos"

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_headers(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def make_user(client: TestClient, username: str, name: str = "", superuser_by_admin=True) -> dict:
    """Register a normal local user through WeCom-mocked provisioning (no register API)."""
    from app.db import SessionLocal
    from app.core.security import hash_password
    from app.models import AuthType, User

    db = SessionLocal()
    try:
        user = User(username=username, password_hash=hash_password("pass123"), name=name or username,
                    auth_type=AuthType.local)
        db.add(user)
        db.commit()
        return {"id": user.id, "username": user.username}
    finally:
        db.close()


def login_as(client: TestClient, username: str, password: str = "pass123") -> dict:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
