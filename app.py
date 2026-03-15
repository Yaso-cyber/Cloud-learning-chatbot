"""
Cloud Learning Chatbot — Flask backend.

Provides a single-page chat UI and a /chat API endpoint that forwards
messages to OpenAI with a cloud/security/GRC-focused system prompt.
"""

import os

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
client = OpenAI(api_key=_api_key) if _api_key else None

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the chat interface."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    Accept a JSON body ``{"messages": [...]}`` where each element is
    ``{"role": "user"|"assistant", "content": "..."}`` and return the
    assistant's next reply as ``{"reply": "..."}``.
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

    # Prepend the system prompt so the model always has context
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_messages

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
        return jsonify({"error": str(exc)}), 500


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
