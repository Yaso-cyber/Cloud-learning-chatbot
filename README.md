# ☁️ CloudGuide — Cloud Learning Chatbot

An AI-powered, beginner-friendly chatbot that helps you learn **Cloud
Computing**, **Cloud Security**, and **GRC (Governance, Risk &
Compliance)** through natural conversation, quizzes, notes, PDF summaries,
and personalised weekly learning plans.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Chat Q&A** | GPT-powered answers focused on Cloud, Cloud Security, and GRC |
| **Analogy mode** | Toggle to receive beginner-friendly analogies for complex topics |
| **Knowledge Quiz** | 5 categories (Networking, Cybersecurity, Cryptography, Cloud Computing, GRC) — random or targeted |
| **Score tracking** | Live progress bar and score display during quizzes |
| **Notes management** | Create, edit, delete, and filter notes by topic — persisted in SQLite |
| **PDF Summariser** | Upload a PDF and receive an AI-generated plain-English summary |
| **Weekly Learning Plan** | AI-generated 7-day plan (≥ 5 active days) with progress tracking |
| **Beginner-friendly UI** | Multi-panel web interface accessible from any browser |

---

## 🗂 Project Structure

```
Cloud-learning-chatbot/
├── app.py                  # Flask backend — all routes
├── quiz_database.json      # Quiz questions across 5 categories
├── sample_qa.json          # Sample Q&A pairs used as context examples
├── templates/
│   └── index.html          # Single-page multi-panel UI
├── static/
│   ├── style.css           # Styling
│   └── script.js           # Frontend logic (chat, quiz, notes, upload, plan)
├── tests/
│   ├── test_app.py         # Chat endpoint tests (OpenAI mocked)
│   ├── test_quiz.py        # Quiz endpoint tests
│   └── test_notes.py       # Notes CRUD + persistence tests
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image
├── Procfile                # Heroku process file
├── .env.example            # Template for environment variables
└── .gitignore
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 2. Clone & install

```bash
git clone https://github.com/Yaso-cyber/Cloud-learning-chatbot.git
cd Cloud-learning-chatbot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up your API key

```bash
cp .env.example .env
# Open .env and replace "your_openai_api_key_here" with your real key
```

### 4. Run the app

```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000** and start learning! 🎉

---

## ⚙️ Configuration

All configuration is done via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model to use (e.g. `gpt-4o`, `gpt-3.5-turbo`) |
| `OPENAI_BASE_URL` | *(unset)* | Optional OpenAI-compatible endpoint (e.g. Google/Groq) |
| `SECRET_KEY` | `dev-secret-…` | Flask session secret — change for production |
| `NOTES_DB_PATH` | `notes.db` | Path for the SQLite notes database |
| `FLASK_DEBUG` | `0` | Set to `1` to enable debug mode (local dev only) |

### Use Google Gemini API Key (Optional)

If you want to use a Google Gemini key instead of OpenAI:

```env
OPENAI_API_KEY=your_google_ai_studio_key
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
OPENAI_MODEL=gemini-2.0-flash
```

Then restart the app (or redeploy on Render).

---

## 🧪 Running Tests

No API key is needed — the OpenAI client is mocked.

```bash
pytest tests/ -v
```

Run a specific test file:

```bash
pytest tests/test_quiz.py -v
pytest tests/test_notes.py -v
```

---

## 📡 API Endpoints

### Chat

**`POST /chat`** — Send a message and receive a reply.

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is the shared responsibility model?"}]}'
```

Enable analogy mode:

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Explain a firewall"}], "analogy": true}'
```

---

### Analogy Explanations

**`POST /explain`** — Get a standalone analogy-based explanation.

```bash
curl -X POST http://localhost:5000/explain \
  -H "Content-Type: application/json" \
  -d '{"concept": "zero-trust architecture"}'
```

---

### Quiz

**`GET /quiz/categories`** — List available quiz categories.

```bash
curl http://localhost:5000/quiz/categories
```

**`POST /quiz/start`** — Start a new quiz session.

```bash
# Category quiz
curl -X POST http://localhost:5000/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"category": "networking"}'

