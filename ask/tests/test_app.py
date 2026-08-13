import numpy as np
from fastapi.testclient import TestClient

from ask import app as app_module

FAKE_CHUNKS = [
    {
        "id": "a",
        "author": "Pranay",
        "post_title": "Edition One",
        "post_url": "https://example.com/one",
        "date": "2024-01-01",
        "header": "India Policy Watch",
        "section_title": "Rent Control",
        "text": "Rent control tends to reduce housing supply over time.",
    },
    {
        "id": "b",
        "author": "RSJ",
        "post_title": "Edition Two",
        "post_url": "https://example.com/two",
        "date": "2024-02-01",
        "header": "Global Policy Watch",
        "section_title": "Rent Control Elsewhere",
        "text": "Rent control can help incumbent tenants in the short run.",
    },
]
FAKE_VECTORS = np.array([[1.0, 0.0], [0.9, 0.1]], dtype=np.float32)


def make_client(monkeypatch):
    monkeypatch.setattr(app_module, "get_index", lambda: {"chunks": FAKE_CHUNKS, "vectors": FAKE_VECTORS})
    monkeypatch.setattr(app_module, "embed_texts", lambda texts: np.array([[1.0, 0.0]], dtype=np.float32))
    monkeypatch.setattr(app_module, "generate_connector", lambda author, question, excerpts: f"Connector for {author}")
    app_module.rate_limiter = app_module.RateLimiter(max_requests=100, window_seconds=3600)
    app_module.cache = app_module.TTLCache(ttl_seconds=86400)
    return TestClient(app_module.app)


def test_ask_returns_grouped_excerpts(monkeypatch):
    client = make_client(monkeypatch)
    response = client.post("/ask", json={"question": "how should I think about rent control?"})
    assert response.status_code == 200
    body = response.json()
    authors = {g["author"] for g in body["groups"]}
    assert "Pranay" in authors
    assert "RSJ" in authors
    pranay_group = next(g for g in body["groups"] if g["author"] == "Pranay")
    assert pranay_group["connector_text"] == "Connector for Pranay"
    assert pranay_group["excerpts"][0]["url"] == "https://example.com/one"


def test_ask_returns_no_results_message_below_threshold(monkeypatch):
    client = make_client(monkeypatch)
    monkeypatch.setattr(app_module, "MIN_SIMILARITY", 2.0)
    response = client.post("/ask", json={"question": "an obscure topic"})
    assert response.status_code == 200
    body = response.json()
    assert body["groups"] == []
    assert "haven't written" in body["message"]


def test_ask_rejects_empty_question(monkeypatch):
    client = make_client(monkeypatch)
    response = client.post("/ask", json={"question": "   "})
    body = response.json()
    assert body["error"] == "empty_question"


def test_ask_enforces_rate_limit(monkeypatch):
    client = make_client(monkeypatch)
    app_module.rate_limiter = app_module.RateLimiter(max_requests=1, window_seconds=3600)
    first = client.post("/ask", json={"question": "rent control"})
    second = client.post("/ask", json={"question": "rent control again"})
    assert first.status_code == 200
    assert second.json()["error"] == "rate_limited"


def test_ask_uses_cache_for_repeated_question(monkeypatch):
    client = make_client(monkeypatch)
    calls = []
    monkeypatch.setattr(
        app_module,
        "generate_connector",
        lambda author, question, excerpts: calls.append(author) or "x",
    )
    client.post("/ask", json={"question": "rent control"})
    client.post("/ask", json={"question": "rent control"})
    assert len(calls) == 2
