"""
Cloud Learning Chatbot — Flask backend.

Provides a chat UI and REST API endpoints for:
  - /chat          : Q&A via AI (Google Gemini / OpenAI-compatible)
  - /explain       : Analogy-based explanations
  - /quiz/*        : Quiz with categories and score tracking
  - /notes/*       : CRUD notes management (SQLite)
  - /upload        : PDF upload and summarization
  - /learning-plan : Weekly learning plan generation
  - /health        : Liveness probe
"""

import io
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

# ---------------------------------------------------------------------------
# OpenAI client — instantiated once at startup
# ---------------------------------------------------------------------------
_api_key = os.getenv("OPENAI_API_KEY", "")
_base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
client = OpenAI(api_key=_api_key, base_url=_base_url) if _api_key else None

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUIZ_DB_PATH = os.path.join(BASE_DIR, "quiz_database.json")
SAMPLE_QA_PATH = os.path.join(BASE_DIR, "sample_qa.json")
NOTES_DB_PATH = os.getenv("NOTES_DB_PATH", os.path.join(BASE_DIR, "notes.db"))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Load quiz database
# ---------------------------------------------------------------------------
with open(QUIZ_DB_PATH, "r", encoding="utf-8") as _f:
    QUIZ_DATABASE: dict = json.load(_f)

# ---------------------------------------------------------------------------
# In-memory quiz sessions: {session_id: {"category": ..., "questions": [...],
#                            "current": int, "correct": int, "total": int}}
# ---------------------------------------------------------------------------
_quiz_sessions: dict = {}

# ---------------------------------------------------------------------------
# System prompt: focus the assistant on cloud, cloud security, and GRC
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are CloudGuide, a friendly and knowledgeable AI assistant
specialized in helping beginners learn about:

1. **Cloud Computing** — core concepts (IaaS, PaaS, SaaS), the main providers
   (AWS, Microsoft Azure, Google Cloud), storage, compute, networking,
   serverless, containers, and DevOps on the cloud.

2. **Cloud Security** — identity and access management (IAM), data encryption,
   network security groups, shared-responsibility model, common cloud threats
   (misconfigurations, data breaches, insider threats), zero-trust architecture,
   and cloud security best practices.

3. **GRC (Governance, Risk and Compliance)** — frameworks such as NIST CSF,
   ISO 27001, SOC 2, PCI-DSS, HIPAA, CIS Benchmarks, and how they apply to
   cloud environments; risk assessment, audit readiness, policy writing, and
   compliance automation tools.

Guidelines:
- Always explain concepts in plain, beginner-friendly language.
- Use bullet points, numbered lists, or short paragraphs to keep answers easy
  to read.
- Provide real-world examples and analogies wherever helpful.
- If asked about something outside cloud, cloud security, or GRC, politely
  redirect the conversation back to those topics.
- Encourage the learner and remind them that everyone starts as a beginner.
"""

ANALOGY_SYSTEM_PROMPT = """You are CloudGuide, an expert at explaining technical
concepts in cloud computing, cloud security, and GRC using simple, relatable
analogies.

When asked to explain a concept:
1. Start with a clear one-sentence analogy that a complete beginner would understand.
2. Use everyday objects or situations (e.g., locks, post offices, nightclubs) to
   illustrate the concept.
3. After the analogy, give a brief plain-English explanation of what the concept
   actually does in practice.