# Random mixed quiz
curl -X POST http://localhost:5000/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"category": "random"}'
```

**`GET /quiz/question?session_id=<id>`** — Get the current question.

```bash
curl "http://localhost:5000/quiz/question?session_id=YOUR_SESSION_ID"
```

**`POST /quiz/answer`** — Submit an answer.

```bash
curl -X POST http://localhost:5000/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_SESSION_ID", "answer": "A"}'
```

**`GET /quiz/score?session_id=<id>`** — Get the current score.

```bash
curl "http://localhost:5000/quiz/score?session_id=YOUR_SESSION_ID"
```

---

### Notes

**`GET /notes`** — List all notes (optionally filter by topic).

```bash
curl http://localhost:5000/notes
curl "http://localhost:5000/notes?topic=Networking"
```

**`POST /notes`** — Create a new note.

```bash
curl -X POST http://localhost:5000/notes \
  -H "Content-Type: application/json" \
  -d '{"topic": "Networking", "content": "The OSI model has 7 layers."}'
```

**`GET /notes/<id>`** — Retrieve a note by ID.

```bash
curl http://localhost:5000/notes/NOTE_ID
```

**`PUT /notes/<id>`** — Update a note.

```bash
curl -X PUT http://localhost:5000/notes/NOTE_ID \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated note content."}'
```

**`DELETE /notes/<id>`** — Delete a note.

```bash
curl -X DELETE http://localhost:5000/notes/NOTE_ID
```

---

### PDF Upload & Summarisation

**`POST /upload`** — Upload a PDF and receive a summary.

```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@/path/to/your/document.pdf"
```

---

### Weekly Learning Plan

**`POST /learning-plan`** — Generate a new weekly plan.

```bash
curl -X POST http://localhost:5000/learning-plan \
  -H "Content-Type: application/json" \
  -d '{"focus": "cloud security", "level": "beginner"}'
```

**`GET /learning-plan/<id>`** — Retrieve a previously generated plan.

```bash
curl http://localhost:5000/learning-plan/PLAN_ID
```

**`PUT /learning-plan/<id>/progress`** — Mark a day as complete.

```bash
curl -X PUT http://localhost:5000/learning-plan/PLAN_ID/progress \
  -H "Content-Type: application/json" \
  -d '{"day": "Monday", "completed": true}'
```

---

### Health

**`GET /health`** — Liveness probe.

```bash
curl http://localhost:5000/health
```

---

## 💡 Example Questions

- *"What is cloud computing and why does it matter?"*
- *"Explain the shared responsibility model with an example."*
- *"What is IAM and how do I secure it in AWS?"*
- *"What does a GRC analyst do day-to-day?"*
- *"How do I start preparing for the AWS Security Specialty exam?"*
- *"What are the key controls in ISO 27001?"*
- *"Explain zero-trust architecture using an analogy."*

---

## 🐳 Docker

```bash
# Build
docker build -t cloudguide .

# Run (set your API key)
docker run -p 5000:5000 -e OPENAI_API_KEY=your_key cloudguide
```

---

## ☁️ Deploy to Render

### Option A: Blueprint (recommended)

This repo includes a `render.yaml` file for one-click setup.

1. Push your latest code to GitHub.
2. In Render, click **New +** → **Blueprint**.
3. Select this GitHub repository.
4. When prompted for environment values, set:
  - `OPENAI_API_KEY` = your real key
  - `OPENAI_MODEL` = `gpt-4o-mini` (or your preferred model)
  - `FLASK_DEBUG` = `0`
5. Deploy and open your public Render URL.

### Option B: Manual Web Service

1. In Render, click **New +** → **Web Service**.
2. Connect this repository.
3. Set:
  - **Runtime**: Python
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `gunicorn app:app`
  - **Health Check Path**: `/health`
4. Add environment variables:
  - `OPENAI_API_KEY` = your real key
  - `OPENAI_MODEL` = `gpt-4o-mini`
  - `SECRET_KEY` = any long random string
  - `FLASK_DEBUG` = `0`
5. Deploy and share the Render URL (not localhost).

---

## ☁️ Deploy to Heroku

```bash
heroku create your-app-name
heroku config:set OPENAI_API_KEY=your_key
git push heroku main
heroku open
```

---

## 🔒 Security Notes

- Your `.env` file is git-ignored — **never commit your API key**.
- The app is for local/educational use. For production deployments use a
  proper WSGI server (e.g. Gunicorn) behind HTTPS.
- Notes are stored in SQLite locally and are never sent to external services.
- PDF text is sent to the OpenAI API for summarisation; do not upload
  confidential documents.

---

## 📄 License

MIT
