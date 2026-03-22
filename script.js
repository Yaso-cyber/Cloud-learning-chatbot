const conceptLibrary = [
  {
    keywords: ["cloud", "cloud computing", "gcp", "aws", "azure"],
    label: "Cloud computing",
    simple:
      "Cloud computing means renting computing resources over the internet instead of buying and running everything yourself.",
    analogy:
      "It is like using electricity from the power grid instead of building your own power station.",
    takeaway: "Use what you need, when you need it."
  },
  {
    keywords: ["iam", "identity", "permission", "access control"],
    label: "IAM",
    simple:
      "IAM controls who can enter a system and what actions they are allowed to perform.",
    analogy:
      "It is like a hotel key card that opens only specific doors based on your role.",
    takeaway: "Give people only the access they actually need."
  },
  {
    keywords: ["shared responsibility", "responsibility model"],
    label: "Shared responsibility model",
    simple:
      "In cloud, the provider secures the platform, while you secure your accounts, data, and configuration.",
    analogy:
      "It is like renting an apartment: the landlord secures the building, but you still lock your own door.",
    takeaway: "Cloud provider security does not replace your own security tasks."
  },
  {
    keywords: ["encryption", "encrypt", "cipher"],
    label: "Encryption",
    simple:
      "Encryption converts readable data into protected text so unauthorized people cannot understand it.",
    analogy:
      "It is like putting a message in a locked box that only someone with the right key can open.",
    takeaway: "Encrypt data at rest and in transit."
  },
  {
    keywords: ["firewall", "network rule", "security group"],
    label: "Firewall",
    simple:
      "A firewall filters traffic and allows only approved network connections.",
    analogy:
      "It is like a venue bouncer checking who can come in and who is turned away.",
    takeaway: "Allow only the traffic you really need."
  }
];

const chatEl = document.getElementById("chat");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const sendBtn = formEl.querySelector("button[type='submit']");
const templateButtons = document.querySelectorAll(".template-btn");
const navButtons = document.querySelectorAll(".nav-btn");
const panels = document.querySelectorAll(".panel");

const GEMINI_MODELS = [
  "gemini-2.5-flash",
  "gemini-2.5-flash-latest",
  "gemini-2.0-flash",
  "gemini-1.5-flash"
];
const SYSTEM_STYLE = [
  "You are a plain, clear cloud learning assistant.",
  "For every user question, respond in this exact structure:",
  "1) Simple version: one to two short sentences.",
  "2) Analogy: one concrete everyday analogy.",
  "3) Takeaway: one practical sentence.",
  "Keep language beginner-friendly. Avoid jargon unless you define it."
].join("\n");

let cachedGeminiKey = null;
let workingGeminiModel = null;

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

async function loadGeminiKey() {
  if (cachedGeminiKey) return cachedGeminiKey;

  if (typeof window !== "undefined" && window.GEMINI_API_KEY) {
    cachedGeminiKey = String(window.GEMINI_API_KEY).trim();
    return cachedGeminiKey;
  }

  return "";
}

