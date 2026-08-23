from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import repository

app = FastAPI()

repository.init_db()


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
    return repository.list_tasks(search=search, done=done, sort=sort)


@app.get("/stats", summary="Task statistics computed in SQL")
def get_stats():
    return repository.get_stats()


@app.get("/tasks/{task_id}", summary="Get a single task by id")
def get_task(task_id: int):
    row = repository.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    return repository.create_task(task.title)


@app.put("/tasks/{task_id}", summary="Update a task's title")
def update_task(task_id: int, updated: TaskCreate):
    if not updated.title or not updated.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    row = repository.update_task(task_id, updated.title)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    deleted = repository.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")