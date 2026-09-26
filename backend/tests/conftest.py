"""测试夹具：隔离环境变量，避免测试触发任何外部调用。"""
import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
for path in (BACKEND_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ("OPENAI_API_KEY", "PYANNOTE_AUTH_TOKEN", "SMTP_SERVER", "SMTP_USER",
                 "SMTP_PASSWORD", "ENCRYPTION_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    import backend.main as main_module
    return TestClient(main_module.app, raise_server_exceptions=False)
