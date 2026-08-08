from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime

app = FastAPI()

def get_db():
    conn = sqlite3.connect("tasks.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    # Migration: if tasks.db already existed from before (no timestamp columns), add them.
    existing_cols = [row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "created_at" not in existing_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")
    if "updated_at" not in existing_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN updated_at TEXT")

    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        now = datetime.utcnow().isoformat()
        conn.executemany(
            "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
            [("Buy milk", 0, now, now), ("Write report", 0, now, now), ("Walk the dog", 1, now, now)]
        )
        conn.commit()
    conn.close()

init_db()

class TaskCreate(BaseModel):
    title: str = ""

@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tasks", summary="List tasks, with optional search/filter/sort")
def get_tasks(
    search: Optional[str] = Query(None, description="Filter tasks whose title contains this text"),
    done: Optional[bool] = Query(None, description="Filter by completion status"),
    sort: Optional[str] = Query(None, description="Set to 'title' to sort alphabetically")
):
    conn = get_db()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")
    if done is not None:
        query += " AND done = ?"
        params.append(1 if done else 0)
    if sort == "title":
        query += " ORDER BY title"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/stats", summary="Task statistics computed in SQL")
def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
    conn.close()
    return {"total": total, "done": done_count, "open": total - done_count}

@app.get("/tasks/{task_id}", summary="Get a single task by id")
def get_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return dict(row)

@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    now = datetime.utcnow().isoformat()
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (task.title, 0, now, now)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "title": task.title, "done": 0, "created_at": now, "updated_at": now}

@app.put("/tasks/{task_id}", summary="Update a task's title")
def update_task(task_id: int, updated: TaskCreate):
    if not updated.title or not updated.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    now = datetime.utcnow().isoformat()
    conn.execute("UPDATE tasks SET title = ?, updated_at = ? WHERE id = ?", (updated.title, now, task_id))
    conn.commit()
    updated_row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(updated_row)

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()