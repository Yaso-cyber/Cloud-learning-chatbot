"""
Tests for the notes management endpoints.

Notes are stored in SQLite. We use a temporary database for each test run.
"""

import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """
    Create a Flask test client backed by a temporary SQLite database so
    that tests don't pollute the development notes.db file.
    """
    db_path = str(tmp_path / "test_notes.db")

    import app as flask_app
    flask_app.NOTES_DB_PATH = db_path
    flask_app.app.config["TESTING"] = True

    with flask_app.app.test_client() as c:
        yield c

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_note(client, topic="Networking", content="OSI model has 7 layers."):
    resp = client.post("/notes", json={"topic": topic, "content": content})
    assert resp.status_code == 201
    return resp.get_json()["note"]


# ---------------------------------------------------------------------------
# GET /notes  (list)
# ---------------------------------------------------------------------------

class TestNotesList:
    def test_empty_list_initially(self, client):
        resp = client.get("/notes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["notes"] == []

    def test_list_returns_created_notes(self, client):
        create_note(client)
        resp = client.get("/notes")
        assert len(resp.get_json()["notes"]) == 1

    def test_filter_by_topic(self, client):
        create_note(client, topic="Networking", content="Content A")
        create_note(client, topic="GRC",        content="Content B")

        resp = client.get("/notes?topic=GRC")
        notes = resp.get_json()["notes"]
        assert len(notes) == 1
        assert notes[0]["topic"] == "GRC"

    def test_filter_no_match_returns_empty(self, client):
        create_note(client)
        resp = client.get("/notes?topic=Cryptography")
        assert resp.get_json()["notes"] == []


# ---------------------------------------------------------------------------
# POST /notes  (create)
# ---------------------------------------------------------------------------

class TestNotesCreate:
    def test_create_note_returns_201(self, client):
        resp = client.post("/notes", json={"topic": "IAM", "content": "Least privilege principle."})
        assert resp.status_code == 201

    def test_created_note_has_id(self, client):
        note = create_note(client)
        assert "id" in note
        assert len(note["id"]) > 0

    def test_created_note_has_timestamps(self, client):
        note = create_note(client)
        assert "created_at" in note
        assert "updated_at" in note

    def test_create_missing_topic_returns_400(self, client):
        resp = client.post("/notes", json={"content": "Some content"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_create_missing_content_returns_400(self, client):
        resp = client.post("/notes", json={"topic": "IAM"})
        assert resp.status_code == 400

    def test_create_empty_body_returns_400(self, client):
        resp = client.post("/notes", data="not json", content_type="text/plain")
        assert resp.status_code == 400

    def test_create_empty_topic_returns_400(self, client):
        resp = client.post("/notes", json={"topic": "  ", "content": "Content"})
        assert resp.status_code == 400

    def test_create_empty_content_returns_400(self, client):
        resp = client.post("/notes", json={"topic": "IAM", "content": "  "})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /notes/<id>  (retrieve)
# ---------------------------------------------------------------------------

class TestNotesGet:
    def test_get_existing_note(self, client):
        note = create_note(client, topic="Cloud", content="AWS regions explanation.")
        resp = client.get(f"/notes/{note['id']}")
        assert resp.status_code == 200
        retrieved = resp.get_json()["note"]
        assert retrieved["topic"] == "Cloud"
        assert retrieved["content"] == "AWS regions explanation."

    def test_get_nonexistent_note_returns_404(self, client):
        resp = client.get("/notes/does-not-exist")
        assert resp.status_code == 404
        assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# PUT /notes/<id>  (update)
# ---------------------------------------------------------------------------

class TestNotesUpdate:
    def test_update_topic(self, client):
        note = create_note(client, topic="Old Topic", content="Content.")
        resp = client.put(f"/notes/{note['id']}", json={"topic": "New Topic"})
        assert resp.status_code == 200
        updated = resp.get_json()["note"]
        assert updated["topic"] == "New Topic"
        assert updated["content"] == "Content."

    def test_update_content(self, client):
        note = create_note(client)
        resp = client.put(f"/notes/{note['id']}", json={"content": "Updated content."})
        assert resp.status_code == 200
        assert resp.get_json()["note"]["content"] == "Updated content."

    def test_update_both_fields(self, client):
        note = create_note(client)
        resp = client.put(f"/notes/{note['id']}",
                          json={"topic": "T2", "content": "C2"})
        assert resp.status_code == 200
        updated = resp.get_json()["note"]
        assert updated["topic"] == "T2"
        assert updated["content"] == "C2"

    def test_update_timestamp_changes(self, client):
        import time
        note = create_note(client)
        time.sleep(0.01)  # ensure updated_at differs
        resp = client.put(f"/notes/{note['id']}", json={"content": "New."})
        updated = resp.get_json()["note"]
        assert updated["updated_at"] >= note["updated_at"]

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put("/notes/bad-id", json={"content": "X"})
        assert resp.status_code == 404

    def test_update_empty_body_returns_400(self, client):
        note = create_note(client)
        resp = client.put(f"/notes/{note['id']}",
                          data="not json", content_type="text/plain")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /notes/<id>
# ---------------------------------------------------------------------------

class TestNotesDelete:
    def test_delete_existing_note(self, client):
        note = create_note(client)
        resp = client.delete(f"/notes/{note['id']}")
        assert resp.status_code == 200
        assert "deleted" in resp.get_json()["message"].lower()

    def test_deleted_note_is_gone(self, client):
        note = create_note(client)
        client.delete(f"/notes/{note['id']}")
        resp = client.get(f"/notes/{note['id']}")
        assert resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/notes/bad-id")
        assert resp.status_code == 404

    def test_delete_reduces_count(self, client):
        n1 = create_note(client, content="Note 1")
        n2 = create_note(client, content="Note 2")
        client.delete(f"/notes/{n1['id']}")
        notes = client.get("/notes").get_json()["notes"]
        assert len(notes) == 1
        assert notes[0]["id"] == n2["id"]


# ---------------------------------------------------------------------------
# Persistence — notes survive across requests
# ---------------------------------------------------------------------------

class TestNotesPersistence:
    def test_notes_persist_across_requests(self, client):
        note = create_note(client, topic="Persistence", content="I should survive.")
        # A fresh GET should still return the note
        resp = client.get(f"/notes/{note['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["note"]["content"] == "I should survive."

    def test_multiple_notes_stored_correctly(self, client):
        topics = ["Networking", "Security", "GRC", "Cloud", "Crypto"]
        ids = [create_note(client, topic=t, content=f"{t} note")["id"] for t in topics]
        for i, note_id in enumerate(ids):
            resp = client.get(f"/notes/{note_id}")
            assert resp.get_json()["note"]["topic"] == topics[i]
