# How the AI Works

## Overview

CloudGuide Lite uses **Google Gemini Flash** as its AI backend. The entire integration is client-side, the browser calls the Gemini API directly, no server needed.

---

## API Key

Your Gemini API key lives in **`config.local.js`** (git-ignored). It sets a global variable:

```js
window.GEMINI_API_KEY = "YOUR_KEY_HERE";
```

A template is provided in `config.local.example.js`. Copy it and paste your real key:

```
cp config.local.example.js config.local.js
```

The key is loaded at runtime in `script.js` via the `loadGeminiKey()` function, which reads `window.GEMINI_API_KEY`.

---

## Personality / System Prompt

The AI's personality is defined in the `SYSTEM_STYLE` constant in **`script.js`** (around line 61):

```js
const SYSTEM_STYLE = [
  "You are a plain, clear cloud learning assistant.",
  "For every user question, respond in this exact structure:",
  "1) Simple version: one to two short sentences.",
  "2) Analogy: one concrete everyday analogy.",
  "3) Takeaway: one practical sentence.",
  "Keep language beginner-friendly. Avoid jargon unless you define it.",
].join("\n");
```

This is sent as the `system_instruction` in every API request, so Gemini always responds in this structured, beginner-friendly format.

**To change the personality:** Edit the strings in the `SYSTEM_STYLE` array. You can change the tone, structure, or topic focus by modifying these lines. You can also have it output code, like json to fill in specifics like items, tables, structures etc (think like thoughtsplus events on a calendar eg NLP)

---

## How a Chat Message Flows

1. User types a question or clicks a quick-prompt button.
2. `script.js` calls `getGeminiReply(question)`.
3. `getGeminiReply` loads the API key via `loadGeminiKey()`.
4. It tries models in order: `gemini-2.5-flash` → `gemini-2.5-flash-latest` → `gemini-2.0-flash` → `gemini-1.5-flash`.
5. For each model, `tryGeminiModel()` sends a POST request to:
   ```
   https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
   ```
   The request body includes:
   - `system_instruction` — the `SYSTEM_STYLE` personality prompt
   - `contents` — the user's question
   - `generationConfig` — `temperature: 0.4`, `maxOutputTokens: 350`
6. If a model returns 404, the next model is tried. Once a model works, it's cached in `workingGeminiModel` so subsequent requests skip the fallback loop.
7. The AI response text is extracted and displayed in the chat.

---

## Model Fallback Chain

Defined in the `GEMINI_MODELS` array in `script.js`:

```js
const GEMINI_MODELS = [
  "gemini-2.5-flash",
  "gemini-2.5-flash-latest",
  "gemini-2.0-flash",
  "gemini-1.5-flash",
];
```

If a model isn't available (404), the next one is tried automatically. The first working model is remembered for the session.

---

## Offline Fallback (No API Key)

If no API key is set or the API is unreachable, the site falls back to a local **concept library** defined at the top of `script.js`:

```js
const conceptLibrary = [
  { keywords: ["cloud", ...], label: "Cloud computing", simple: "...", analogy: "...", takeaway: "..." },
  { keywords: ["iam", ...],   label: "IAM", ... },
  // ... more concepts
];
```

The fallback matches the user's question against keywords and returns a pre-written simple explanation, analogy, and takeaway. If nothing matches, a generic response is returned.

---

## Generation Settings

| Setting           | Value | Where                           |
| ----------------- | ----- | ------------------------------- |
| Temperature       | 0.4   | `tryGeminiModel()` in script.js |
| Max output tokens | 350   | `tryGeminiModel()` in script.js |

- **Temperature 0.4** keeps responses focused and consistent (lower = less random).
- **350 tokens** keeps answers concise.

---

## Quick Reference: What to Edit

| Want to change…            | Edit this…                              |
| -------------------------- | --------------------------------------- |
| AI personality / tone      | `SYSTEM_STYLE` in `script.js`           |
| API key                    | `config.local.js`                       |
| Which Gemini models to try | `GEMINI_MODELS` array in `script.js`    |
| Response length            | `maxOutputTokens` in `tryGeminiModel()` |
| Response randomness        | `temperature` in `tryGeminiModel()`     |
| Offline fallback answers   | `conceptLibrary` array in `script.js`   |
