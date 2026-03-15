"""
Tests for the quiz endpoints.

No real API key is needed — quiz functionality is purely data-driven.
"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    flask_app._quiz_sessions.clear()
    with flask_app.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# /quiz/categories
# ---------------------------------------------------------------------------

class TestQuizCategories:
    def test_returns_category_list(self, client):
        resp = client.get("/quiz/categories")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "categories" in data
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) >= 1

    def test_known_categories_present(self, client):
        resp = client.get("/quiz/categories")
        categories = resp.get_json()["categories"]
        for expected in ("networking", "cybersecurity", "cryptography"):
            assert expected in categories


# ---------------------------------------------------------------------------
# /quiz/start
# ---------------------------------------------------------------------------

class TestQuizStart:
    def test_start_random_quiz(self, client):
        resp = client.post("/quiz/start", json={"category": "random"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert "session_id" in data
        assert data["category"] == "random"
        assert data["total_questions"] > 0

    def test_start_category_quiz(self, client):
        resp = client.post("/quiz/start", json={"category": "networking"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["category"] == "networking"
        assert data["total_questions"] > 0

    def test_start_default_category(self, client):
        """Omitting category defaults to random."""
        resp = client.post("/quiz/start", json={})
        assert resp.status_code == 201
        assert resp.get_json()["category"] == "random"

    def test_start_unknown_category_returns_400(self, client):
        resp = client.post("/quiz/start", json={"category": "does-not-exist"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_each_start_creates_unique_session(self, client):
        r1 = client.post("/quiz/start", json={"category": "random"})
        r2 = client.post("/quiz/start", json={"category": "random"})
        assert r1.get_json()["session_id"] != r2.get_json()["session_id"]


# ---------------------------------------------------------------------------
# /quiz/question
# ---------------------------------------------------------------------------

class TestQuizQuestion:
    def _start(self, client, category="networking"):
        resp = client.post("/quiz/start", json={"category": category})
        return resp.get_json()["session_id"]

    def test_get_first_question(self, client):
        sid = self._start(client)
        resp = client.get(f"/quiz/question?session_id={sid}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "question" in data
        assert "options" in data
        assert data["question_number"] == 1

    def test_question_has_required_fields(self, client):
        sid = self._start(client)
        data = client.get(f"/quiz/question?session_id={sid}").get_json()
        for field in ("question_number", "total", "id", "question", "options"):
            assert field in data

    def test_missing_session_returns_404(self, client):
        resp = client.get("/quiz/question?session_id=nonexistent")
        assert resp.status_code == 404

    def test_empty_session_id_returns_404(self, client):
        resp = client.get("/quiz/question?session_id=")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /quiz/answer
# ---------------------------------------------------------------------------

class TestQuizAnswer:
    def _start(self, client, category="networking"):
        resp = client.post("/quiz/start", json={"category": category})
        return resp.get_json()["session_id"]

    def _get_correct_answer(self, client, session_id):
        """Return the correct letter for the current question by peeking at the DB."""
        import app as flask_app
        session = flask_app._quiz_sessions[session_id]
        current = session["current"]
        return session["questions"][current]["answer"].upper()

    def test_correct_answer(self, client):
        sid = self._start(client)
        correct = self._get_correct_answer(client, sid)
        resp = client.post("/quiz/answer", json={"session_id": sid, "answer": correct})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["correct"] is True
        assert data["score"] == 1

    def test_wrong_answer(self, client):
        sid = self._start(client)
        correct = self._get_correct_answer(client, sid)
        wrong = "B" if correct != "B" else "A"
        resp = client.post("/quiz/answer", json={"session_id": sid, "answer": wrong})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["correct"] is False
        assert data["score"] == 0

    def test_answer_increments_current(self, client):
        import app as flask_app
        sid = self._start(client)
        correct = self._get_correct_answer(client, sid)
        client.post("/quiz/answer", json={"session_id": sid, "answer": correct})
        assert flask_app._quiz_sessions[sid]["current"] == 1

    def test_answer_returns_explanation(self, client):
        sid = self._start(client)
        correct = self._get_correct_answer(client, sid)
        data = client.post("/quiz/answer",
                           json={"session_id": sid, "answer": correct}).get_json()
        assert "explanation" in data
        assert len(data["explanation"]) > 0

    def test_missing_session_returns_404(self, client):
        resp = client.post("/quiz/answer",
                           json={"session_id": "bad", "answer": "A"})
        assert resp.status_code == 404

    def test_missing_answer_returns_400(self, client):
        sid = self._start(client)
        resp = client.post("/quiz/answer", json={"session_id": sid})
        assert resp.status_code == 400

    def test_no_body_returns_400(self, client):
        resp = client.post("/quiz/answer",
                           data="not json", content_type="text/plain")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /quiz/score
# ---------------------------------------------------------------------------

class TestQuizScore:
    def test_score_after_correct_answer(self, client):
        import app as flask_app
        resp = client.post("/quiz/start", json={"category": "networking"})
        sid  = resp.get_json()["session_id"]
        correct = flask_app._quiz_sessions[sid]["questions"][0]["answer"].upper()
        client.post("/quiz/answer", json={"session_id": sid, "answer": correct})

        score_resp = client.get(f"/quiz/score?session_id={sid}")
        assert score_resp.status_code == 200
        data = score_resp.get_json()
        assert data["score"] == 1
        assert data["questions_answered"] == 1
        assert data["finished"] is False

    def test_score_missing_session_returns_404(self, client):
        resp = client.get("/quiz/score?session_id=bad")
        assert resp.status_code == 404

    def test_score_shows_percentage(self, client):
        import app as flask_app
        resp = client.post("/quiz/start", json={"category": "networking"})
        sid  = resp.get_json()["session_id"]
        total = flask_app._quiz_sessions[sid]["total"]
        # Answer all questions correctly
        for _ in range(total):
            correct = flask_app._quiz_sessions[sid]["questions"][
                flask_app._quiz_sessions[sid]["current"]
            ]["answer"].upper()
            client.post("/quiz/answer", json={"session_id": sid, "answer": correct})

        data = client.get(f"/quiz/score?session_id={sid}").get_json()
        assert data["percentage"] == 100
        assert data["finished"] is True
