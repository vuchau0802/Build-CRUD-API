# The Polite Scraper

## Target classification

- **Site:** [books.toscrape.com](https://books.toscrape.com)
- **Why this site:** It is an explicit practice sandbox — the site's own pages state "We love being scraped!" and "Warning! This is a demo website for web scraping purposes." This is about as direct a permission statement as a website can give.
- **Scope:** Only the first 3 catalogue pages (`page-1.html` through `page-3.html`) and the ~60 individual book pages linked from them. No other pages, categories, or site sections are touched.
- **Data collected:** Title, price, availability, star rating, description, and product URL for each book — publicly displayed, non-personal, catalogue data.
- **`robots.txt` check:** Requested `https://books.toscrape.com/robots.txt` once — the site returns a 404 (no robots file exists). A missing file is not itself permission; the site's own explicit "we love being scraped" language is what makes this appropriate, not the absence of a robots file.
- **I will not reuse this code on another site without checking its rules and terms first.**

## Politeness rules this scraper follows

- Identifies itself with an honest `User-Agent` header naming this project
- Sets a request timeout — never waits forever for a response
- Waits at least 500ms between real requests to the site
- Caches every fetched page locally, so repeated development runs read from disk instead of re-hitting the site
- Checks the HTTP status code before parsing anything; only `200` is treated as a successful fetch

## Status

Stage 0 complete — target classified, robots.txt checked, scope defined.
