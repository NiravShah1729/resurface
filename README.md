# Resurface 🌊

> **Turn your saved reels, LinkedIn posts, and bookmarks into actionable knowledge — powered by Gemma.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local--First-003B57?logo=sqlite)](https://www.sqlite.org/)
[![Gemma](https://img.shields.io/badge/Model-Gemma--4--26B-8E44AD)](https://ai.google.dev/gemma)
[![Telegram](https://img.shields.io/badge/Bot-Telegram-2CA5E0?logo=telegram)](https://telegram.org/)

---

## 📌 1. What does it do, and for whom?

### The Problem
We all save things online every day: Instagram reels, LinkedIn job posts, book recommendations, and coding tutorials. But once saved, they disappear into a "bookmark graveyard" and are rarely revisited or acted upon.

### The Solution: Resurface
**Resurface** is a local-first application designed for **learners, researchers, and professionals** that captures what you save, understands *why* you saved it, and resurfaces it at the right time.

- 🧩 **Zero-Friction Capture:** When you click native **Save** on Instagram or LinkedIn, our Manifest V3 Chrome Extension intercepts it automatically.
- 🧠 **Intent Understanding:** Uses open-weight AI to strip social media clutter, infer why you saved the post, categorize it (`book`, `movie`, `job`, `skill`, `recipe`, `other`), assign an educational value score (1–5), and suggest an action (`read`, `watch`, `apply`, `learn`, `try`).
- 🤖 **Telegram Companion:** Confirms every save in real-time, answers semantic questions about your collection (`/ask`), and sends scheduled nudges with **Done** and **Ignore** buttons to keep your backlog fresh.

---

## 🧠 2. Which open-source / open-weight AI does it use?

Resurface is powered by:
- **[Gemma 4 26B (`gemma-4-26b-a4b-it`)](https://ai.google.dev/gemma):** Google's open-weights LLM, accessed via the `google-genai` SDK. Gemma strips HTML/social clutter, classifies bookmarks, extracts structured metadata, and crafts punchy, motivational nudge reminders.
- **[Gemini Embedding (`gemini-embedding-001`)](https://ai.google.dev/):** Computes 3072-dimensional vector embeddings stored directly in SQLite for cosine-similarity semantic search (`/ask`).
- **Provider Agnostic Abstraction:** All AI calls are isolated in [`app/llm.py`](app/llm.py) behind `generate(prompt, system=None, json_mode=False)` and `embed(text)`. No other file touches the AI client, allowing the backend LLM to be swapped effortlessly.

---

## 🛠️ 3. How do I run it?

### Prerequisites
- Python 3.11+
- Google Chrome browser
- A Telegram account and a bot token from [@BotFather](https://t.me/botfather)
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Step 1: Clone & Configure
```powershell
git clone https://github.com/NiravShah1729/resurface.git
cd resurface
```

Create your virtual environment and install dependencies:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file from the example:
```powershell
cp .env.example .env
```
Fill in your credentials in [.env](.env):
```env
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
GEMINI_API_KEY="your_gemini_api_key"
GEMMA_MODEL=gemma-4-26b-a4b-it
EMBED_MODEL=gemini-embedding-001
NUDGE_INTERVAL_MINUTES=1440
```

---

### Step 2: Start the Backend & Telegram Bot
Run the single command:
```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
This boots the FastAPI REST API and runs the Telegram bot polling process together.

---

### Step 3: Install the Chrome Extension
1. Open Google Chrome and go to `chrome://extensions`.
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** (top-left).
4. Select the [`extension/`](extension/) directory from this repository.

---

### Step 4: Connect & Use
1. Open Telegram and search for your bot (or click your bot's link).
2. Send **`/start`** to register your chat ID.
3. Browse Instagram or LinkedIn and click **Save** on any post or reel:
   - A **"⚡ Sent to Resurface"** toast pops up on the webpage.
   - Your Telegram bot immediately sends a confirmation with title, category, and action!
4. In Telegram, try:
   - `/nudge_now` — Get an immediate smart nudge with **[Done]** and **[Ignore]** buttons.
   - `/ask What books or interview tips did I save?` — Ask questions answered via semantic search.

---

## 📸 4. Screenshots & Demo

### 1. Zero-Friction Capture (Chrome Extension Toast)
```
+-------------------------------------------------------------+
| Instagram / LinkedIn Reel                                   |
|                                                             |
|   [Bookmark Clicked]                                        |
|                                                             |
|                                     +---------------------+ |
|                                     | ⚡ Sent to Resurface | |
|                                     +---------------------+ |
+-------------------------------------------------------------+
```

### 2. Live Telegram Bot Confirmation & Nudge Flow
```
Telegram Bot (@nirav_hackerfestBot):
─────────────────────────────────────────────────────────────
Saved: Google Interview Prep with AI (skill) - The user wants 
to learn how to leverage AI tools for technical interviews. 
Action: learn
https://www.instagram.com/reels/De10LQ3SN40/

─────────────────────────────────────────────────────────────
💡 Nudge: Ready to master your Google technical interviews? 
Take 10 minutes to review these AI preparation strategies today.

📌 Google Interview Prep with AI (skill)
🎯 Action: learn
🔗 https://www.instagram.com/reels/De10LQ3SN40/

[ ✅ Done ]    [ ⏭️ Ignore ]
─────────────────────────────────────────────────────────────
User: /ask What movies did I save?

Bot: You saved "Courtroom Drama Movie Recommendations" 
(watch). The user was looking for high-quality courtroom 
drama recommendations!
```

*(Add video/GIF link here: `demo.mp4`)*

---

## 👥 5. Who built it?

Built for the Hackathon by:

- **Nirav Shah** — [@NiravShah1729](https://github.com/NiravShah1729)

---

## 📜 License
MIT License. See [LICENSE](LICENSE) for details.
