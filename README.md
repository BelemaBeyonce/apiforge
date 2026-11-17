# APIForge — Python Backend & AI Evaluation Lab

A Python 3.12+ backend portfolio project for backend engineering, AI engineering, and code evaluation interviews. Create coding tasks, define a reference rubric, submit inert text responses, and inspect reproducible weighted scores and persisted feedback.

The MVP evaluates **reference criteria**, not program correctness. It never executes submitted code and makes no LLM calls. A response containing `sorted` can satisfy a contains criterion even if its code is wrong. This deliberate limitation makes the evaluation behavior transparent, inexpensive, and safe to demonstrate.

## Features

- Versioned FastAPI REST API with create, read, replace, and delete task operations.
- Pydantic validation, bounded pagination, exact language/difficulty filters, consistent errors, request IDs.
- Weighted exact/contains rules, configurable case sensitivity, per-criterion feedback, scores from 0–100.
- SQLAlchemy persistence with SQLite locally and PostgreSQL via Psycopg; Alembic owns schema changes.
- Immutable evaluation snapshots capture rubric, task content, revision, and engine version.
- JSON application logs exclude submissions, query strings, credentials, and raw validation input.
- Interactive Swagger UI, ReDoc, sample tasks, repeatable API demo, automated tests, Docker, and GitHub Actions.

## Local quick start

Run from this repository root with Python 3.12 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
cp .env.example .env
alembic upgrade head
python -m examples.seed
uvicorn app.main:app --reload --no-access-log
```

Visit [Swagger UI](http://127.0.0.1:8000/docs), [ReDoc](http://127.0.0.1:8000/redoc), or [health](http://127.0.0.1:8000/api/v1/health). The OpenAPI schema is at `/openapi.json`. Reload is for development. Migrations are explicit; starting the app does not silently create tables. Do not run multiple concurrent migration processes.

The dependency lock files capture the versions used for this delivery; `pyproject.toml` defines supported ranges. Re-resolve and audit dependencies deliberately before a public deployment. Runtime dependencies are in `requirements.lock`; HTTPX and Pytest are development tools.

## Architecture

```mermaid
flowchart LR
    HTTP[HTTP / Swagger] --> API[Routes and Pydantic validation]
    API --> Service[Task business service]
    Service --> Engine[Deterministic evaluator]
    Service --> ORM[SQLAlchemy models and session]
    ORM --> DB[(SQLite / PostgreSQL)]
    Alembic[Alembic migrations] --> DB
```

| Component | Responsibility |
|---|---|
| `app/main.py` | App assembly, error envelopes, request IDs, completion logs |
| `app/api/routes.py` | HTTP routing, pagination and query filters |
| `app/schemas.py` | Input limits, criterion definitions, response schemas |
| `app/services/tasks.py` | Task writes, evaluation orchestration, snapshots and transactions |
| `app/services/evaluator.py` | Pure deterministic scoring with no execution or external calls |
| `app/models.py`, `app/database.py` | Persistence, request-scoped sessions, foreign key enforcement |
| `app/config.py`, `app/logging.py` | Environment settings and JSON application logging |
| `migrations/` | Explicit, reversible schema history |
| `tests/` | Unit, API and migration tests on isolated temporary databases |
| `examples/` | Sample tasks, idempotent seed command, repeatable demo |

A request receives its own database session. Services commit each write transaction; session teardown closes and rolls back uncommitted work after failure. Lists use ascending IDs for deterministic ordering. Task replacement increments a revision; prior evaluation snapshots stay unchanged. Task deletion intentionally cascades to all owned evaluations. Concurrent replacements currently use last-write-wins semantics.

## API at a glance

All data endpoints use `/api/v1`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Database connectivity/readiness |
| POST | `/tasks` | Create task (201) |
| GET | `/tasks` | List/filter tasks with `limit`, `offset`, `language`, `difficulty` |
| GET | `/tasks/{id}` | Read task |
| PUT | `/tasks/{id}` | Replace all editable fields |
| DELETE | `/tasks/{id}` | Delete task and evaluations (204) |
| POST | `/tasks/{id}/evaluations` | Evaluate a text response (201) |
| GET | `/tasks/{id}/evaluations` | Paginated task history |
| GET | `/evaluations/{id}` | Read evaluation and historical rubric |

See [complete API examples](docs/API.md), [database schema](docs/DATABASE.md), and [security boundaries](SECURITY.md).

## Tests and quality checks

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=90
ruff check .
ruff format --check .
alembic check
python -m examples.demo --in-process
```

The demo uses your configured, migrated database, creates a temporary task, checks scores and validation, and deletes that task afterward. To exercise a running HTTP server instead:

```bash
python -m examples.demo --url http://127.0.0.1:8000
```

Tests cover normal CRUD, filters, empty pages, Unicode case folding, score rounding, inert malicious-looking input, invalid payloads, unknown fields, missing resources, sanitized failures, snapshot retention, cascade deletion, and migration upgrade/downgrade/schema drift. See [executed verification results](docs/VERIFICATION.md). CI runs the suite, lint/format checks, PostgreSQL migration and API integration, and an image build. A workflow file does not imply a hosted GitHub run has occurred.

## Docker

```bash
docker compose up --build -d api
curl http://127.0.0.1:8000/api/v1/health
docker compose exec api python -m examples.seed
docker compose logs api
docker compose down
```

SQLite persists in a named volume; `down` preserves it. The container runs as an unprivileged user. Host binding defaults to loopback. The single-service Compose command migrates before starting; for a multi-replica deployment use a separate migration job.

For the PostgreSQL profile, set your own password (no default password is shipped):

```bash
read -s -p 'PostgreSQL password: ' POSTGRES_PASSWORD; echo
export POSTGRES_PASSWORD
docker compose --profile postgres up --build -d api-postgres
curl http://127.0.0.1:8001/api/v1/health
```

Set `POSTGRES_API_PORT=8011` if port 8001 is occupied. The default PostgreSQL username/database are `apiforge`. If you customize them, set `POSTGRES_DATABASE_URL=postgresql+psycopg://YOUR_USER@postgres:5432/YOUR_DB`. The password comes from `PGPASSWORD` inside the API container. For an externally managed database, set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB` in your local environment and run migrations before starting Uvicorn. URL-encode credentials; require TLS using provider-specific connection parameters. Never commit `.env`.

## Interview demonstration (about 7 minutes)

1. Explain the safe MVP boundary: text criteria are deterministic and reproducible, while code execution and semantic judging require additional infrastructure.
2. Open `/docs`, create a task using `examples/tasks.json`, and show Pydantic rejecting an invalid difficulty or empty rubric.
3. Submit `Use sorted for stable ordering.` to the stable-sorting task. Show 100 points, then submit `Use sorted.` and explain the 66.67 weighted score.
4. Replace the task title/rubric and retrieve an earlier evaluation. Show the stored revision and unchanged snapshot.
5. Filter tasks by `language=python&difficulty=easy`, request `limit=1&offset=1`, and show structured validation errors and request IDs.
6. Run the tests, explain fixture isolation and migration round trips, and trace route → service → pure evaluator → database.
7. Discuss tradeoffs: reference matching can be gamed; SQLite has limited write concurrency; authentication, rate limiting, sandbox workers, and calibrated LLM judges belong on the roadmap.

For a scripted demo, run `python -m examples.demo` while Uvicorn is running. Use [the roadmap](docs/ROADMAP.md) to discuss next steps. To publish, initialize a Git repository in this directory, review files, commit, and push to your own GitHub repository. No external repository or deployment is created by this deliverable.
