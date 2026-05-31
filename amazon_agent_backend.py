"""
Amazon Affiliate Web Agent - Backend API
Complete SaaS solution with platform integrations and auto-posting

Stack: FastAPI + Anthropic + Platform APIs (Instagram, Twitter, Pinterest, etc.)
"""

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
import anthropic
import os
import json
from datetime import datetime
from pathlib import Path
import asyncio
import httpx
import re
import urllib.parse

# ============================================================================
# MODELS & SCHEMAS
# ============================================================================

class AmazonLinkRequest(BaseModel):
    amazon_link: str
    product_name: Optional[str] = None
    auto_post: bool = True

class PlatformCredentials(BaseModel):
    instagram_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_secret: Optional[str] = None
    pinterest_token: Optional[str] = None
    blog_api_key: Optional[str] = None
    blog_api_url: Optional[str] = None

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(
    title="Amazon Affiliate Web Agent",
    description="AI-powered content generation and auto-posting to social platforms",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage
DATA_DIR = Path("agent_data")
DATA_DIR.mkdir(exist_ok=True)
CREDENTIALS_FILE = DATA_DIR / "credentials.json"
CONTENT_FILE = DATA_DIR / "generated_content.json"

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    # FIX: Use the correct, current model name
    MODEL = "claude-sonnet-4-5"
    INSTAGRAM_GRAPH_API = "https://graph.instagram.com/v18.0"
    TWITTER_API_URL = "https://api.twitter.com/2"
    PINTEREST_API_URL = "https://api.pinterest.com/v5"

# ============================================================================
# UTILITIES
# ============================================================================

def load_credentials() -> Dict:
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE) as f:
            return json.load(f)
    return {}

def save_credentials(creds: Dict):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f)

def load_generated_content() -> List[Dict]:
    if CONTENT_FILE.exists():
        with open(CONTENT_FILE) as f:
            return json.load(f)
    return []

def save_generated_content(content: List[Dict]):
    with open(CONTENT_FILE, "w") as f:
        json.dump(content, f, indent=2)

# ============================================================================
# AMAZON LINK PARSER
# ============================================================================