async function tryGeminiModel(model, apiKey, rawQuestion) {
  const endpoint =
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(apiKey)}`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system_instruction: {
        parts: [{ text: SYSTEM_STYLE }]
      },
      contents: [
        {
          role: "user",
          parts: [{ text: rawQuestion }]
        }
      ],
      generationConfig: {
        temperature: 0.4,
        maxOutputTokens: 350
      }
    })
  });

  const data = await response.json();
  if (!response.ok) {
    const errMsg = data?.error?.message || `gemini_http_${response.status}`;
    const err = new Error(errMsg);
    err.status = response.status;
    throw err;
  }

  const text = (data?.candidates || [])
    .flatMap((c) => c?.content?.parts || [])
    .map((p) => p?.text || "")
    .join("\n")
    .trim();

  if (!text) {
    throw new Error("empty_model_response");
  }

  return text;
}

async function getGeminiReply(rawQuestion) {
  const apiKey = await loadGeminiKey();
  if (!apiKey) {
    throw new Error("missing_key");
  }

  const modelOrder = workingGeminiModel
    ? [workingGeminiModel, ...GEMINI_MODELS.filter((m) => m !== workingGeminiModel)]
    : [...GEMINI_MODELS];

  let lastError = null;
  for (const model of modelOrder) {
    try {
      const reply = await tryGeminiModel(model, apiKey, rawQuestion);
      workingGeminiModel = model;
      return reply;
    } catch (err) {
      lastError = err;
      // Try next model only when model path is invalid.
      if (!(err?.status === 404 || String(err?.message || "").includes("NOT_FOUND"))) {
        throw err;
      }
    }
  }

  throw lastError || new Error("no_supported_model");
}

function simplifyUserText(text) {
  const cleaned = text.trim().replace(/[?!.]+$/g, "");
  if (!cleaned) return "I can explain that simply.";
  return `You are asking about: ${cleaned}.`;
}

function buildPlainAnalogyReply(concept, userText) {
  if (!concept) {
    return [
      simplifyUserText(userText),
      "Simple version: This topic can be understood as a system with rules, roles, and risk controls.",
      "Analogy: Think of it like organizing a house with keys, locks, and labeled rooms so people only enter where they should.",
      "Takeaway: Break big topics into who can access, what is protected, and how to monitor it."
    ].join("\n\n");
  }

  return [
    `Topic: ${concept.label}`,
    `Simple version: ${concept.simple}`,
    `Analogy: ${concept.analogy}`,
    `Takeaway: ${concept.takeaway}`
  ].join("\n\n");
}

function getFallbackReply(rawQuestion) {
  const question = rawQuestion.trim().toLowerCase();
  for (const concept of conceptLibrary) {
    if (concept.keywords.some((keyword) => question.includes(keyword))) {
      return buildPlainAnalogyReply(concept, rawQuestion);
    }
  }

  return buildPlainAnalogyReply(null, rawQuestion);
}

loadGeminiKey().then((key) => {
  if (key) {
    addMessage(
      "bot",
      "CloudGuide Lite detected your Gemini key. I will use Gemini Flash and auto-fallback to compatible Flash model IDs if needed."
    );
  } else {
    addMessage(
      "bot",
      "CloudGuide Lite is ready in offline fallback mode. Add your key in config.local.js as window.GEMINI_API_KEY, then refresh."
    );
  }
});

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = inputEl.value.trim();
  if (!question) return;

  addMessage("user", question);
  inputEl.value = "";

  inputEl.disabled = true;
  sendBtn.disabled = true;
  const pending = addMessage("bot", "Thinking...");

  try {
    const aiReply = await getGeminiReply(question);
    pending.textContent = aiReply;
  } catch (err) {
    const reason = err?.message === "missing_key"
      ? "Missing key in config.local.js"
      : String(err?.message || "Gemini request failed");
    pending.textContent = [
      getFallbackReply(question),
      "",
      `Note: Gemini could not be reached (${reason}), so this answer used local fallback logic.`
    ].join("\n");
  } finally {
    inputEl.disabled = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
});

// ── Conversation templates ─────────────────────────────────────────
templateButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    inputEl.value = btn.dataset.template || "";
    inputEl.focus();
    // Hide templates once the user picks one
    document.getElementById("templates").style.display = "none";
  });
});

// Show templates again when chat input is emptied
inputEl.addEventListener("input", () => {
  const tpl = document.getElementById("templates");
  tpl.style.display = inputEl.value.trim() === "" ? "" : "none";
});

// ── Sidebar navigation ────────────────────────────────────────────
navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    navButtons.forEach((b) => b.classList.remove("active"));
    panels.forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("panel-" + btn.dataset.panel).classList.add("active");
  });
});

const quizData = [
  {
    question: "Which model gives you virtual machines and networking?",
    options: ["IaaS", "SaaS", "MFA"],
    answer: "IaaS",
  },
  {
    question: "What does IAM mainly control?",
    options: ["Power usage", "Identity and permissions", "Internet speed"],
    answer: "Identity and permissions",
  },
  {
    question: "In shared responsibility, customer secures:",
    options: ["Their data and configuration", "Provider datacenter locks", "Global DNS root"],
    answer: "Their data and configuration",
  },
];

let quizIndex = -1;
let quizScore = 0;
let answered = 0;

const qText = document.getElementById("quiz-question");
const qOptions = document.getElementById("quiz-options");
const qFeedback = document.getElementById("quiz-feedback");
const qScore = document.getElementById("quiz-score");
const qStart = document.getElementById("quiz-start");

function setScore() {
  qScore.textContent = `Score: ${quizScore} / ${answered}`;
}

function showQuestion() {
  quizIndex += 1;
  qFeedback.textContent = "";
  qFeedback.className = "feedback";

  if (quizIndex >= quizData.length) {
    qText.textContent = "Quiz complete.";
    qOptions.innerHTML = "";
    qStart.textContent = "Restart Quiz";
    quizIndex = -1;
    return;
  }

  const current = quizData[quizIndex];
  qText.textContent = current.question;
  qOptions.innerHTML = "";

  current.options.forEach((option) => {
    const btn = document.createElement("button");
    btn.textContent = option;
    btn.addEventListener("click", () => {
      answered += 1;
      if (option === current.answer) {
        quizScore += 1;
        qFeedback.textContent = "Correct";
        qFeedback.className = "feedback good";
      } else {
        qFeedback.textContent = `Not quite. Correct answer: ${current.answer}`;
        qFeedback.className = "feedback bad";
      }
      setScore();
      setTimeout(showQuestion, 650);
    });
    qOptions.appendChild(btn);
  });
}

qStart.addEventListener("click", () => {
  if (quizIndex === -1) {
    quizScore = 0;
    answered = 0;
    setScore();
  }
  showQuestion();
});
