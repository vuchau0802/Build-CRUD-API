import requests
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/vuchau0802/Build-CRUD-API)"
TIMEOUT = 10  # seconds
DELAY = 0.5   # seconds between real requests


def fetch(url: str, cache_name: str) -> str:
    """Fetch a URL, using a local cache if available. Returns the HTML text."""
    cache_path = CACHE_DIR / cache_name

    if cache_path.exists():
        print(f"CACHE HIT: {cache_name} ({cache_path.stat().st_size} bytes)")
        return cache_path.read_text(encoding="utf-8")

    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url}: status {response.status_code}")

    cache_path.write_text(response.text, encoding="utf-8")
    print(f"FETCH complete: {cache_name} ({len(response.text)} bytes)")

    time.sleep(DELAY)
    return response.text


if __name__ == "__main__":
    html = fetch(
        "https://books.toscrape.com/catalogue/page-1.html",
        "catalogue-page-1.html"
    )
    print(f"Page 1 fetched, {len(html)} characters total.")