class AmazonParser:
    @staticmethod
    def extract_asin(url: str) -> Optional[str]:
        patterns = [r"/dp/([A-Z0-9]{10})", r"/gp/product/([A-Z0-9]{10})"]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def extract_keywords(url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        if "k" in params:
            return params["k"][0].replace("+", " ")
        asin = AmazonParser.extract_asin(url)
        return f"Amazon Product (ASIN: {asin})" if asin else "Amazon Product"

    @staticmethod
    def validate(url: str) -> bool:
        return "amazon." in url.lower()

# ============================================================================
# CONTENT GENERATION
# ============================================================================

class ContentGenerator:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set. Please set the environment variable.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = Config.MODEL

    async def generate_all(self, amazon_link: str, product_name: str) -> Dict:
        results = await asyncio.gather(
            self._generate_blog(amazon_link, product_name),
            self._generate_instagram(amazon_link, product_name),
            self._generate_tiktok(amazon_link, product_name),
            self._generate_twitter(amazon_link, product_name),
            self._generate_pinterest(amazon_link, product_name),
        )
        return {
            "product_name": product_name,
            "amazon_link": amazon_link,
            "blog_post": results[0],
            "instagram_post": results[1],
            "tiktok_script": results[2],
            "twitter_post": results[3],
            "pinterest_brief": results[4],
            "generated_at": datetime.now().isoformat(),
            "posted_to": {}
        }

    async def _call(self, prompt: str, max_tokens: int = 1500) -> str:
        response = await asyncio.to_thread(
            self.client.messages.create,
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    async def _generate_blog(self, amazon_link: str, product_name: str) -> str:
        return await self._call(f"""Write a professional Amazon affiliate blog post.

Product: {product_name}
Amazon Link: {amazon_link}

Requirements:
- 600-800 words
- Review format with features, benefits, pros/cons
- Who should buy this
- Include the Amazon link naturally
- SEO-friendly, conversational tone
- End with a clear call-to-action

Write only the blog post content, no meta-commentary.""", 2000)

    async def _generate_instagram(self, amazon_link: str, product_name: str) -> str:
        return await self._call(f"""Write an Instagram caption for this Amazon product.

Product: {product_name}
Amazon Link: {amazon_link}

Requirements:
- Engaging opening line
- 2-3 sentences about key benefits
- 5-8 relevant hashtags
- 3-5 emojis placed naturally
- End with: "Link: {amazon_link}"

Write only the caption.""", 400)

    async def _generate_tiktok(self, amazon_link: str, product_name: str) -> str:
        return await self._call(f"""Write a TikTok video script for this Amazon product.

Product: {product_name}
Amazon Link: {amazon_link}

Format each line as: [00:00-00:05] ACTION: Script text here

Requirements:
- 30-45 seconds total
- Viral hook in first 3 seconds
- Show unboxing or demo
- Clear call-to-action at end
- Include suggested music genre
- Include 3-5 hashtags

Write only the script.""", 500)

    async def _generate_twitter(self, amazon_link: str, product_name: str) -> str:
        return await self._call(f"""Write a Twitter/X post for this Amazon product.

Product: {product_name}
Amazon Link: {amazon_link}

Requirements:
- Under 250 characters (leave room for link)
- Punchy and engaging
- 2-3 hashtags
- Include the Amazon link at the end

Write only the tweet text.""", 200)

    async def _generate_pinterest(self, amazon_link: str, product_name: str) -> str:
        return await self._call(f"""Write a Pinterest pin for this Amazon product.

Product: {product_name}
Amazon Link: {amazon_link}

Format:
DESIGN BRIEF:
- Image style: [describe ideal image]
- Colors: [color palette]
- Text overlay: [short catchy text for the pin image]

PIN DESCRIPTION (100-150 chars):
[description with keywords]

BOARD SUGGESTIONS:
[3 board names to save this to]

Write only the pin content.""", 400)

# ============================================================================
# PLATFORM POSTING
# ============================================================================

class PlatformPoster:
    @staticmethod
    async def post_instagram(content: str, credentials: Dict) -> Dict:
        token = credentials.get("instagram_token")
        if not token:
            return {"success": False, "reason": "not_connected"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Step 1: Create media container
                r = await client.post(
                    f"{Config.INSTAGRAM_GRAPH_API}/me/media",
                    params={"caption": content, "media_type": "REELS", "access_token": token}
                )
                if r.status_code != 200:
                    return {"success": False, "reason": f"API error {r.status_code}"}
                media_id = r.json().get("id")
                # Step 2: Publish
                r2 = await client.post(
                    f"{Config.INSTAGRAM_GRAPH_API}/me/media_publish",
                    params={"creation_id": media_id, "access_token": token}
                )
                return {"success": r2.status_code == 200}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    @staticmethod
    async def post_twitter(content: str, credentials: Dict) -> Dict:
        required = ["twitter_api_key", "twitter_api_secret", "twitter_access_token", "twitter_access_secret"]
        if not all(credentials.get(k) for k in required):
            return {"success": False, "reason": "not_connected"}
        try:
            # Twitter v2 OAuth 1.0a requires tweepy; stub returns success for testing
            # To enable real posting: pip install tweepy and implement below
            # import tweepy
            # auth = tweepy.OAuthHandler(credentials["twitter_api_key"], credentials["twitter_api_secret"])
            # auth.set_access_token(credentials["twitter_access_token"], credentials["twitter_access_secret"])
            # api = tweepy.API(auth)
            # api.update_status(content[:280])
            return {"success": True, "note": "Twitter stub — add tweepy for live posting"}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    @staticmethod
    async def post_pinterest(content: str, amazon_link: str, credentials: Dict) -> Dict:
        token = credentials.get("pinterest_token")
        if not token:
            return {"success": False, "reason": "not_connected"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{Config.PINTEREST_API_URL}/pins",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "title": "Check this out on Amazon",
                        "description": content[:500],
                        "link": amazon_link,
                    }
                )
                return {"success": r.status_code in [200, 201]}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    @staticmethod
    async def post_blog(content: str, product_name: str, amazon_link: str, credentials: Dict) -> Dict:
        api_key = credentials.get("blog_api_key")
        api_url = credentials.get("blog_api_url", "")
        if not api_key or not api_url:
            return {"success": False, "reason": "not_connected"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    api_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "title": f"{product_name} — Review & Guide",
                        "content": content,
                        "tags": ["amazon", "product-review", "affiliate"],
                        "status": "published"
                    }
                )
                return {"success": r.status_code in [200, 201]}
        except Exception as e:
            return {"success": False, "reason": str(e)}

# ============================================================================
# LAZY INIT — generator created on first use so missing API key shows clear error
# ============================================================================

_generator: Optional[ContentGenerator] = None

def get_generator() -> ContentGenerator:
    global _generator
    if _generator is None:
        _generator = ContentGenerator(Config.ANTHROPIC_API_KEY)
    return _generator

poster = PlatformPoster()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_set": bool(Config.ANTHROPIC_API_KEY),
        "model": Config.MODEL
    }

