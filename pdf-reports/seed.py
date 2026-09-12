import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "report.db"
BOOKS_JSON_PATH = Path(__file__).parent.parent / "scraper" / "output" / "books.json"

RATING_WORDS_TO_NUMBERS = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def seed():
    if not BOOKS_JSON_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {BOOKS_JSON_PATH}. Run the A9 scraper first so books.json exists."
        )

    books = json.loads(BOOKS_JSON_PATH.read_text(encoding="utf-8"))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            rating INTEGER,
            url TEXT NOT NULL
        )
    """)

    # Delete-then-insert: makes running this script twice leave exactly one clean copy,
    # rather than doubling the row count.
    conn.execute("DELETE FROM books")

    rows = []
    for book in books:
        rating_word = book.get("rating_text")
        rating_number = RATING_WORDS_TO_NUMBERS.get(rating_word)
        rows.append((book["title"], book["price_gbp"], rating_number, book["product_url"]))

    conn.executemany(
        "INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    print(f"Seeded {count} books into {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    seed()