"""
FastAPI application for WeChat MP RSS Generator.
"""

import importlib.resources
import os
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel

from .data_loader import get_mps_with_puid
from .db_reader import get_messages_for_mp, has_articles_for_mp, batch_has_articles, batch_article_counts
from .rss_generator import generate_rss_feed
from .opml_generator import generate_opml


# Load config: prefer CONFIG_PATH env var, then current working directory
CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", Path.cwd() / "config.yaml"))
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


app = FastAPI(
    title="WeChat MP RSS Generator",
    description="Generate RSS feeds for WeChat public accounts",
    version="0.1.0"
)


# Hidden MP names - these will be excluded and always return "no articles"
HIDDEN_MP_NAMES = {"微信支付", "微信收款助手"}


# Cache for MP list (reloaded on startup or refresh)
_mp_cache: Optional[List[dict]] = None


def get_cached_mps(force_reload: bool = False) -> List[dict]:
    """Get MPs with caching. Excludes hidden MPs from HIDDEN_MP_NAMES."""
    global _mp_cache
    if _mp_cache is None or force_reload:
        all_mps = get_mps_with_puid(
            config["wxpy_pkl_path"],
            config["wxpy_puid_pkl_path"]
        )
        # Filter out hidden MPs
        _mp_cache = [mp for mp in all_mps if mp["name"] not in HIDDEN_MP_NAMES]
    return _mp_cache


class MPInfo(BaseModel):
    puid: str
    name: str
    signature: str


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


@app.get("/api/has-articles/{puid}")
async def check_has_articles(puid: str):
    """
    Check if a public account has any articles.
    
    Path params:
        puid: The puid of the public account
    
    Returns:
        {"has_articles": bool}
    """
    # Verify MP exists
    mps = get_cached_mps()
    mp_info = next((mp for mp in mps if mp["puid"] == puid), None)
    
    if not mp_info:
        raise HTTPException(status_code=404, detail=f"Public account with puid '{puid}' not found")
    
    has_articles = has_articles_for_mp(config["tgdata_db_path"], puid)
    
    return {"has_articles": has_articles}


@app.get("/api/has-articles-batch")
async def check_has_articles_batch():
    """
    Check all public accounts for articles in a single query.
    
    Returns:
        {puid: bool, ...} for all MPs
    """
    mps = get_cached_mps()
    puids = [mp["puid"] for mp in mps]
    
    result = batch_has_articles(config["tgdata_db_path"], puids)
    
    return result


@app.get("/api/article-counts-batch")
async def get_article_counts_batch():
    """
    Get article counts for all public accounts in a single query.
    
    Returns:
        {puid: count, ...} for all MPs
    """
    mps = get_cached_mps()
    puids = [mp["puid"] for mp in mps]
    
    result = batch_article_counts(config["tgdata_db_path"], puids)
    
    return result


class ExportOpmlRequest(BaseModel):
    puids: Optional[List[str]] = None


@app.post("/api/opml")
async def export_opml(request: Request, body: ExportOpmlRequest = None):
    """
    Export public accounts as OPML file for bulk import into RSS readers.
    
    Body (optional):
        puids: List of puids to export. If omitted or empty, exports all.
    
    Returns:
        OPML 2.0 XML file download
    """
    mps = get_cached_mps()
    
    # Filter by puids if provided
    if body and body.puids:
        puid_set = set(body.puids)
        mps = [mp for mp in mps if mp["puid"] in puid_set]
    
    base_url = str(request.base_url).rstrip("/")
    opml_xml = generate_opml(mps, base_url)
    
    return Response(
        content=opml_xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": "attachment; filename=wechat-mp-feeds.opml"
        }
    )


# Serve frontend
# Priority: FRONTEND_DIR env var > installed package > project relative path
def _get_frontend_dir() -> Path:
    """Locate frontend directory."""
    # 1. Environment variable override
    if env_dir := os.environ.get("FRONTEND_DIR"):
        return Path(env_dir)
    
    # 2. Try importlib.resources for installed package
    try:
        import frontend
        # Python 3.9+: use importlib.resources.files()
        frontend_path = importlib.resources.files(frontend)
        # Convert to Path if possible
        if hasattr(frontend_path, '_path'):
            return Path(frontend_path._path)
        # Fallback: use as_file for older Python
        with importlib.resources.as_file(frontend_path) as p:
            return Path(p)
    except (ImportError, TypeError):
        pass
    
    # 3. Fallback to project relative path (for development)
    return Path(__file__).resolve().parent.parent / "frontend"


FRONTEND_DIR = _get_frontend_dir()


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