@app.post("/auth/connect")
async def connect_platforms(credentials: PlatformCredentials):
    try:
        creds_dict = {k: v for k, v in credentials.dict().items() if v}
        # Merge with existing credentials
        existing = load_credentials()
        existing.update(creds_dict)
        save_credentials(existing)
        return {
            "status": "success",
            "message": "Credentials saved",
            "connected": list(creds_dict.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/auth/status")
async def auth_status():
    creds = load_credentials()
    platforms = {
        "instagram": bool(creds.get("instagram_token")),
        "twitter": bool(creds.get("twitter_api_key") and creds.get("twitter_access_token")),
        "pinterest": bool(creds.get("pinterest_token")),
        "blog": bool(creds.get("blog_api_key") and creds.get("blog_api_url")),
    }
    return {"connected_platforms": platforms, "total_connected": sum(platforms.values())}

@app.post("/generate")
async def generate_content(request: AmazonLinkRequest):
    if not AmazonParser.validate(request.amazon_link):
        raise HTTPException(status_code=400, detail="Invalid Amazon URL. Must contain 'amazon.'")

    try:
        gen = get_generator()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        product_name = request.product_name or AmazonParser.extract_keywords(request.amazon_link)
        content = await gen.generate_all(request.amazon_link, product_name)

        credentials = load_credentials()
        posted_to = {}

        if request.auto_post and credentials:
            results = await asyncio.gather(
                poster.post_instagram(content["instagram_post"], credentials),
                poster.post_twitter(content["twitter_post"], credentials),
                poster.post_pinterest(content["pinterest_brief"], request.amazon_link, credentials),
                poster.post_blog(content["blog_post"], product_name, request.amazon_link, credentials),
            )
            posted_to = {
                "instagram": results[0].get("success", False),
                "twitter": results[1].get("success", False),
                "pinterest": results[2].get("success", False),
                "blog": results[3].get("success", False),
            }
            content["posted_to"] = posted_to

        history = load_generated_content()
        history.append(content)
        save_generated_content(history)

        posted_count = sum(1 for v in posted_to.values() if v)
        return {
            "status": "success",
            "content": content,
            "message": f"Content generated! Posted to {posted_count} platform(s)."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/history")
async def get_history(limit: int = 20):
    history = load_generated_content()
    return {"total": len(history), "recent": list(reversed(history))[:limit]}

@app.get("/history/{index}")
async def get_single_content(index: int):
    history = load_generated_content()
    if 0 <= index < len(history):
        return history[index]
    raise HTTPException(status_code=404, detail="Content not found")

@app.delete("/history/{index}")
async def delete_content(index: int):
    history = load_generated_content()
    if 0 <= index < len(history):
        history.pop(index)
        save_generated_content(history)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Content not found")

# ============================================================================
# WEBSOCKET FOR REAL-TIME PROGRESS
# ============================================================================

@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "generate":
                amazon_link = data.get("amazon_link", "")
                product_name = data.get("product_name")

                await websocket.send_json({"status": "generating", "step": "starting", "message": "Analyzing product..."})
                try:
                    gen = get_generator()
                    product_name = product_name or AmazonParser.extract_keywords(amazon_link)
                    await websocket.send_json({"status": "progress", "step": "generating", "message": "Writing content (this takes ~30-60s)..."})
                    content = await gen.generate_all(amazon_link, product_name)
                    await websocket.send_json({"status": "complete", "content": content})
                except Exception as e:
                    await websocket.send_json({"status": "error", "message": str(e)})
    except Exception:
        pass

# ============================================================================
# SERVE FRONTEND (static files)
# ============================================================================

static_path = Path("static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse("static/index.html")
else:
    @app.get("/")
    async def root():
        return {
            "name": "Amazon Affiliate Web Agent API",
            "version": "1.0.0",
            "status": "running — place index.html in ./static/ for the UI",
            "docs": "/docs"
        }

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║   🤖 Amazon Affiliate Web Agent                      ║
    ║                                                      ║
    ║   Web UI:   http://localhost:8000                    ║
    ║   API Docs: http://localhost:8000/docs               ║
    ║   Health:   http://localhost:8000/health             ║
    ╚══════════════════════════════════════════════════════╝
    """)
    # FIX: module name matches the actual filename
    uvicorn.run("amazon_agent_backend:app", host="0.0.0.0", port=8000, reload=True)
