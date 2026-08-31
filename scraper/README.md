# The Polite Scraper

A small, polite scraping pipeline that downloads the first three catalogue pages of Books to Scrape, visits all 60 book pages, turns messy HTML into clean, checked JSON records, survives a broken page without crashing, and ends every run with an honest report.

## Target classification

- **Site:** [books.toscrape.com](https://books.toscrape.com)
- **Why this site:** It is an explicit practice sandbox — the site's own pages state "We love being scraped!" and "Warning! This is a demo website for web scraping purposes." This is about as direct a permission statement as a website can give.
- **Scope:** Only the first 3 catalogue pages (`page-1.html` through `page-3.html`) and the 60 individual book pages linked from them. No other pages, categories, or site sections are touched.
- **Data collected:** Title, price, availability, star rating, description, and product URL for each book — publicly displayed, non-personal, catalogue data.
- **`robots.txt` check:** Requested `https://books.toscrape.com/robots.txt` once — the site returns a 404 (no robots file exists). A missing file is not itself permission; the site's own explicit "we love being scraped" language is what makes this appropriate, not the absence of a robots file.
- **I will not reuse this code on another site without checking its rules and terms first.**

## Politeness rules this scraper follows

- Identifies itself with an honest `User-Agent` header naming this project and linking to the repo
- Sets a 10-second request timeout — never waits forever for a response
- Waits at least 500ms between real requests to the site
- Caches every fetched page locally in `cache/`, so repeated development runs read from disk instead of re-hitting the site
- Checks the HTTP status code before parsing anything; only `200` is treated as a successful fetch
- No browser was used or needed — the data is already present in the server-rendered HTML, so a headless browser would only add cost with no benefit here

## How to run it

```bash
pip install -r requirements.txt
python src/main.py
```

Output:
- `output/books.json` — 60 validated book records
- `output/errors.json` — any records that failed schema validation, with a reason
- `output/run-report.json` — honest counts from the run

Re-running the script produces the same 60 records, not 120 — the identity check on `product_url` prevents duplicates, and cached pages are reused instead of re-fetched.

## Record schema

Each validated record in `books.json` has:

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | |
| `product_url` | string | Absolute URL, used as the record's canonical identity |
| `price_gbp` | number | Normalized from `price_text`, e.g. `51.77` |
| `price_text` | string | Original raw text, e.g. `"£51.77"` — kept alongside the clean value |
| `availability_text` | string | e.g. `"In stock (22 available)"` |
| `rating_text` | string | e.g. `"Three"` — extracted from a CSS class name, not visible text |
| `description` | string or null | `null` when a book genuinely has no description on the page — never invented |
| `source_page` | string | Which of the 3 catalogue pages this book was discovered on |
| `fetched_at` | string | ISO 8601 UTC timestamp of when this record was fetched |

## Proof of surviving a broken page

Deliberately added one fake book URL (`this-book-does-not-exist_9999`) to the discovered list and ran the scraper. The fake URL correctly failed with a `404`, was logged and skipped, and the run still completed with all 60 real records intact:

```
FETCH: https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html
FAILED: https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html (Failed to fetch https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html: status 404)
detail_pages=60 failed_pages=1
valid=60 invalid=0 failed_pages=1
```

The fake URL was removed after this test; it is not part of the permanent code.

## Sample run report

A clean run's actual `output/run-report.json`:

```json
{
  "started_at": "2026-08-31T01:07:18.681226+00:00",
  "duration_seconds": 0.39,
  "catalogue_pages_fetched": 3,
  "detail_pages_attempted": 60,
  "detail_pages_succeeded": 60,
  "failed_pages": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "cache_files_present": 63
}
```

(Duration is under a second here because this run read entirely from cache — a genuinely fresh, uncached run against the live site takes roughly 30-60 seconds, due to the deliberate 500ms politeness delay between the 63 real requests.)

## Ethics note

This scraper only touches a site explicitly built and offered for scraping practice. In general: use an official API when one exists rather than scraping; never bypass logins, paywalls, or explicit blocks; collect only the data actually needed for the stated purpose; and re-check a site's rules and terms before reusing any of this code elsewhere.