4. Keep the entire response short — 3 to 6 sentences maximum.
5. End with one practical takeaway the learner should remember.
"""

# ---------------------------------------------------------------------------
# SQLite helper for notes
# ---------------------------------------------------------------------------

def _get_notes_db() -> sqlite3.Connection:
    """Return a SQLite connection, creating the notes table if needed."""
    conn = sqlite3.connect(NOTES_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id        TEXT PRIMARY KEY,
            topic     TEXT NOT NULL,
            content   TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ---------------------------------------------------------------------------
# Helper — translate raw API errors into user-friendly messages
# ---------------------------------------------------------------------------

def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "insufficient_quota" in msg or "RESOURCE_EXHAUSTED" in msg or "429" in msg:
        return ("The AI service has reached its free-tier usage limit for today. "
                "Please try again tomorrow — limits reset daily. "
                "If you are the site owner, check your API quota at https://ai.dev/rate-limit")
    if "invalid_api_key" in msg or "401" in msg:
        return "The AI service is not configured correctly. Please contact the site owner."
    if "404" in msg or "NOT_FOUND" in msg:
        return "The AI model could not be found. Please contact the site owner."
    return "The AI service is temporarily unavailable. Please try again in a moment."


# ---------------------------------------------------------------------------
# Routes — UI
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the chat interface."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Routes — Chat
# ---------------------------------------------------------------------------

@app.route("/chat", methods=["POST"])
def chat():
    """
    Accept ``{"messages": [...], "analogy": false}`` and return
    ``{"reply": "..."}``.

    Set ``"analogy": true`` to receive an analogy-based explanation instead
    of a standard answer.
    """
    if client is None:
        return jsonify({"error": "OPENAI_API_KEY is not configured. "
                                 "Please add it to your .env file."}), 500

    data = request.get_json(silent=True)
    if not data or "messages" not in data:
        return jsonify({"error": "Request body must be JSON with a "
                                 "'messages' array."}), 400

    user_messages = data["messages"]
    if not isinstance(user_messages, list) or len(user_messages) == 0:
        return jsonify({"error": "'messages' must be a non-empty array."}), 400

    use_analogy = bool(data.get("analogy", False))
    system = ANALOGY_SYSTEM_PROMPT if use_analogy else SYSTEM_PROMPT

    # Prepend the system prompt so the model always has context
    messages = [{"role": "system", "content": system}] + user_messages

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": _friendly_error(exc)}), 500


# ---------------------------------------------------------------------------
# Routes — Analogy Explanations
# ---------------------------------------------------------------------------

@app.route("/explain", methods=["POST"])
def explain():
    """
    Generate an analogy-based explanation for a technical concept.

    Request body: ``{"concept": "firewall"}``
    Response:     ``{"explanation": "..."}``
    """
    if client is None:
        return jsonify({"error": "OPENAI_API_KEY is not configured."}), 500

    data = request.get_json(silent=True)
    if not data or not data.get("concept", "").strip():
        return jsonify({"error": "Request body must be JSON with a non-empty "
                                 "'concept' field."}), 400

    concept = data["concept"].strip()
    messages = [
        {"role": "system", "content": ANALOGY_SYSTEM_PROMPT},
        {"role": "user",   "content": f"Explain '{concept}' using a simple analogy."},
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )
        explanation = response.choices[0].message.content
        return jsonify({"concept": concept, "explanation": explanation})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": _friendly_error(exc)}), 500


# ---------------------------------------------------------------------------
# Routes — Quiz
# ---------------------------------------------------------------------------

@app.route("/quiz/categories", methods=["GET"])
def quiz_categories():
    """Return the list of available quiz categories."""
    categories = list(QUIZ_DATABASE.keys())
    return jsonify({"categories": categories})


@app.route("/quiz/start", methods=["POST"])
def quiz_start():
    """
    Start a new quiz session.

    Request body: ``{"category": "networking"}``  (or ``"random"`` for a
    mixed quiz drawn from all categories).

    Response: ``{"session_id": "...", "total_questions": N, "category": "..."}``
    """
    import random

    data = request.get_json(silent=True) or {}
    category = data.get("category", "random").lower().strip()

    if category == "random":
        all_questions = [q for qs in QUIZ_DATABASE.values() for q in qs]
        questions = random.sample(all_questions, min(10, len(all_questions)))
    elif category in QUIZ_DATABASE:
        questions = list(QUIZ_DATABASE[category])
        random.shuffle(questions)
    else:
        valid = list(QUIZ_DATABASE.keys()) + ["random"]
        return jsonify({"error": f"Unknown category '{category}'. "
                                  f"Valid values: {valid}"}), 400

    session_id = str(uuid.uuid4())
    _quiz_sessions[session_id] = {
        "category": category,
        "questions": questions,
        "current": 0,
        "correct": 0,
        "total": len(questions),
    }

    return jsonify({
        "session_id": session_id,
        "category": category,
        "total_questions": len(questions),
    }), 201


@app.route("/quiz/question", methods=["GET"])
def quiz_question():
    """
    Return the current question for a session.

    Query parameter: ``?session_id=<id>``

    Response: ``{"question_number": N, "total": M, "id": "...", "question": "...",
                 "options": [...]}``
    or ``{"finished": true, "score": ..., "total": ..., "percentage": ...}``
    when the quiz is complete.
    """
    session_id = request.args.get("session_id", "").strip()
    session = _quiz_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found. Start a new quiz with "
                                  "POST /quiz/start."}), 404

    current = session["current"]
    if current >= session["total"]:
        pct = round(session["correct"] / session["total"] * 100) if session["total"] else 0
        return jsonify({
            "finished": True,
            "score": session["correct"],
            "total": session["total"],
            "percentage": pct,
        })

    q = session["questions"][current]
    return jsonify({
        "question_number": current + 1,
        "total": session["total"],
        "id": q["id"],
        "question": q["question"],
        "options": q["options"],
    })


@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    """
    Submit an answer for the current question.

    Request body: ``{"session_id": "...", "answer": "A"}``

    Response: ``{"correct": true/false, "correct_answer": "A",
                 "explanation": "...", "score": N, "question_number": N,
                 "total": M}``
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    session_id = data.get("session_id", "").strip()
    submitted = data.get("answer", "").strip().upper()

    session = _quiz_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    current = session["current"]
    if current >= session["total"]:
        return jsonify({"error": "Quiz is already finished."}), 400

    if not submitted:
        return jsonify({"error": "'answer' field is required."}), 400

    q = session["questions"][current]
    is_correct = submitted == q["answer"].upper()
    if is_correct:
        session["correct"] += 1
    session["current"] += 1

    return jsonify({
        "correct": is_correct,
        "correct_answer": q["answer"],
        "explanation": q["explanation"],
        "score": session["correct"],
        "question_number": current + 1,
        "total": session["total"],
    })


