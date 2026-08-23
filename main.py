from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from repository import get_db, init_db
from datetime import datetime

app = FastAPI()

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

@app.get("/stats", summary="Task statistics computed in SQL")
def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
    done_count = conn.execute("SELECT COUNT(*) AS count FROM tasks WHERE done = TRUE").fetchone()["count"]
    conn.close()
    return {"total": total, "done": done_count, "open": total - done_count}

@app.get("/tasks/{task_id}", summary="Get a single task by id")
def get_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row

@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    conn = get_db()
    row = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
        (task.title, False)
    ).fetchone()
    conn.commit()
    conn.close()
    return row

@app.put("/tasks/{task_id}", summary="Update a task's title")
def update_task(task_id: int, updated: TaskCreate):
    if not updated.title or not updated.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    updated_row = conn.execute(
        "UPDATE tasks SET title = %s WHERE id = %s RETURNING *",
        (updated.title, task_id)
    ).fetchone()
    conn.commit()
    conn.close()
    return updated_row

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()