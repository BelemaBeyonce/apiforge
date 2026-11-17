# APIForge — Python Backend & AI Evaluation Lab

APIForge is a Python backend portfolio project for creating coding tasks, evaluating **inert text** against weighted rubrics, and inspecting feedback over time. It combines authenticated REST APIs, portable relational persistence, reproducible baseline scoring, and an optional, genuinely integrated OpenAI-compatible feedback adapter.

It addresses a practical evaluation problem: preserve what was assessed, how a score was calculated, and who can inspect it. Deterministic rubric results and model-generated advice are separate records. Neither establishes that submitted code works. **Submitted code is never executed.**

## Features

- FastAPI/Pydantic APIs and interactive Swagger Bearer authentication.
- Argon2id password hashes, expiring JWTs, database-backed role/activation checks, and operator-only first-admin bootstrap.
- Admin, evaluator, and viewer roles; task ownership and explicit reader/editor grants; unauthorized resources return 404.
- Weighted exact, literal substring, and bounded regex criteria; category-normalized scoring and per-rule contributions.
- Revision-checked updates, archival instead of destructive deletion, immutable evaluation snapshots, comparison endpoints.
- Optional OpenAI-compatible integration with explicit external-transmission consent, structured output validation, bounded retries, and independent human review. A clearly labeled mock runs without a paid key.
- SQLite and PostgreSQL, data-preserving Alembic migrations, request IDs, JSON logs, explicit CORS, body limits, readiness/liveness.
- Automated tests, dependency audit, non-root Docker image, Compose, GitHub Actions, and a reproducible synthetic demonstration.

## Windows quick start

Install Git and Python **3.12+**, then use PowerShell from the repository root:

```powershell
git clone https://github.com/BelemaBeyonce/apiforge.git
cd apiforge
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
Copy-Item .env.example .env
$key = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
Add-Content .env "JWT_SECRET=$key"
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.bootstrap
.\.venv\Scripts\python.exe -m examples.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --no-access-log --no-proxy-headers
```

The bootstrap command prompts privately for the first administrator's password (12–128 characters). It never promotes a pre-existing registration and cannot create another bootstrap admin after completion. Additional admins/evaluators are assigned by an authenticated admin. Keep `.env` local. Invoking the venv executable directly avoids PowerShell activation-policy changes.

Open **http://127.0.0.1:8000/docs**. Register a viewer or log in using `POST /api/v1/auth/login`, copy its `access_token`, and click **Authorize** in Swagger (paste the token without the `Bearer` prefix). Use your bootstrap administrator for task creation, or promote a registered user to evaluator through `PUT /api/v1/users/{id}`. Re-login after any role/activation change because previous tokens are revoked.

For Linux/macOS, create `.venv` with `python3.12 -m venv .venv`, activate it, and run the same commands without the Windows executable prefixes. Generate the key using Python's `secrets.token_urlsafe(48)` and write it only to your local `.env`.

## Architecture

```mermaid
flowchart LR
    Client[Swagger or HTTP client] --> Limits[Body limits / CORS / request IDs]
    Limits --> Auth[JWT identity and role dependencies]
    Auth --> API[FastAPI routes and Pydantic schemas]
    API --> Tasks[Task service: access / revision checks]
    Tasks --> Baseline[Deterministic rubric evaluator]
    Tasks --> DB[(SQLAlchemy: SQLite or PostgreSQL)]
    API --> AI[Optional AI service]
    AI --> Provider[Mock or OpenAI-compatible provider]
    AI --> DB
    API --> Review[Independent human review]
    Review --> DB
    Alembic[Alembic migrations] --> DB
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for module responsibilities, access rules, transaction boundaries, and tradeoffs.

## Run tests and the demonstration

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-fail-under=90
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m examples.demo --in-process
```

The demo creates a **temporary database**, bootstraps synthetic users, exercises login/RBAC, weighted scoring, revision conflicts, comparison, mocked AI, independent review, and archival history, then removes the database. It makes no external model calls and prints no passwords or tokens. It uses an in-process HTTP client, not a publicly hosted website.

