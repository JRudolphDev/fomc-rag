"""Download pages from the Fed site, caching raw HTML on disk so re-runs skip the network."""

import time
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import requests

USER_AGENT = "fomc-rag/0.1 (github.com/JRudolphDev/fomc-rag)"
TIMEOUT_SECONDS = 30
DELAY_SECONDS = 1.0


def fetch_cached(url: str, cache_dir: Path, refresh: bool = False) -> str:
    """
    Fetch a URL, caching the raw HTML in cache_dir.
    If refresh is False and the file exists, read it from disk instead of fetching.
    """
    path = cache_dir / PurePosixPath(urlparse(url).path).name

    if path.exists() and not refresh:
        return path.read_bytes().decode("utf-8-sig")
    response = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS
    )
    response.raise_for_status()

    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)

    time.sleep(DELAY_SECONDS)
    return response.content.decode("utf-8-sig")
