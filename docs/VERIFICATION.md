# Executed verification

Verified on 17 November 2026 using Python 3.12.14 in the development environment. These are executed results, not predictions of future CI runs.

| Stage | Actual result |
|---|---|
| Pure evaluation module | 8 tests passed |
| API, validation and persistence | 33 tests passed after fixes |
| Final suite including migrations | **34 tests passed**, **98.94% application line coverage** |
| Ruff lint and formatting | Passed |
| SQLite migrations | Upgrade, schema drift check, downgrade, re-upgrade passed |
| Sample data | Seed run twice without duplicates |
| Local Uvicorn HTTP demo | Passed against SQLite on port 8010 |
| Docker image | Build passed with BuildKit CA secret for this environment's HTTPS proxy |
| SQLite Compose service | Healthy; HTTP demo passed on port 8000; non-root UID 999; `pip check` passed |
| PostgreSQL 16 Compose service | Healthy; HTTP demo passed on port 8011; seed, schema drift check, downgrade and re-upgrade passed |
| GitHub Actions | Workflow supplied; not run on GitHub during this delivery |

Final test command:

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=90
```

One third-party deprecation warning remains: Starlette's TestClient refers to an AnyIO alias slated for removal. It does not affect these successful test runs. Keep dependency upgrades under regression testing.

## Failures encountered and resolved

- Initial evaluator tests could not import the project before installation. Installed the package with `pip install -e '.[dev]'`; all eight tests then passed.
- An API test searched error messages for the substring `input`, incorrectly rejecting the valid message `Extra inputs are not permitted`. Corrected the assertion to check that raw `input` keys are absent from error details; the suite passed.
- Initial Ruff checks flagged import order, dictionary style and the deliberate broad HTTP-boundary exception handler. Applied formatting/import fixes and documented the boundary exception suppression. Final lint checks pass.
- Docker's first build could not validate this managed environment's proxy certificate. Added an optional BuildKit `pip_ca` secret and rebuilt with the environment's trusted CA bundle, retaining TLS verification. The secret is not copied into image layers.
- The default PostgreSQL API port 8001 was already occupied. Made the port configurable through `POSTGRES_API_PORT` and completed verification on 8011.

## Reproduce the container checks

Ordinary environments need no custom certificate:

```bash
docker compose up --build -d api
python -m examples.demo --url http://127.0.0.1:8000
```

If an enterprise proxy requires a trusted CA bundle:

```bash
docker build --secret id=pip_ca,src=/path/to/trusted-ca-bundle.pem -t apiforge-api .
docker compose up --no-build -d api
```

For PostgreSQL, use the password setup in the README, set `POSTGRES_API_PORT=8011` if needed, and run the same demo with that port. The checks exercised the real API over HTTP and a real PostgreSQL database. The complete 34-test suite uses isolated SQLite databases; this delivery does not claim the entire suite was executed against PostgreSQL.