@app.route("/quiz/score", methods=["GET"])
def quiz_score():
    """
    Return the current score for a session.

    Query parameter: ``?session_id=<id>``
    """
    session_id = request.args.get("session_id", "").strip()
    session = _quiz_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found."}), 404

    pct = round(session["correct"] / session["total"] * 100) if session["total"] else 0
    return jsonify({
        "session_id": session_id,
        "category": session["category"],
        "score": session["correct"],
        "total": session["total"],
        "questions_answered": session["current"],
        "percentage": pct,
        "finished": session["current"] >= session["total"],
    })


# ---------------------------------------------------------------------------
# Routes — Notes
# ---------------------------------------------------------------------------

@app.route("/notes", methods=["GET"])
def notes_list():
    """
    List all notes, optionally filtered by topic.

    Query parameter: ``?topic=<topic>`` (optional)
    """
    topic_filter = request.args.get("topic", "").strip()
    conn = _get_notes_db()
    try:
        if topic_filter:
            rows = conn.execute(
                "SELECT * FROM notes WHERE topic = ? ORDER BY updated_at DESC",
                (topic_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC"
            ).fetchall()
        return jsonify({"notes": [_row_to_dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/notes", methods=["POST"])
def notes_create():
    """
    Create a new note.

    Request body: ``{"topic": "networking", "content": "..."}``
    Response: ``{"note": {...}}``
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    topic = data.get("topic", "").strip()
    content = data.get("content", "").strip()

    if not topic:
        return jsonify({"error": "'topic' is required."}), 400
    if not content:
        return jsonify({"error": "'content' is required."}), 400

    now = datetime.now(timezone.utc).isoformat()
    note_id = str(uuid.uuid4())
    conn = _get_notes_db()
    try:
        conn.execute(
            "INSERT INTO notes (id, topic, content, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (note_id, topic, content, now, now),
        )
        conn.commit()
        return jsonify({
            "note": {
                "id": note_id,
                "topic": topic,
                "content": content,
                "created_at": now,
                "updated_at": now,
            }
        }), 201
    finally:
        conn.close()


@app.route("/notes/<note_id>", methods=["GET"])
def notes_get(note_id: str):
    """Retrieve a single note by ID."""
    conn = _get_notes_db()
    try:
        row = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Note not found."}), 404
        return jsonify({"note": _row_to_dict(row)})
    finally:
        conn.close()


@app.route("/notes/<note_id>", methods=["PUT"])
def notes_update(note_id: str):
    """
    Update an existing note.

    Request body: ``{"topic": "...", "content": "..."}``
    (either or both fields may be supplied)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    conn = _get_notes_db()
    try:
        row = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Note not found."}), 404

        note = _row_to_dict(row)
        topic = data.get("topic", note["topic"]).strip() or note["topic"]
        content = data.get("content", note["content"]).strip() or note["content"]
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            "UPDATE notes SET topic = ?, content = ?, updated_at = ? WHERE id = ?",
            (topic, content, now, note_id),
        )
        conn.commit()
        return jsonify({
            "note": {
                "id": note_id,
                "topic": topic,
                "content": content,
                "created_at": note["created_at"],
                "updated_at": now,
            }
        })
    finally:
        conn.close()


@app.route("/notes/<note_id>", methods=["DELETE"])
def notes_delete(note_id: str):
    """Delete a note by ID."""
    conn = _get_notes_db()
    try:
        row = conn.execute(
            "SELECT id FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Note not found."}), 404

        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        return jsonify({"message": "Note deleted successfully."})
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes — PDF Upload & Summarisation
# ---------------------------------------------------------------------------

@app.route("/upload", methods=["POST"])
def upload_pdf():
    """
    Upload a PDF file and receive a summary.

    Form data: ``file=<pdf file>``
    Response:  ``{"filename": "...", "summary": "...", "word_count": N}``
    """
    if client is None:
        return jsonify({"error": "OPENAI_API_KEY is not configured."}), 500

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request. "
                                  "Send a multipart/form-data request with a 'file' field."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"error": "No file selected."}), 400
    if not uploaded_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    try:
        import PyPDF2  # noqa: PLC0415
    except ImportError:
        return jsonify({"error": "PyPDF2 is not installed. "
                                  "Run: pip install PyPDF2"}), 500

    try:
        file_bytes = uploaded_file.read()
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
        extracted_text = "\n".join(text_parts).strip()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Failed to read PDF: {exc}"}), 422

    if not extracted_text:
        return jsonify({"error": "Could not extract any text from the PDF. "
                                  "The file may be image-based or encrypted."}), 422

    # Truncate to avoid huge token counts (keep ~6000 words)
    words = extracted_text.split()
    truncated = " ".join(words[:6000])
    was_truncated = len(words) > 6000

    summary_prompt = (
        "You are a helpful summariser. The following text was extracted from a PDF.\n"
        "Please provide a clear, structured summary in plain English, suitable for a beginner.\n"
        "Use bullet points or numbered sections where appropriate.\n\n"
        f"--- START OF DOCUMENT ---\n{truncated}\n--- END OF DOCUMENT ---"
    )
    if was_truncated:
        summary_prompt += "\n\n(Note: the document was truncated to the first 6,000 words.)"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
        summary = response.choices[0].message.content
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Summarisation failed: {exc}"}), 500

    return jsonify({
        "filename": uploaded_file.filename,
        "summary": summary,
        "word_count": len(words),
        "truncated": was_truncated,
    })


