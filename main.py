from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
import repository
from auth import supabase
from llm_enrich import EnrichRequest, EnrichResponse, enrich_stub, call_model, EnrichmentFailed
import os

app = FastAPI()
security_scheme = HTTPBearer()
print("Server running and connected to Supabase")

repository.init_db()


def get_current_user(request: Request, credentials = Depends(security_scheme)):
    token = credentials.credentials
    try:
        result = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if result is None or result.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return result.user


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

class AuthCredentials(BaseModel):
    email: str = ""
    password: str = ""

@app.post("/auth/signup", status_code=201, summary="Create a new user account")
def signup(creds: AuthCredentials):
    if not creds.email or not creds.password:
        raise HTTPException(status_code=400, detail="email and password are required")
    try:
        result = supabase.auth.sign_up({"email": creds.email, "password": creds.password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"user": result.user}

@app.post("/auth/login", summary="Authenticate and return a JWT")
def login(creds: AuthCredentials):
    if not creds.email or not creds.password:
        raise HTTPException(status_code=400, detail="email and password are required")
    try:
        result = supabase.auth.sign_in_with_password({"email": creds.email, "password": creds.password})
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token
    }

@app.get("/public/info", summary="Public info, no auth required")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile", summary="Get the logged-in user's profile")
def protected_profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at
    }


@app.post("/auth/logout", status_code=204, summary="End the current session")
def logout(user=Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass


@app.get("/protected/dashboard", summary="Example second protected route")
def protected_dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user.email}"}

@app.post("/enrich", response_model=EnrichResponse, summary="Enrich a scraped book record")
def enrich(request: EnrichRequest):
    if os.environ.get("LLM_STUB") == "1":
        return enrich_stub(request)
    try:
        return call_model(request)
    except EnrichmentFailed as e:
        raise HTTPException(status_code=422, detail=f"Model output could not be validated: {e}")