For the full API suite against PostgreSQL, set `APIFORGE_TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/TEST_DB` and run Pytest again. Each fixture creates/drops a unique schema; the database user must be allowed to create schemas. Use a **dedicated disposable test database**, never production. The test run also verifies upgrades from the original `0001` schema with existing task/evaluation rows. See [actual verification](docs/VERIFICATION.md).

## Docker

First copy `.env.example` to `.env` and generate a private `JWT_SECRET` as above:

```bash
docker compose up --build -d api
docker compose exec api python -m app.bootstrap
docker compose exec api python -m examples.seed
```

Swagger: port 8000. The image runs as a non-root user; SQLite persists in a named volume. For PostgreSQL, set your own `POSTGRES_PASSWORD` in `.env`, then run `docker compose --profile postgres up --build -d api-postgres`. That API uses port 8001 (`POSTGRES_API_PORT` can change it). Set a matching `POSTGRES_DATABASE_URL` if customizing the user/database. No database password is supplied in source. The PostgreSQL Compose service exposes no database port to the host.

For enterprise HTTPS proxies, the Dockerfile supports an optional BuildKit `pip_ca` secret containing the trusted CA bundle; TLS verification remains enabled. See [deployment instructions](docs/DEPLOYMENT.md).

## Optional AI evaluation

Disabled by default. To run the local mock, set `AI_ENABLED=true` and `AI_PROVIDER=mock` in development. It is visibly labeled synthetic and rejected in production settings.

For a real provider, set `AI_ENABLED=true`, `AI_PROVIDER=openai`, `AI_ALLOW_EXTERNAL=true`, and your own `AI_API_KEY`, `AI_BASE_URL`, and `AI_MODEL`. Requests also require `consent_to_external=true`. This transmits the stored task/rubric, submitted response, and deterministic feedback to that provider. Only enable it for data you are authorized to transmit.

The adapter calls `/chat/completions`, requests JSON-schema output, validates it, and records model, prompt version, timestamp, safe usage metadata, and failure categories. Real HTTP behavior is tested with mocked transports; **no paid/live provider evaluation is claimed**. Model support for structured outputs varies. See [AI integration](docs/AI_EVALUATION.md).

## API compatibility changes in 0.2

- All task/evaluation/user/AI data endpoints now require Bearer authentication. Public registration creates viewers only.
- Task replacement requires `expected_revision` in its complete PUT body; stale revisions return 409.
- `DELETE /tasks/{id}` requires an integer `If-Match` revision and archives the task. It returns 204 and preserves history; ordinary task reads/lists omit archived tasks. Authorized users can request `include_archived=true` and read history.
- Existing tasks keep their IDs, revisions, rubrics, scores, and evaluations. Legacy tasks without owners are visible only to admins. No account is silently granted access.
- New tasks/evaluations use category-aware `deterministic-v2`; stored `deterministic-v1` results are not recalculated. Regex timeout outcomes are flagged `completed_with_limits`.

## Documentation and portfolio demonstration

- [API examples and permission matrix](docs/API.md)
- [Database schema and migration policy](docs/DATABASE.md)
- [Security boundaries](SECURITY.md)
- [AI evaluation and human review](docs/AI_EVALUATION.md)
- [Deployment / GitHub Actions](docs/DEPLOYMENT.md)
- [Executed checks](docs/VERIFICATION.md)
- [Seven-minute interview guide](docs/INTERVIEW_GUIDE.md)
- [Roadmap](docs/ROADMAP.md)

## Remaining limits

This is a production-minded portfolio backend, **not a claim of production readiness**. Authentication throttling is per-process and must be supplemented by a shared gateway limiter. JWT refresh/password recovery, verified email, MFA, distributed quotas, durable jobs, and hosted deployment are future work. Regex time-budget failures can depend on machine load; their status and reason are explicit. Model advice can be wrong or manipulated despite safeguards. Protect data, bound concurrency/cost at your gateway, scan dependencies, rehearse restore procedures, and obtain an independent security review before exposing valuable data publicly.