# ---------------------------------------------------------------------------
# Routes — Weekly Learning Plan
# ---------------------------------------------------------------------------

# In-memory store for plans: {plan_id: {plan data}}
_learning_plans: dict = {}


@app.route("/learning-plan", methods=["POST"])
def create_learning_plan():
    """
    Generate a weekly learning plan.

    Request body (optional): ``{"focus": "cloud security", "level": "beginner"}``
    Response: ``{"plan_id": "...", "plan": {...}}``
    """
    if client is None:
        return jsonify({"error": "OPENAI_API_KEY is not configured."}), 500

    data = request.get_json(silent=True) or {}
    focus = data.get("focus", "").strip()
    level = data.get("level", "beginner").strip()

    focus_text = f" with a focus on {focus}" if focus else ""
    prompt = (
        f"Create a 7-day weekly learning plan for a {level} studying cloud computing, "
        f"cloud security, and GRC{focus_text}.\n\n"
        "Requirements:\n"
        "- Include at least 5 active learning days (Monday–Friday minimum).\n"
        "- Each day should have: a topic, a brief description, 1-2 specific learning "
        "  activities (e.g., read a doc page, watch a video, do a hands-on lab), "
        "  and an estimated time in minutes.\n"
        "- Keep activities concrete and actionable.\n\n"
        "Return the response as valid JSON in this exact structure:\n"
        "{\n"
        '  "title": "Weekly Cloud Learning Plan",\n'
        '  "level": "beginner",\n'
        '  "focus": "...",\n'
        '  "days": [\n'
        '    {\n'
        '      "day": "Monday",\n'
        '      "topic": "...",\n'
        '      "description": "...",\n'
        '      "activities": ["...", "..."],\n'
        '      "estimated_minutes": 60\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        plan_data = json.loads(raw)
    except json.JSONDecodeError:
        # Return raw text wrapped in a simple structure
        plan_data = {"title": "Weekly Cloud Learning Plan", "raw": raw}
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": _friendly_error(exc)}), 500
    now = datetime.now(timezone.utc).isoformat()
    plan_record = {
        "plan_id": plan_id,
        "created_at": now,
        "focus": focus,
        "level": level,
        "progress": {},
        "plan": plan_data,
    }
    _learning_plans[plan_id] = plan_record

    return jsonify(plan_record), 201


@app.route("/learning-plan/<plan_id>", methods=["GET"])
def get_learning_plan(plan_id: str):
    """Retrieve a previously generated learning plan."""
    plan = _learning_plans.get(plan_id)
    if not plan:
        return jsonify({"error": "Plan not found."}), 404
    return jsonify(plan)


@app.route("/learning-plan/<plan_id>/progress", methods=["PUT"])
def update_learning_plan_progress(plan_id: str):
    """
    Update progress on a learning plan.

    Request body: ``{"day": "Monday", "completed": true}``
    Response: ``{"plan_id": "...", "progress": {"Monday": true, ...}}``
    """
    plan = _learning_plans.get(plan_id)
    if not plan:
        return jsonify({"error": "Plan not found."}), 404

    data = request.get_json(silent=True)
    if not data or "day" not in data:
        return jsonify({"error": "Request body must include 'day'."}), 400

    day = data["day"]
    completed = bool(data.get("completed", True))
    plan["progress"][day] = completed

    return jsonify({"plan_id": plan_id, "progress": plan["progress"]})


# ---------------------------------------------------------------------------
# Routes — Health
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    """Simple liveness probe."""
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug)
