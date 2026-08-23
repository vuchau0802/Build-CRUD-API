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


def list_tasks(search=None, done=None, sort=None):
    conn = get_db()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if search:
        query += " AND title LIKE %s"
        params.append(f"%{search}%")
    if done is not None:
        query += " AND done = %s"
        params.append(done)
    if sort == "title":
        query += " ORDER BY title"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_task(task_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    conn.close()
    return row


def create_task(title):
    conn = get_db()
    row = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
        (title, False)
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def update_task(task_id, title):
    conn = get_db()
    existing = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if existing is None:
        conn.close()
        return None
    row = conn.execute(
        "UPDATE tasks SET title = %s WHERE id = %s RETURNING *",
        (title, task_id)
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def delete_task(task_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if existing is None:
        conn.close()
        return False
    conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()
    return True


def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
    done_count = conn.execute("SELECT COUNT(*) AS count FROM tasks WHERE done = TRUE").fetchone()["count"]
    conn.close()
    return {"total": total, "done": done_count, "open": total - done_count}