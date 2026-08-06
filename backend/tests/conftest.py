import os
import shutil
from pathlib import Path

TEST_STORAGE = Path(__file__).resolve().parent / ".tmp_storage"
if TEST_STORAGE.exists():
    shutil.rmtree(TEST_STORAGE)
TEST_STORAGE.mkdir(parents=True, exist_ok=True)

# Must be set before `app.config` is imported anywhere (including
# transitively via app.main) so the test suite never touches the real
# dev database/storage under backend/storage/.
os.environ["DOCUFLOW_STORAGE_DIR"] = str(TEST_STORAGE)
os.environ["DOCUFLOW_DATABASE_URL"] = f"sqlite:///{(TEST_STORAGE / 'test.db').as_posix()}"
os.environ["DOCUFLOW_FRONTEND_BASE_URL"] = "http://localhost:5173"
os.environ["DOCUFLOW_REMINDER_AFTER_DAYS"] = "2"
os.environ["DOCUFLOW_REMINDER_MIN_INTERVAL_DAYS"] = "2"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
