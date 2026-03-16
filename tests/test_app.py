"""
Unit tests for the CloudGuide Flask application.

These tests use pytest-flask and mock out the OpenAI client so no real
API key is needed to run the suite.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_client():
    """Create a Flask test client with a dummy API key set."""
    mock_client = MagicMock()
    mock_choice  = MagicMock()
    mock_choice.message.content = "Test reply from CloudGuide."
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[mock_choice]
    )

    import app as flask_app
    flask_app.client = mock_client
    flask_app.app.config["TESTING"] = True

    with flask_app.app.test_client() as client:
        yield client, mock_client


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self, app_client):
        client, _ = app_client
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Index route
# ---------------------------------------------------------------------------

class TestIndex:
    def test_index_returns_html(self, app_client):
        client, _ = app_client
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"CloudGuide" in resp.data
        assert b"text/html" in resp.content_type.encode()

    def test_index_contains_topic_pills(self, app_client):
        client, _ = app_client
        resp = client.get("/")
        assert b"topic-pill" in resp.data

    def test_index_loads_static_assets(self, app_client):
        client, _ = app_client
        resp = client.get("/")
        assert b"style.css" in resp.data
        assert b"script.js" in resp.data


# ---------------------------------------------------------------------------
# /chat endpoint — happy path
# ---------------------------------------------------------------------------

class TestChatHappyPath:
    def test_returns_reply(self, app_client):
        client, _ = app_client
        payload = {"messages": [{"role": "user", "content": "What is cloud computing?"}]}
        resp = client.post("/chat", json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reply" in data
        assert data["reply"] == "Test reply from CloudGuide."

    def test_system_prompt_prepended(self, app_client):
        """The system message must always be the first element sent to OpenAI."""
        client, mock_openai = app_client
        payload = {"messages": [{"role": "user", "content": "Tell me about IAM."}]}
        client.post("/chat", json=payload)

        call_kwargs = mock_openai.chat.completions.create.call_args
        messages_sent = call_kwargs[1]["messages"]
        assert messages_sent[0]["role"] == "system"

    def test_user_history_forwarded(self, app_client):
        """All user-provided messages must be forwarded to OpenAI."""
        client, mock_openai = app_client
        history = [
            {"role": "user",      "content": "What is IaaS?"},
            {"role": "assistant", "content": "IaaS stands for ..."},
            {"role": "user",      "content": "And PaaS?"},
        ]
        client.post("/chat", json={"messages": history})

        call_kwargs = mock_openai.chat.completions.create.call_args
        messages_sent = call_kwargs[1]["messages"]
        # system + 3 history messages
        assert len(messages_sent) == 4

    def test_analogy_mode_uses_analogy_prompt(self, app_client):
        """When analogy=true, the analogy system prompt should be used."""
        client, mock_openai = app_client
        payload = {
            "messages": [{"role": "user", "content": "Explain a firewall."}],
            "analogy": True,
        }
        client.post("/chat", json=payload)

        call_kwargs = mock_openai.chat.completions.create.call_args
        messages_sent = call_kwargs[1]["messages"]
        assert messages_sent[0]["role"] == "system"
        # The analogy prompt mentions 'analogy'
        assert "analogy" in messages_sent[0]["content"].lower()


# ---------------------------------------------------------------------------
# /chat endpoint — error cases
# ---------------------------------------------------------------------------

class TestChatErrors:
    def test_missing_messages_key(self, app_client):
        client, _ = app_client
        resp = client.post("/chat", json={"text": "hello"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_empty_body(self, app_client):
        client, _ = app_client
        resp = client.post("/chat", data="not json",
                           content_type="text/plain")
        assert resp.status_code == 400

    def test_empty_messages_list(self, app_client):
        client, _ = app_client
        resp = client.post("/chat", json={"messages": []})
        assert resp.status_code == 400

    def test_no_api_key_configured(self, app_client):
        """When client is None (no API key), /chat should return 500."""
        client, _ = app_client
        import app as flask_app
        original = flask_app.client
        try:
            flask_app.client = None
            resp = client.post("/chat",
                               json={"messages": [{"role": "user", "content": "hi"}]})
            assert resp.status_code == 500
            assert "error" in resp.get_json()
        finally:
            flask_app.client = original

    def test_openai_exception_returns_500(self, app_client):
        """OpenAI SDK exceptions should surface as a 500 with an error message."""
        client, mock_openai = app_client
        mock_openai.chat.completions.create.side_effect = RuntimeError("API down")
        resp = client.post("/chat",
                           json={"messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["error"] == (
            "The AI service is temporarily unavailable. "
            "Please try again in a moment."
        )
