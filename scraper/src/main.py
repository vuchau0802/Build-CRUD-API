from datetime import datetime, timezone
import re
import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pydantic import BaseModel, ValidationError
import json


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
    """Fetch catalogue pages 1-3, following 'next' links, and return (url, source_page) pairs."""
    base_url = "https://books.toscrape.com/catalogue/page-1.html"
    all_pairs = []
    current_url = base_url
    page_num = 1

    while page_num <= 3:
        cache_name = f"catalogue-page-{page_num}.html"
        html = fetch(current_url, cache_name)
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.select("h3 a"):
            href = link.get("href")
            absolute_url = urljoin(current_url, href)
            all_pairs.append((absolute_url, current_url))

        next_link = soup.select_one("li.next a")
        if next_link and page_num < 3:
            current_url = urljoin(current_url, next_link.get("href"))
            page_num += 1
        else:
            break

    seen = set()
    unique_pairs = []
    for url, source in all_pairs:
        if url not in seen:
            seen.add(url)
            unique_pairs.append((url, source))
    return unique_pairs

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

class BookRecord(BaseModel):
    title: str
    product_url: str
    price_gbp: float
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None
    source_page: str
    fetched_at: str


def normalize_price(price_text: str) -> float:
    """Turn '£51.77' into 51.77"""
    cleaned = price_text.replace("£", "").replace(",", "").strip()
    return float(cleaned)


def normalize_and_validate(raw_record: dict) -> BookRecord:
    """Convert a raw record into a validated BookRecord, or raise ValidationError."""
    price_gbp = normalize_price(raw_record["price_text"])
    return BookRecord(
        title=raw_record["title"],
        product_url=raw_record["product_url"],
        price_gbp=price_gbp,
        price_text=raw_record["price_text"],
        availability_text=raw_record["availability_text"],
        rating_text=raw_record["rating_text"],
        description=raw_record["description"],
        source_page=raw_record["source_page"],
        fetched_at=raw_record["fetched_at"]
    )

if __name__ == "__main__":
    pairs = discover_book_urls()
    print(f"catalogue_pages=3 discovered={len(pairs)} unique_urls={len(pairs)}")

    raw_records = []
    for url, source_page in pairs:
        record = extract_book(url, source_page)
        raw_records.append(record)

    print(f"detail_pages={len(raw_records)}")

    valid_records = []
    invalid_records = []
    seen_urls = set()

    for raw in raw_records:
        if raw["product_url"] in seen_urls:
            continue
        seen_urls.add(raw["product_url"])
        try:
            validated = normalize_and_validate(raw)
            valid_records.append(validated.model_dump())
        except (ValidationError, ValueError) as e:
            invalid_records.append({"record": raw, "reason": str(e)})

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "books.json", "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open(output_dir / "errors.json", "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, indent=2, ensure_ascii=False)

    print(f"valid={len(valid_records)} invalid={len(invalid_records)}")