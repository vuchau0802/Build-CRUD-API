import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    count = conn.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
    if count == 0:
        conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s), (%s, %s), (%s, %s)",
            ("Buy milk", False, "Write report", False, "Walk the dog", True)
        )
    conn.commit()
    conn.close()