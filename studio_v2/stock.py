from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import re
import requests

MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024

def search_pexels(query: str, api_key: str, orientation: str = "portrait", per_page: int = 5) -> list[dict]:
    if not api_key:
        raise ValueError("Enter a Pexels API key in the Stock Footage settings.")
    response = requests.get(
        "https://api.pexels.com/v1/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "orientation": orientation, "per_page": max(1, min(per_page, 10))},
        timeout=(10, 45),
    )
    response.raise_for_status()
    rows = []
    for item in response.json().get("videos", []):
        files = item.get("video_files") or []
        files = [f for f in files if f.get("link") and f.get("file_type") == "video/mp4"]
        if not files:
            continue
        chosen = sorted(files, key=lambda f: (
            f.get("quality") == "hd",
            int(f.get("width") or 0) * int(f.get("height") or 0),
        ), reverse=True)[0]
        rows.append({
            "id": f"pexels-{item.get('id')}",
            "source": "Pexels",
            "title": f"Video by {item.get('user', {}).get('name', 'Pexels contributor')}",
            "creator": item.get("user", {}).get("name", "Unknown creator"),
            "credit_url": item.get("url", ""),
            "preview_url": item.get("image", ""),
            "download_url": chosen["link"],
            "duration": item.get("duration", 0),
            "width": chosen.get("width", 0),
            "height": chosen.get("height", 0),
        })
    return rows

def search_pixabay(query: str, api_key: str, per_page: int = 5) -> list[dict]:
    if not api_key:
        raise ValueError("Enter a Pixabay API key in the Stock Footage settings.")
    response = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": max(1, min(per_page, 10)), "safesearch": "true"},
        timeout=(10, 45),
    )
    response.raise_for_status()
    rows = []
    for item in response.json().get("hits", []):
        videos = item.get("videos") or {}
        chosen = videos.get("large") or videos.get("medium") or videos.get("small")
        if not chosen or not chosen.get("url"):
            continue
        rows.append({
            "id": f"pixabay-{item.get('id')}",
            "source": "Pixabay",
            "title": f"Video by {item.get('user', 'Pixabay contributor')}",
            "creator": item.get("user", "Unknown creator"),
            "credit_url": item.get("pageURL", ""),
            "preview_url": item.get("picture", ""),
            "download_url": chosen["url"],
            "duration": item.get("duration", 0),
            "width": chosen.get("width", 0),
            "height": chosen.get("height", 0),
        })
    return rows

def search_stock(provider: str, query: str, api_key: str, aspect_ratio: str) -> list[dict]:
    if not query.strip():
        raise ValueError("The scene needs a stock search phrase.")
    orientation = "portrait" if aspect_ratio == "9:16" else "landscape"
    if provider == "pexels":
        return search_pexels(query, api_key, orientation)
    if provider == "pixabay":
        return search_pixabay(query, api_key)
    raise ValueError("Choose Pexels or Pixabay for stock footage.")

def download_stock(item: dict, folder: str | Path) -> str:
    url = str(item.get("download_url") or "")
    parsed = urlparse(url)
    host = parsed.hostname or ""
    allowed = parsed.scheme == "https" and (
        host == "videos.pexels.com"
        or host == "cdn.pixabay.com"
        or host.endswith(".pexels.com")
    )
    if not allowed:
        raise ValueError("The selected download URL is not from an approved Pexels/Pixabay media host.")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(item.get("id", "stock")))[:60] + ".mp4"
    path = folder / safe_name
    total = 0
    with requests.get(url, stream=True, timeout=(15, 90)) as response:
        response.raise_for_status()
        with path.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    path.unlink(missing_ok=True)
                    raise ValueError("The selected stock clip exceeds the 300 MB safety limit.")
                output.write(chunk)
    if path.stat().st_size < 1024:
        path.unlink(missing_ok=True)
        raise RuntimeError("The stock provider returned an empty or invalid video file.")
    return str(path)
