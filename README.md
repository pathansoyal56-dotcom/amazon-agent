# Amazon Affiliate Web Agent

AI-powered content generator for Amazon affiliate marketing.
Paste one Amazon link → get blog post, Instagram caption, TikTok script, Twitter post, Pinterest pin — all auto-posted.

---

## Quick Start (local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
# Windows: set ANTHROPIC_API_KEY=sk-ant-your-key-here

# 3. Run the server
python amazon_agent_backend.py
# OR
uvicorn amazon_agent_backend:app --reload --host 0.0.0.0 --port 8000

# 4. Open http://localhost:8000 in your browser
```

---

## Deploy to Render (free tier)

1. Push this folder to a GitHub repo
2. Go to https://render.com → New Web Service → connect your repo
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn amazon_agent_backend:app --host 0.0.0.0 --port $PORT`
   - **Environment Variable**: `ANTHROPIC_API_KEY` = your key
4. Deploy → your public URL is ready

## Deploy to Heroku

```bash
heroku create your-agent-name
heroku config:set ANTHROPIC_API_KEY="sk-ant-your-key"
git push heroku main
heroku open
```

## Deploy to Railway

1. Go to https://railway.app → New Project → Deploy from GitHub
2. Add env var: `ANTHROPIC_API_KEY`
3. Done — Railway auto-detects Python and the Procfile

---

## Bugs Fixed (vs original)

| Bug | Fix |
|-----|-----|
| Wrong model name `claude-opus-4-20250805` | Changed to `claude-sonnet-4-5` |
| `uvicorn.run("app:app")` — wrong module name | Fixed to `"amazon_agent_backend:app"` |
| Frontend hardcoded `localhost:8000` | Now uses `window.location.origin` dynamically |
| No static file serving | Added `StaticFiles` mount + `FileResponse` for `/` |
| No `requirements.txt` | Added with pinned versions |
| No `Procfile` | Added for Heroku/Render/Railway |
| Twitter poster was a no-op stub with no feedback | Returns honest `note` field |
| Blog poster used hardcoded fake URL | Now requires `blog_api_url` credential |
| `posted_to` not initialized on non-auto-post | Initialized to `{}` always |
| Generator crashed at import if no API key | Lazy init — clean error message |

---

## API Docs

Visit `/docs` for the interactive Swagger UI once the server is running.

Key endpoints:
- `POST /generate` — generate content from Amazon link
- `POST /auth/connect` — save platform credentials
- `GET /auth/status` — check connected platforms
- `GET /history` — list generated content
- `GET /health` — server health + model info
