import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="benji_test_")
os.environ["BENJI_DB"] = os.path.join(_TMP, "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["BENJI_DEMO_MODE"] = "1"  # synthetic fixtures for tests only; off by default for users


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from benji import api

    api.store.wipe()
    return TestClient(api.app)


@pytest.fixture()
def demo(client):
    r = client.post("/api/demo/reset")
    assert r.status_code == 200
    return client
