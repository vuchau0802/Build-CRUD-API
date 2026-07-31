# Task API

A small in-memory CRUD API for managing a to-do list, built with FastAPI as part of the FlyRank Backend AI Engineering internship (Week 2, Assignment BE-01).

## What this is

A REST API that supports Create, Read, Update, and Delete operations on a list of tasks. Data is stored in memory only — it resets whenever the server restarts.

## How to run it

1. Install dependencies:
```bash
pip install fastapi uvicorn --break-system-packages
```

2. Start the server:
```bash
uvicorn main:app --reload --port 8000
```

3. Visit `http://localhost:8000/docs` for interactive API documentation.

## Endpoints

| Method | Path | Description | Success code |
|--------|------|-------------|--------------|
| GET | `/` | API info | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List all tasks | 200 |
| GET | `/tasks/{task_id}` | Get one task | 200 (404 if not found) |
| POST | `/tasks` | Create a task | 201 (400 if title missing/empty) |
| PUT | `/tasks/{task_id}` | Update a task's title | 200 (404 if not found, 400 if invalid) |
| DELETE | `/tasks/{task_id}` | Delete a task | 204 (404 if not found) |

## Example request

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://localhost:8000/tasks -Method POST -Body '{"title":"Buy milk"}' -ContentType "application/json"
```

```
StatusCode        : 201
StatusDescription : Created
Content           : {"id":4,"title":"Buy milk","done":false}
RawContent        : HTTP/1.1 201 Created
                    Content-Length: 40
                    Content-Type: application/json
                    Date: Fri, 31 Jul 2026 16:56:48 GMT
                    Server: uvicorn

                    {"id":4,"title":"Buy milk","done":false}
Forms             :
Headers           : {[Content-Length, 40], [Content-Type, application/json], [Date, Fri, 31 Jul 2026 16:56:48
                    GMT], [Server, uvicorn]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        :
RawContentLength  : 40
```

## Swagger UI

![Swagger UI screenshot](Swagger.png)
