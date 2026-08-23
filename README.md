# Task API

A CRUD API for managing a to-do list, built with FastAPI as part of the FlyRank Backend AI Engineering internship. The project has evolved through three storage backends while its endpoints stayed identical:
 
1. **In-memory** — data lost on restart
2. **SQLite** — data in a single file, survives a restart
3. **PostgreSQL in Docker** — a real database server, running in a container alongside the app, started together with one command

## What this is

A REST API supporting Create, Read, Update, and Delete operations on a list of tasks, now backed by PostgreSQL running in Docker.

## Architecture
 
Database logic lives entirely in `repository.py` — a single module implementing `get_db()` and `init_db()`. `main.py`'s routes call these functions but contain no direct database connection logic themselves. This separation is what let the storage swap from SQLite to Postgres happen without changing a single route's behavior or shape.
 
## How to run it
 
**Requires:** Docker Desktop (or Podman) installed and running.
 
1. Copy the example environment file:
```bash
cp .env.example .env
```
 
2. Start the whole stack (app + Postgres) with one command:
```bash
docker compose up
```
 
The `tasks` table is created automatically and seeded with 3 example tasks on first run. Visit `http://localhost:8000/docs` for interactive API documentation.
 
**Running without Docker** (for local development): install dependencies with `pip install -r requirements.txt --break-system-packages`, make sure a Postgres instance is reachable at the URL in `.env`, and run `uvicorn main:app --reload --port 8000`.

## Environment variables
 
See `.env.example`. Only one variable is required:
 
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string. Inside `docker compose`, the host is `db` (the service name); when running locally outside Docker, it's `localhost`. |
 
`.env` is git-ignored — never commit real credentials.
 
## Endpoints
 
| Method | Path | Description | Success code |
|--------|------|-------------|--------------|
| GET | `/` | API info | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List all tasks (supports `?search=`, `?done=`, `?sort=title`) | 200 |
| GET | `/tasks/{task_id}` | Get one task | 200 (404 if not found) |
| POST | `/tasks` | Create a task | 201 (400 if title missing/empty) |
| PUT | `/tasks/{task_id}` | Update a task's title | 200 (404 if not found, 400 if invalid) |
| DELETE | `/tasks/{task_id}` | Delete a task | 204 (404 if not found) |
| GET | `/stats` | Task counts (total/done/open), computed in SQL | 200 |
 
## Example request
 
```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://localhost:8000/tasks -Method POST -Body '{"title":"Buy milk"}' -ContentType "application/json"
```

```
StatusCode        : 201
StatusDescription : Created
Content           : {"id":5,"title":"Buy milk","done":false}
RawContent        : HTTP/1.1 201 Created
                    Content-Length: 40
                    Content-Type: application/json
                    Date: Sun, 23 Aug 2026 21:41:00 GMT
                    Server: uvicorn

                    {"id":5,"title":"Buy milk","done":false}
Forms             :
Headers           : {[Content-Length, 40], [Content-Type, application/json], [Date, Sun, 23 Aug 2026 21:41:00 GMT],
                    [Server, uvicorn]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        :
RawContentLength  : 40
```

## Persistence proof

Created a task via POST, then ran a full `docker compose down` followed by `docker compose up` — a complete teardown and rebuild of both containers, not just a restart. The task was still present afterward, proving the named Docker volume (`taskdata`) — not the container itself — is what holds the actual data.

## Viewing the database directly
 
```bash
docker exec -it taskdb psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```
 
```
 id |            title             | done
----+-------------------------------+------
  1 | Buy milk                      | f
  2 | Write report                  | f
  3 | Walk the dog                  | t
  4 | Compose persistence test      | f
```

## A debugging note worth keeping
 
The default `postgres:latest` image (Postgres 18) uses a different internal data directory layout than the `-v taskdata:/var/lib/postgresql/data` mount convention this assignment uses, and fails to start with that mount path. Pinning to `postgres:16` fixed it. Separately, the app container initially raced ahead of the database container — `depends_on` alone only waits for the container to *start*, not for Postgres to finish initializing inside it — fixed by adding a `healthcheck` (`pg_isready`) to the `db` service and changing `depends_on` to require `condition: service_healthy`.
 
## Exploring the database directly

Opened `tasks.db` in DB Browser for SQLite and ran several queries by hand, including:

```sql
SELECT * FROM tasks;
SELECT * FROM tasks WHERE done = 1;
SELECT COUNT(*) FROM tasks;
UPDATE tasks SET done = 1;
DELETE FROM tasks WHERE done = 1;
```

Running `UPDATE` without a `WHERE` clause marked every task as done, so the following `DELETE` removed all of them — a direct demonstration of why unscoped `UPDATE`/`DELETE` statements are dangerous in a real system. `GET /tasks` on the running API reflected the empty table instantly, with no restart needed, proving the API and DB Browser read the exact same file with no syncing step in between.

**Example query:**
```sql
SELECT COUNT(*) FROM tasks;
```
**Result:** `0` — returned after running `UPDATE tasks SET done = 1;` followed by `DELETE FROM tasks WHERE done = 1;` on the seeded table. The `UPDATE` had no `WHERE` clause, so it marked every task as done, and the following `DELETE` removed all of them — a direct demonstration of why unscoped `UPDATE`/`DELETE` statements are dangerous in a real system.
 
`GET /tasks` on the running API reflected the empty table instantly, with no restart needed, proving the API and DB Browser read the exact same file with no syncing step in between.

## Swagger UI

![Swagger UI screenshot](Swagger.png)

## Database viewer

![DB Browser screenshot](DBBrowser.png)

