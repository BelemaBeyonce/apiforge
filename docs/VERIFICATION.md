# Executed verification — APIForge 0.2

Verified on 17 November 2026 with Python 3.12.14. Counts below are actual local executions, not assumptions carried over from the original project or claims of hosted CI success.

| Check | Actual result |
|---|---|
| Unmodified baseline | 34 passed, 98.94% application coverage |
| Auth/history checkpoint | 61 passed, including preserved legacy rows |
| Regex/categories/comparison checkpoint | 74 passed |
| Final SQLite suite | **97 passed; 98.51% application line coverage** |
| Final PostgreSQL suite | **98 passed; 98.51% application line coverage** |
| Ruff lint / formatting | Passed |
| Legacy migrations | Seeded 0001 tasks/results upgraded to head on SQLite and PostgreSQL; scores/snapshots/IDs/engine versions preserved; schema drift check passed |
| Competing updates | Two independent sessions raced; one revision update won, one returned conflict, on each database backend |
| AI adapter | HTTPX mocked-transport checks passed for request contract, structured output, consent, retries/recovery, timeout/network failure, output limit and sanitized persistence |
| Human review | Different authorized actor required; conflicting/repeated review rejected |
| Dependency audit | pip-audit of final requirements-dev.lock: **no known vulnerabilities found** at execution time |
| Docker | Image built with optional trusted CA build secret; UID 999; pip check passed; isolated demo passed |
| Live container HTTP | Readiness/liveness and full authenticated mock-AI demo passed on port 8012 |
| GitHub Actions | See the exact commit's Actions page; workflow file alone is not a successful hosted run |
| Paid/live model | **Not executed**; real adapter transport integration tested with mocks |
| Hosted deployment | **Not performed**; Render template and instructions supplied |

Final suite commands:

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=90
APIFORGE_TEST_DATABASE_URL=postgresql+psycopg://postgres@localhost:55432/apiforge_phase2_test pytest --cov=app --cov-report=term-missing --cov-fail-under=90
ruff check .
ruff format --check .
pip-audit --disable-pip --no-deps -r requirements-dev.lock
python -m examples.demo --in-process
```

The PostgreSQL suite uses unique per-test schemas in a disposable PostgreSQL 16 container. Its extra test is the PostgreSQL seeded-legacy migration case. This is a complete API/unit test run using PostgreSQL-backed fixtures, not only a SELECT 1 smoke test. The SQLite migration case also runs during that invocation. The body-timeout branch and a few operator/transport cleanup branches are not covered; coverage is a useful signal, not proof of security.

## Resolved findings and changes

- Independently reproduced the old 34-test baseline before modifications.
- Updated old regression contracts only where documented API changes require authentication, revision fields, and archive preservation. The original normal/invalid/edge scenarios remain tested.
- Found original Starlette advisories during the dependency audit; upgraded FastAPI/Starlette and reran the complete suite. Also upgraded pip, a dependency of the audit tool. No advisories were suppressed.
- Fixed PostgreSQL FK-name discovery and portable typed JSON backfill while preserving the original migration file. SQLite FK checks protect batch recreation from the old cascade behavior.
- Docker dependency installation uses this environment's enterprise-proxy CA through a build-only secret; certificate verification remains enabled. The default Dockerfile also works without that optional secret on ordinary trusted networks.
- The final suite emits one upstream Starlette deprecation warning about HTTPX-based TestClient compatibility. Both final database runs still pass. Plan the next HTTP client compatibility upgrade under tests.

## Interpretation

These results do not establish production readiness, live-provider semantic accuracy, or a successfully deployed website. Regex timeout outcomes can vary with system load; they are explicitly flagged. Model feedback is advisory, has independent review, and never executes code or replaces stored deterministic scores. New vulnerabilities may be published after this audit. Re-run checks and inspect the specific GitHub Actions result before merging or deploying.
