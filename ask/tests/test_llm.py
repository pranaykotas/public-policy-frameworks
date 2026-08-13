from unittest.mock import Mock

import pytest

from ask import llm


def test_generate_connector_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "")
    result = llm.generate_connector("Pranay", "what about rent control?", ["excerpt one"])
    assert result is None


def test_generate_connector_returns_stripped_content_on_success(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "fake-key")

    fake_response = Mock()
    fake_response.raise_for_status = Mock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "  Pranay has argued rent control backfires.  "}}]
    }

    def fake_post(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(llm.requests, "post", fake_post)

    result = llm.generate_connector("Pranay", "what about rent control?", ["excerpt one"])
    assert result == "Pranay has argued rent control backfires."


def test_generate_connector_returns_none_on_request_exception(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "fake-key")

    def fake_post(*args, **kwargs):
        raise llm.requests.RequestException("network error")

    monkeypatch.setattr(llm.requests, "post", fake_post)

    result = llm.generate_connector("Pranay", "what about rent control?", ["excerpt one"])
    assert result is None


def test_generate_connector_does_not_call_api_without_key(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("requests.post should not be called without an API key")

    monkeypatch.setattr(llm.requests, "post", fail_if_called)

    llm.generate_connector("RSJ", "what about rent control?", ["excerpt one"])
