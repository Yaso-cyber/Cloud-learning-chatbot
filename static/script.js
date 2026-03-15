/**
 * CloudGuide — frontend logic
 *
 * Handles the multi-panel SPA: Chat, Quiz, Notes, Upload, Learning Plan.
 */

(function () {
  "use strict";

  // ── Tab / panel navigation ────────────────────────────────────────────
  const navTabs  = document.querySelectorAll(".nav-tab");
  const panels   = document.querySelectorAll(".panel");
  const inputBar = document.getElementById("input-bar");

  navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      navTabs.forEach((t) => t.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      const panelId = tab.dataset.panel;
      document.getElementById(panelId).classList.add("active");
      // Only show the input bar on the chat panel
      inputBar.style.display = (panelId === "panel-chat") ? "" : "none";
    });
  });

  // ════════════════════════════════════════════════════════════════════════
  // CHAT PANEL
  // ════════════════════════════════════════════════════════════════════════
  const chatContainer = document.getElementById("chat-container");
  const inputForm     = document.getElementById("input-form");
  const userInput     = document.getElementById("user-input");
  const sendBtn       = document.getElementById("send-btn");
  const topicPills    = document.querySelectorAll(".topic-pill");
  const analogyToggle = document.getElementById("analogy-toggle");

  /** @type {{ role: "user"|"assistant", content: string }[]} */
  const history = [];

  appendBotMessage(
    "👋 Hi! I'm **CloudGuide**, your AI learning companion for Cloud, " +
    "Cloud Security, and GRC.\n\n" +
    "Ask me anything — like *\"What is IaaS?\"* or " +
    "*\"How do I start preparing for a cloud security role?\"* — " +
    "or click one of the topic buttons above to get started!\n\n" +
    "💡 Tip: Enable **Analogy mode** (toggle below) for beginner-friendly " +
    "explanations using everyday examples."
  );

  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 128) + "px";
  });

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitMessage(); }
  });

  inputForm.addEventListener("submit", (e) => { e.preventDefault(); submitMessage(); });

  topicPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      const prompt = pill.dataset.prompt;
      if (prompt) { userInput.value = prompt; submitMessage(); }
    });
  });

  function submitMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    appendUserMessage(text);
    history.push({ role: "user", content: text });
    userInput.value = "";
    userInput.style.height = "auto";
    const typingEl = appendTypingIndicator();
    setInputEnabled(false);

    const useAnalogy = analogyToggle && analogyToggle.checked;

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history, analogy: useAnalogy }),
    })
      .then((r) => r.json())
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
      .catch((err) => { typingEl.remove(); appendErrorMessage("⚠️ Network error: " + err.message); })
      .finally(() => { setInputEnabled(true); userInput.focus(); });
  }

  // ── DOM helpers (chat) ────────────────────────────────────────────────

  function renderMarkdown(text) {
    const el = document.createElement("span");
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

  // ════════════════════════════════════════════════════════════════════════
  // QUIZ PANEL
  // ════════════════════════════════════════════════════════════════════════
  let quizSessionId = null;
  let currentAnswer = null;

  const categoryGrid   = document.getElementById("category-grid");
  const startQuizBtn   = document.getElementById("start-quiz-btn");
  const quizSetup      = document.getElementById("quiz-setup");
  const quizQuestion   = document.getElementById("quiz-question");
  const quizResult     = document.getElementById("quiz-result");
  const questionText   = document.getElementById("question-text");
  const quizOptions    = document.getElementById("quiz-options");
  const quizFeedback   = document.getElementById("quiz-feedback");
  const quizProgress   = document.getElementById("quiz-progress");
  const progressFill   = document.getElementById("progress-fill");
  const nextBtn        = document.getElementById("next-btn");
  const resultScore    = document.getElementById("result-score");
  const resultTotal    = document.getElementById("result-total");
  const resultPct      = document.getElementById("result-pct");
  const newQuizBtn     = document.getElementById("new-quiz-btn");

  // Load categories
  fetch("/quiz/categories")
    .then((r) => r.json())
    .then((data) => {
      const allBtn = buildCategoryBtn("🎲 Random Mix", "random", true);
      categoryGrid.appendChild(allBtn);
      (data.categories || []).forEach((cat) => {
        const label = cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        categoryGrid.appendChild(buildCategoryBtn("📚 " + label, cat, false));
      });
    })
    .catch(() => {});

  function buildCategoryBtn(label, value, selected) {
    const btn = document.createElement("button");
    btn.className = "category-btn" + (selected ? " selected" : "");
    btn.textContent = label;
    btn.dataset.value = value;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".category-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      startQuizBtn.disabled = false;
    });
    return btn;
  }

  startQuizBtn.addEventListener("click", () => {
    const selected = document.querySelector(".category-btn.selected");
    if (!selected) return;
    const category = selected.dataset.value;

    fetch("/quiz/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) { alert(data.error); return; }
        quizSessionId = data.session_id;
        quizSetup.style.display  = "none";
        quizResult.style.display = "none";
        quizQuestion.style.display = "block";
        loadNextQuestion();
      })
      .catch(() => alert("Failed to start quiz."));
  });

  function loadNextQuestion() {
    currentAnswer = null;
    quizFeedback.className = "quiz-feedback";
    quizFeedback.textContent = "";
    nextBtn.style.display = "none";
    quizOptions.innerHTML = "";

    fetch("/quiz/question?session_id=" + quizSessionId)
      .then((r) => r.json())
      .then((data) => {
        if (data.finished) {
          showResult(data.score, data.total, data.percentage);
          return;
        }
        const pct = Math.round((data.question_number - 1) / data.total * 100);
        progressFill.style.width = pct + "%";
        quizProgress.textContent = "Question " + data.question_number + " of " + data.total;
        questionText.textContent = data.question;

        data.options.forEach((opt) => {
          const btn = document.createElement("button");
          btn.className = "option-btn";
          btn.textContent = opt;
          const letter = opt.charAt(0);
          btn.addEventListener("click", () => submitQuizAnswer(letter, data.options));
          quizOptions.appendChild(btn);
        });
      });
  }

  function submitQuizAnswer(answer, options) {
    if (currentAnswer !== null) return;
    currentAnswer = answer;

    document.querySelectorAll(".option-btn").forEach((b) => { b.disabled = true; });

    fetch("/quiz/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: quizSessionId, answer }),
    })
      .then((r) => r.json())
      .then((data) => {
        // Highlight options
        document.querySelectorAll(".option-btn").forEach((btn) => {
          const letter = btn.textContent.charAt(0);
          if (letter === data.correct_answer) btn.classList.add("correct");
          else if (letter === answer && !data.correct) btn.classList.add("wrong");
        });

        quizFeedback.className = "quiz-feedback show " + (data.correct ? "correct-fb" : "wrong-fb");
        quizFeedback.textContent = (data.correct ? "✅ Correct! " : "❌ Incorrect. ") + data.explanation;
        nextBtn.style.display = "inline-block";
      });
  }

  nextBtn.addEventListener("click", () => {
    fetch("/quiz/question?session_id=" + quizSessionId)
      .then((r) => r.json())
      .then((data) => {
        if (data.finished) {
          showResult(data.score, data.total, data.percentage);
        } else {
          loadNextQuestion();
        }
      });
  });

  function showResult(score, total, pct) {
    quizQuestion.style.display = "none";
    quizResult.style.display   = "block";
    resultScore.textContent = score;
    resultTotal.textContent = total;
    resultPct.textContent   = pct + "%";
  }

  newQuizBtn.addEventListener("click", () => {
    quizSessionId = null;
    quizResult.style.display   = "none";
    quizQuestion.style.display = "none";
    quizSetup.style.display    = "block";
    startQuizBtn.disabled = true;
    document.querySelectorAll(".category-btn").forEach((b) => b.classList.remove("selected"));
  });

  // ════════════════════════════════════════════════════════════════════════
  // NOTES PANEL
  // ════════════════════════════════════════════════════════════════════════
  const addNoteBtn    = document.getElementById("add-note-btn");
  const noteForm      = document.getElementById("note-form");
  const cancelNoteBtn = document.getElementById("cancel-note-btn");
  const saveNoteBtn   = document.getElementById("save-note-btn");
  const noteTopicIn   = document.getElementById("note-topic");
  const noteContentIn = document.getElementById("note-content");
  const notesList     = document.getElementById("notes-list");
  const topicFilter   = document.getElementById("topic-filter");
  const filterBtn     = document.getElementById("filter-btn");
  const clearFilter   = document.getElementById("clear-filter");
  let editingNoteId   = null;

  addNoteBtn.addEventListener("click", () => {
    editingNoteId = null;
    noteTopicIn.value   = "";
    noteContentIn.value = "";
    noteForm.classList.add("show");
    noteTopicIn.focus();
  });

  cancelNoteBtn.addEventListener("click", () => noteForm.classList.remove("show"));

  saveNoteBtn.addEventListener("click", () => {
    const topic   = noteTopicIn.value.trim();
    const content = noteContentIn.value.trim();
    if (!topic || !content) { alert("Both topic and content are required."); return; }

    const url    = editingNoteId ? "/notes/" + editingNoteId : "/notes";
    const method = editingNoteId ? "PUT" : "POST";

    fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, content }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) { alert(data.error); return; }
        noteForm.classList.remove("show");
        loadNotes();
      })
      .catch(() => alert("Failed to save note."));
  });

  filterBtn.addEventListener("click", () => loadNotes(topicFilter.value.trim()));
  clearFilter.addEventListener("click", () => { topicFilter.value = ""; loadNotes(); });
  topicFilter.addEventListener("keydown", (e) => { if (e.key === "Enter") loadNotes(topicFilter.value.trim()); });

  function loadNotes(topic) {
    const url = topic ? "/notes?topic=" + encodeURIComponent(topic) : "/notes";
    fetch(url)
      .then((r) => r.json())
      .then((data) => renderNotes(data.notes || []))
      .catch(() => {});
  }

  function renderNotes(notes) {
    notesList.innerHTML = "";
    if (notes.length === 0) {
      notesList.innerHTML = "<p style='color:var(--clr-muted);font-size:.9rem;'>No notes yet. Click \"+ Add Note\" to create one.</p>";
      return;
    }
    notes.forEach((note) => {
      const card = document.createElement("div");
      card.className = "note-card";
      card.innerHTML =
        "<div class='note-topic'>" + escapeHtml(note.topic) + "</div>" +
        "<div class='note-content'>" + escapeHtml(note.content) + "</div>" +
        "<div class='note-date'>Updated " + formatDate(note.updated_at) + "</div>" +
        "<div class='note-actions'>" +
        "  <button class='note-edit-btn' data-id='" + note.id + "'>✏️ Edit</button>" +
        "  <button class='note-delete-btn' data-id='" + note.id + "'>🗑️ Delete</button>" +
        "</div>";
      notesList.appendChild(card);
    });

    document.querySelectorAll(".note-edit-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const noteId = btn.dataset.id;
        fetch("/notes/" + noteId)
          .then((r) => r.json())
          .then((data) => {
            editingNoteId   = noteId;
            noteTopicIn.value   = data.note.topic;
            noteContentIn.value = data.note.content;
            noteForm.classList.add("show");
            noteTopicIn.focus();
          });
      });
    });

    document.querySelectorAll(".note-delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (!confirm("Delete this note?")) return;
        fetch("/notes/" + btn.dataset.id, { method: "DELETE" })
          .then(() => loadNotes())
          .catch(() => alert("Failed to delete note."));
      });
    });
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatDate(iso) {
    try { return new Date(iso).toLocaleString(); } catch (_) { return iso; }
  }

  // Load notes when switching to the notes tab
  document.querySelector('[data-panel="panel-notes"]').addEventListener("click", () => loadNotes());

  // ════════════════════════════════════════════════════════════════════════
  // UPLOAD PANEL
  // ════════════════════════════════════════════════════════════════════════
  const pdfInput     = document.getElementById("pdf-file-input");
  const uploadBtn    = document.getElementById("upload-btn");
  const uploadResult = document.getElementById("upload-result");
  const summaryText  = document.getElementById("summary-text");
  const resultFile   = document.getElementById("result-filename");
  const uploadSpinner= document.getElementById("upload-spinner");
  const dropZone     = document.getElementById("upload-drop-zone");

  dropZone.addEventListener("click", () => pdfInput.click());
  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      pdfInput.files = e.dataTransfer.files;
      updateDropZoneLabel();
    }
  });

  pdfInput.addEventListener("change", updateDropZoneLabel);

  function updateDropZoneLabel() {
    const label = dropZone.querySelector(".drop-label");
    if (pdfInput.files && pdfInput.files.length) {
      label.textContent = "📄 " + pdfInput.files[0].name;
      uploadBtn.disabled = false;
    }
  }

  uploadBtn.addEventListener("click", () => {
    if (!pdfInput.files || !pdfInput.files.length) { alert("Please select a PDF file."); return; }
    const formData = new FormData();
    formData.append("file", pdfInput.files[0]);
    uploadBtn.disabled = true;
    uploadSpinner.classList.add("show");
    uploadResult.classList.remove("show");

    fetch("/upload", { method: "POST", body: formData })
      .then((r) => r.json())
      .then((data) => {
        uploadSpinner.classList.remove("show");
        if (data.error) { alert(data.error); uploadBtn.disabled = false; return; }
        resultFile.textContent = data.filename + (data.truncated ? " (first 6,000 words)" : "");
        summaryText.textContent = data.summary;
        uploadResult.classList.add("show");
        uploadBtn.disabled = false;
      })
      .catch(() => { uploadSpinner.classList.remove("show"); alert("Upload failed."); uploadBtn.disabled = false; });
  });

  // ════════════════════════════════════════════════════════════════════════
  // LEARNING PLAN PANEL
  // ════════════════════════════════════════════════════════════════════════
  const generatePlanBtn = document.getElementById("generate-plan-btn");
  const planFocusIn     = document.getElementById("plan-focus");
  const planLevelIn     = document.getElementById("plan-level");
  const planGrid        = document.getElementById("plan-grid");
  const planLoading     = document.getElementById("plan-loading");
  let currentPlanId     = null;
  let currentPlanData   = null;

  generatePlanBtn.addEventListener("click", () => {
    const focus = planFocusIn.value.trim();
    const level = planLevelIn.value;
    generatePlanBtn.disabled = true;
    planLoading.classList.add("show");
    planGrid.innerHTML = "";

    fetch("/learning-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ focus, level }),
    })
      .then((r) => r.json())
      .then((data) => {
        planLoading.classList.remove("show");
        generatePlanBtn.disabled = false;
        if (data.error) { alert(data.error); return; }
        currentPlanId   = data.plan_id;
        currentPlanData = data.plan.plan || data.plan;
        renderPlan(currentPlanData, data.progress || {});
      })
      .catch(() => { planLoading.classList.remove("show"); generatePlanBtn.disabled = false; alert("Failed to generate plan."); });
  });

  function renderPlan(plan, progress) {
    planGrid.innerHTML = "";
    const days = plan.days || [];
    if (!days.length) {
      planGrid.innerHTML = "<p style='color:var(--clr-muted);'>Could not parse plan. Try again.</p>";
      return;
    }
    days.forEach((day) => {
      const isComplete = progress[day.day] === true;
      const card = document.createElement("div");
      card.className = "day-card" + (isComplete ? " completed" : "");

      const activitiesHtml = (day.activities || [])
        .map((a) => "<li>" + escapeHtml(a) + "</li>")
        .join("");

      card.innerHTML =
        "<div class='day-header'>" +
        "  <span class='day-name'>" + escapeHtml(day.day) + "</span>" +
        "  <button class='complete-day-btn" + (isComplete ? " done" : "") + "' data-day='" + escapeHtml(day.day) + "'>" +
        (isComplete ? "✅ Done" : "Mark complete") + "</button>" +
        "</div>" +
        "<div class='day-topic'>" + escapeHtml(day.topic || "") + "</div>" +
        "<div class='day-desc'>" + escapeHtml(day.description || "") + "</div>" +
        (activitiesHtml ? "<ul class='day-activities'>" + activitiesHtml + "</ul>" : "") +
        (day.estimated_minutes ? "<div class='day-time'>⏱ ~" + day.estimated_minutes + " min</div>" : "");

      planGrid.appendChild(card);
    });

    document.querySelectorAll(".complete-day-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (!currentPlanId) return;
        const day = btn.dataset.day;
        const completed = !btn.classList.contains("done");
        fetch("/learning-plan/" + currentPlanId + "/progress", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ day, completed }),
        })
          .then((r) => r.json())
          .then((data) => renderPlan(currentPlanData || plan, data.progress || {}));
      });
    });
  }
})();
