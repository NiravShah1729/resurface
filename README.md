# Resurface 🌊

Local-first companion that captures things you save (Instagram reels, LinkedIn posts, movie/book recs), uses Gemma via the Google GenAI SDK to understand **why** you saved them, and resurfaces them through a Telegram bot.

---

## 🚀 Quickstart

### 1. Environment Setup
```powershell
.\.venv\Scripts\Activate.ps1
# Or run with .\.venv\Scripts\python directly
```

Make sure your [.env](file:///.env) contains:
```env
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
GEMINI_API_KEY="your_gemini_api_key"
GEMMA_MODEL=gemma-4-26b-a4b-it
EMBED_MODEL=gemini-embedding-001
NUDGE_INTERVAL_MINUTES=1440
```

### 2. Start the Backend & Telegram Bot
```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
This single command runs:
- **FastAPI backend** on `http://localhost:8000`
- **Telegram bot** (listening for `/start`, `/ask`, `/nudge_now`, and sending notifications)
- **JobQueue** (automatically dispatching periodic learning nudges)

---

## 🧩 Loading the Chrome Extension

1. Open Google Chrome and navigate to `chrome://extensions`.
2. Toggle **Developer mode** on (top-right corner).
3. Click the **Load unpacked** button (top-left).
4. Select the `extension/` folder in this repository:
   ```
   c:\Users\nirav\OneDrive\Desktop\MyProjects\hacktoberfest\extension
   ```
5. Pin the Resurface extension if desired.

### How it works:
- When you click **Save** on an **Instagram** reel/post or **LinkedIn** update, the content script captures the post text and sends it to the extension service worker.
- The service worker sends a `POST` request to `http://localhost:8000/saves` (avoiding site CSP/mixed-content blocks).
- A **"⚡ Sent to Resurface"** toast appears on your screen.
- Your Telegram bot immediately pings you with the parsed title, category, reason, and action.
