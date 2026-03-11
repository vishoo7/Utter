import json
import os
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def _reset_server_state(tmp_path):
    """Reset global server state before each test and use a temp directory."""
    import server

    server.STATIC_DIR = str(tmp_path / "static")
    server.UPLOAD_DIR = str(tmp_path / "uploads")
    server.HISTORY_FILE = str(tmp_path / "history.json")
    os.makedirs(server.STATIC_DIR, exist_ok=True)
    os.makedirs(server.UPLOAD_DIR, exist_ok=True)

    server.status = {"state": "idle", "filename": None, "error": None}
    server.transcribe_status = {"state": "idle", "text": None, "error": None}
    server.history = []
    server.pipeline = MagicMock(name="pipeline")
    server.whisper_model = "mock-model"
    server.generation_lock = threading.Lock()


@pytest.fixture
def client():
    """Flask test client."""
    import server

    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c
