# ☁️ CloudGuide — Cloud Learning Chatbot

An AI-powered, beginner-friendly chatbot that helps you learn **Cloud
Computing**, **Cloud Security**, and **GRC (Governance, Risk &
Compliance)** through natural conversation.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Cloud topics** | IaaS / PaaS / SaaS, AWS / Azure / GCP, storage, compute, networking, containers, serverless |
| **Cloud Security** | IAM, shared-responsibility model, zero-trust, encryption, common threats |
| **GRC** | NIST CSF, ISO 27001, SOC 2, PCI-DSS, HIPAA, CIS Benchmarks, risk assessment, audit prep |
| **Beginner-friendly UI** | Clean chat interface with quick-start topic buttons |
| **Full conversation memory** | The whole chat history is sent on every turn so answers stay in context |

---

## 🗂 Project Structure

```
Cloud-learning-chatbot/
├── app.py               # Flask backend + OpenAI integration
├── templates/
│   └── index.html       # Single-page chat UI
├── static/
│   ├── style.css        # Styling
│   └── script.js        # Frontend chat logic
├── tests/
│   └── test_app.py      # Pytest test suite (no API key needed)
├── requirements.txt     # Python dependencies
├── .env.example         # Template for your environment variables
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

Open your browser at **http://127.0.0.1:5000** and start chatting! 🎉

---

## ⚙️ Configuration

All configuration is done via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model to use (e.g. `gpt-4o`, `gpt-3.5-turbo`) |
| `SECRET_KEY` | `dev-secret-…` | Flask session secret — change for production |

---

## 🧪 Running Tests

No API key is needed for the tests — the OpenAI client is mocked.

```bash
pytest tests/ -v
```

---

## 💡 Example Questions

- *"What is cloud computing and why does it matter?"*
- *"Explain the shared responsibility model with an example."*
- *"What is IAM and how do I secure it in AWS?"*
- *"What does a GRC analyst do day-to-day?"*
- *"How do I start preparing for the AWS Security Specialty exam?"*
- *"What are the key controls in ISO 27001?"*

---

## 🔒 Security Notes

- Your `.env` file is git-ignored — **never commit your API key**.
- The app is for local/educational use. For production deployments use a
  proper WSGI server (e.g. Gunicorn) behind HTTPS.

---

## 📄 License

MIT
