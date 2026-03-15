/**
 * CloudGuide — frontend chat logic
 *
 * Maintains a local copy of the conversation history and sends the full
 * history to /chat on each message so the assistant has context.
 */

(function () {
  "use strict";

  // ── DOM refs ───────────────────────────────────────────────────────────
  const chatContainer = document.getElementById("chat-container");
  const inputForm     = document.getElementById("input-form");
  const userInput     = document.getElementById("user-input");
  const sendBtn       = document.getElementById("send-btn");
  const topicPills    = document.querySelectorAll(".topic-pill");

  // ── Conversation history (sent to the server on each turn) ─────────────
  /** @type {{ role: "user"|"assistant", content: string }[]} */
  const history = [];

  // ── Greeting ───────────────────────────────────────────────────────────
  appendBotMessage(
    "👋 Hi! I'm **CloudGuide**, your AI learning companion for Cloud, " +
    "Cloud Security, and GRC.\n\n" +
    "Ask me anything — like *\"What is IaaS?\"* or " +
    "*\"How do I start preparing for a cloud security role?\"* — " +
    "or click one of the topic buttons above to get started!"
  );

  // ── Auto-resize textarea ───────────────────────────────────────────────
  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 128) + "px";
  });

  // ── Send on Enter (Shift+Enter = newline) ──────────────────────────────
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitMessage();
    }
  });

  // ── Form submit ────────────────────────────────────────────────────────
  inputForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitMessage();
  });

  // ── Topic pill clicks ──────────────────────────────────────────────────
  topicPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      const prompt = pill.dataset.prompt;
      if (prompt) {
        userInput.value = prompt;
        submitMessage();
      }
    });
  });

  // ── Core: submit a message ─────────────────────────────────────────────
  function submitMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Show user bubble
    appendUserMessage(text);

    // Add to history
    history.push({ role: "user", content: text });

    // Clear input
    userInput.value = "";
    userInput.style.height = "auto";

    // Show typing indicator while waiting
    const typingEl = appendTypingIndicator();

    // Disable input while waiting
    setInputEnabled(false);

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    })
      .then((res) => res.json())
      .then((data) => {
        typingEl.remove();
        if (data.error) {
          appendErrorMessage("⚠️ " + data.error);
        } else {
          const reply = data.reply || "(no response)";
          history.push({ role: "assistant", content: reply });
          appendBotMessage(reply);
        }
      })
      .catch((err) => {
        typingEl.remove();
        appendErrorMessage("⚠️ Network error: " + err.message);
      })
      .finally(() => {
        setInputEnabled(true);
        userInput.focus();
      });
  }

  // ── DOM helpers ────────────────────────────────────────────────────────

  /**
   * Render minimal markdown: bold (**text**), italic (*text*), and
   * inline code (`code`).  Safe — does NOT use innerHTML with raw input.
   */
  function renderMarkdown(text) {
    const el = document.createElement("span");
    // Split on **…**, *…*, `…` patterns (non-greedy, negated delimiters)
    const parts = text.split(/(\*\*[^*]+?\*\*|\*[^*]+?\*|`[^`]+?`)/g);
    parts.forEach((part) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        const b = document.createElement("strong");
        b.textContent = part.slice(2, -2);
        el.appendChild(b);
      } else if (part.startsWith("*") && part.endsWith("*") && !part.startsWith("**")) {
        const em = document.createElement("em");
        em.textContent = part.slice(1, -1);
        el.appendChild(em);
      } else if (part.startsWith("`") && part.endsWith("`")) {
        const code = document.createElement("code");
        code.textContent = part.slice(1, -1);
        el.appendChild(code);
      } else {
        el.appendChild(document.createTextNode(part));
      }
    });
    return el;
  }

  function createMessage(role, isError) {
    const wrapper = document.createElement("div");
    wrapper.className = "message " + (isError ? "bot error" : role);

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = role === "user" ? "🧑" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    chatContainer.appendChild(wrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return bubble;
  }

  function appendUserMessage(text) {
    const bubble = createMessage("user", false);
    bubble.textContent = text;
  }

  function appendBotMessage(text) {
    const bubble = createMessage("bot", false);
    // Render line-by-line to support newlines + inline markdown
    text.split("\n").forEach((line, i, arr) => {
      bubble.appendChild(renderMarkdown(line));
      if (i < arr.length - 1) bubble.appendChild(document.createElement("br"));
    });
  }

  function appendErrorMessage(text) {
    const bubble = createMessage("bot", true);
    bubble.textContent = text;
  }

  function appendTypingIndicator() {
    const wrapper = document.createElement("div");
    wrapper.className = "message bot";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "🤖";

    const bubble = document.createElement("div");
    bubble.className = "bubble typing-indicator";
    bubble.setAttribute("aria-label", "CloudGuide is typing");
    for (let i = 0; i < 3; i++) bubble.appendChild(document.createElement("span"));

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    chatContainer.appendChild(wrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return wrapper;
  }

  function setInputEnabled(enabled) {
    userInput.disabled = !enabled;
    sendBtn.disabled   = !enabled;
  }
})();
