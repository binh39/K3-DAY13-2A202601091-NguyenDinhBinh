from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app import main as main_module


CORRELATION_ID_RE = re.compile(r"^req-[0-9a-fA-F]{8}$")


def test_middleware_preserves_valid_id_and_replaces_invalid_id() -> None:
    with TestClient(main_module.app) as client:
        supplied = client.get("/health", headers={"x-request-id": "req-deadBEEF"})
        generated = client.get("/health", headers={"x-request-id": "not-safe"})

    assert supplied.status_code == 200
    assert supplied.headers["x-request-id"] == "req-deadBEEF"
    assert CORRELATION_ID_RE.fullmatch(generated.headers["x-request-id"])
    assert generated.headers["x-response-time-ms"]


def test_unexpected_chat_error_uses_safe_handler(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    secret_detail = "sensitive-backend-detail"

    def fail(*args, **kwargs):
        raise RuntimeError(secret_detail)

    monkeypatch.setattr(main_module.agent, "run", fail)

    with TestClient(main_module.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "req-aBcD1234"},
            json={
                "user_id": "student-01",
                "session_id": "session-01",
                "feature": "qa",
                "message": "hello",
            },
        )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error",
        "correlation_id": "req-aBcD1234",
    }
    assert response.headers["x-request-id"] == "req-aBcD1234"
    assert response.headers["x-response-time-ms"]

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    failed = next(event for event in events if event["event"] == "request_failed")
    assert failed["correlation_id"] == "req-aBcD1234"
    assert failed["error_type"] == "RuntimeError"
    assert secret_detail not in log_path.read_text(encoding="utf-8")
