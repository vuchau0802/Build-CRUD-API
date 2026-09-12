import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "report.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_report_data() -> dict:
    conn = get_db()

    total_books = conn.execute("SELECT COUNT(*) AS count FROM books").fetchone()["count"]

    average_price = conn.execute("SELECT AVG(price) AS avg_price FROM books").fetchone()["avg_price"]

    top_5_expensive = conn.execute(
        "SELECT title, price FROM books ORDER BY price DESC LIMIT 5"
    ).fetchall()
    top_5_expensive = [dict(row) for row in top_5_expensive]

    books_per_rating = conn.execute(
        "SELECT rating, COUNT(*) AS count FROM books GROUP BY rating ORDER BY rating"
    ).fetchall()
    books_per_rating = [dict(row) for row in books_per_rating]

    conn.close()

    return {
        "total_books": total_books,
        "average_price": round(average_price, 2) if average_price else 0,
        "top_5_expensive": top_5_expensive,
        "books_per_rating": books_per_rating,
    }


if __name__ == "__main__":
    import json
    data = get_report_data()
    print(json.dumps(data, indent=2))