"""
FastAPI application for WeChat MP RSS Generator.
"""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel

from .data_loader import get_mps_with_puid
from .db_reader import get_messages_for_mp
from .rss_generator import generate_rss_feed


# Load config: prefer CONFIG_PATH env var, then current working directory
CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", Path.cwd() / "config.yaml"))
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


app = FastAPI(
    title="WeChat MP RSS Generator",
    description="Generate RSS feeds for WeChat public accounts",
    version="0.1.0"
)


# Cache for MP list (reloaded on startup or refresh)
_mp_cache: Optional[List[dict]] = None


def get_cached_mps(force_reload: bool = False) -> List[dict]:
    """Get MPs with caching."""
    global _mp_cache
    if _mp_cache is None or force_reload:
        _mp_cache = get_mps_with_puid(
            config["wxpy_pkl_path"],
            config["wxpy_puid_pkl_path"]
        )
    return _mp_cache


class MPInfo(BaseModel):
    puid: str
    name: str
    signature: str
    head_img: str


@app.get("/api/mps", response_model=List[MPInfo])
async def list_mps(refresh: bool = False):
    """
    Get list of all available public accounts.
    
    Query params:
        refresh: Force reload from pkl files
    """
    mps = get_cached_mps(force_reload=refresh)
    return mps


@app.get("/api/rss/{puid}")
async def get_rss_feed(puid: str, request: Request, limit: int = 100):
    """
    Get RSS feed for a specific public account.
    
    Path params:
        puid: The puid of the public account
    
    Query params:
        limit: Maximum number of items (default: 100)
    """
    # Find MP info
    mps = get_cached_mps()
    mp_info = next((mp for mp in mps if mp["puid"] == puid), None)
    
    if not mp_info:
        raise HTTPException(status_code=404, detail=f"Public account with puid '{puid}' not found")
    
    # Get messages
    messages = get_messages_for_mp(
        config["tgdata_db_path"],
        puid,
        limit=limit
    )
    
    # Generate RSS feed
    feed_url = str(request.url)
    rss_xml = generate_rss_feed(
        mp_name=mp_info["name"],
        mp_signature=mp_info["signature"],
        messages=messages,
        feed_url=feed_url
    )
    
    return Response(
        content=rss_xml,
        media_type="application/rss+xml; charset=utf-8"
    )


# Serve frontend
# Default to frontend/ directory relative to this module's parent (project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", _PROJECT_ROOT / "frontend"))


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the frontend index.html"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)


@app.get("/style.css")
async def serve_css():
    """Serve CSS file"""
    css_path = FRONTEND_DIR / "style.css"
    if css_path.exists():
        return Response(
            content=css_path.read_text(encoding="utf-8"),
            media_type="text/css"
        )
    raise HTTPException(status_code=404, detail="CSS not found")


def main():
    """Run the server."""
    import uvicorn
    
    host = config.get("server", {}).get("host", "0.0.0.0")
    port = config.get("server", {}).get("port", 8080)
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
