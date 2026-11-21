from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_assistant_status_chat_and_daily_load_configured_secret(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.delenv("SARVAM_API_URL", raising=False)

    app = create_app(Path("data/csv"))
    client = TestClient(app)

    status = client.get("/api/assistant/status")
    assert status.status_code == 200
    assert status.json()["configured"] is True

    chat = client.post("/api/assistant/chat", json={"query": "show me the overall network"})
    assert chat.status_code == 200
    assert chat.json()["status"] in ("ok", "fallback")
    assert chat.json()["text"]
    assert chat.json()["citations"]

    daily = client.get("/api/assistant/daily")
    assert daily.status_code == 200
    assert daily.json()["text"]


def test_assistant_chat_requires_query(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.delenv("SARVAM_API_URL", raising=False)
    client = TestClient(create_app(Path("data/csv")))

    response = client.post("/api/assistant/chat", json={"query": "  "})

    assert response.status_code == 400
