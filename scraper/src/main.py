from datetime import datetime, timezone
import re
import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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
    response.encoding = response.apparent_encoding

    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url}: status {response.status_code}")

    cache_path.write_text(response.text, encoding="utf-8")
    print(f"FETCH complete: {cache_name} ({len(response.text)} bytes)")

    time.sleep(DELAY)
    return response.text

def discover_book_urls():
    """Fetch catalogue pages 1-3, following 'next' links, and return all unique book URLs."""
    base_url = "https://books.toscrape.com/catalogue/page-1.html"
    all_urls = []
    current_url = base_url
    page_num = 1

    while page_num <= 3:
        cache_name = f"catalogue-page-{page_num}.html"
        html = fetch(current_url, cache_name)
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.select("h3 a"):
            href = link.get("href")
            absolute_url = urljoin(current_url, href)
            all_urls.append(absolute_url)

        next_link = soup.select_one("li.next a")
        if next_link and page_num < 3:
            current_url = urljoin(current_url, next_link.get("href"))
            page_num += 1
        else:
            break

    unique_urls = list(dict.fromkeys(all_urls))  # de-dupe, preserve order
    return unique_urls

def extract_book(url: str, source_page: str) -> dict:
    """Fetch one book detail page and extract its raw fields."""
    # Use a safe filename derived from the URL for caching
    cache_name = re.sub(r"[^a-zA-Z0-9]+", "_", url) + ".html"
    html = fetch(url, cache_name)
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("div.product_main h1").get_text(strip=True)

    price_text = soup.select_one("p.price_color").get_text(strip=True)

    availability_text = soup.select_one("p.availability").get_text(strip=True)

    rating_tag = soup.select_one("p.star-rating")
    rating_classes = rating_tag.get("class", [])
    rating_text = next((c for c in rating_classes if c != "star-rating"), None)

    description_tag = soup.select_one("#product_description ~ p")
    description = description_tag.get_text(strip=True) if description_tag else None

    return {
        "title": title,
        "product_url": url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    urls = discover_book_urls()
    print(f"catalogue_pages=3 discovered={len(urls)} unique_urls={len(urls)}")

    records = []
    for url in urls:
        record = extract_book(url, "https://books.toscrape.com/catalogue/page-1.html")
        records.append(record)

    print(f"detail_pages={len(records)}")
    print(records[0])