# Deployment preparation and CI

These instructions prepare a private or controlled public demonstration. No hosted application is deployed by this repository and local checks alone do not establish production readiness.

## Configuration

Use the fields in `.env.example`. Production requires `ENVIRONMENT=production`, a stable random JWT_SECRET of at least 32 characters, and `DATABASE_URL=postgresql+psycopg://...`. Use provider-recommended TLS options and URL-encode credentials. Store secrets in the platform secret manager. Production CORS origins, if set, must be explicit HTTPS URLs; the default empty list permits no cross-origin browser clients. Production rejects mock AI. External AI additionally requires explicit opt-in and an API key. Disabled AI needs no key.

The application limits bodies to 256 KiB by default before parsing, with a 10-second receive budget. Configure gateway header/body limits, connection/request timeouts, concurrency limits, and shared login/registration rate limiting. Add per-user AI quotas and spending alerts before enabling a paid provider. Current auth throttling is per-process; default server commands disable proxy-header trust. Add trusted proxy handling only after reviewing gateway behavior.

## Render example

`render.yaml` is a preparation template, not a deployment claim. Create a managed PostgreSQL instance separately; provision backup/retention and restore procedures. Create a Docker web service connected to this repository, set its DATABASE_URL using SQLAlchemy's `postgresql+psycopg` scheme, and set the production variables above. The template generates a JWT secret and disables AI. The selected paid service plan supports a pre-deploy migration command; verify current platform capabilities/pricing before provisioning anything.

- Build: supplied Dockerfile.
- Pre-deploy: `alembic upgrade head`, once per release, with controlled migration credentials.
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log --no-proxy-headers`.
- Health check: `/api/v1/ready`.
- First admin: run `python -m app.bootstrap` through a protected operator shell after migration; enter the password interactively.
- Verify `/live`, `/ready`, login, an unauthorized read, and a revision conflict. Use synthetic data only.

For a private demonstration, place the service behind an authenticated gateway and do not make admin credentials public. There is no public bootstrap endpoint. Re-login after role changes. Swagger is available at /docs and should also be protected by the gateway if the schema should be private.

## Migrations and rollback

Back up the database, verify backup restoration, stop writers, run `alembic upgrade head`, then `alembic check`. Readiness checks the database's recorded revision against the code's head; it does not replace schema-drift checks. Bring up the service and run smoke tests before restoring traffic. Do not let all replicas race migrations at startup. Compose's startup migration is for a local single-container demo only.

Migration 0002 is intentionally forward-only because undoing access control can expose data. Roll back by restoring a reviewed backup with compatible code, not by blindly downgrading. Keep the previous release and its database backup until acceptance. See DATABASE.md for SQLite batch/FK precautions and legacy ownership behavior.

## Containers and reproducibility

The image installs the resolved runtime dependency versions, then the project without re-resolving dependencies. It runs as UID 999 and has a readiness health check. The Python and PostgreSQL base image tags still move; production releases should additionally pin reviewed image digests, generate SBOMs, scan images, and schedule rebuilds. Lock files are Python-3.12 resolutions with version pins, not a hash-verified supply-chain guarantee. Build tools are resolved separately by the build backend.

Enterprise proxy CA support:

```bash
docker build --secret id=pip_ca,src=/path/to/trusted-ca-bundle.pem -t apiforge-api .
```

The optional CA file is mounted only during dependency installation; TLS verification is preserved. Do not bake proxy credentials into images. Local Compose binds API ports to loopback and uses named database volumes. PostgreSQL password must be supplied privately. Do not run `docker compose down -v` on valuable data.

## GitHub verification

Push a feature branch and open a PR. In GitHub Actions, inspect the **Backend checks** workflow for the exact commit. It runs:

1. Locked dependency installation and Ruff lint/format checks.
2. SQLite suite with >=90% application coverage and XML artifact.
3. The complete suite against isolated PostgreSQL schemas, including seeded legacy upgrades and competing revision writes.
4. The isolated mock-AI interview demo.
5. pip-audit against the development dependency lock, without suppressing advisories.
6. A Docker image build.

The PostgreSQL service uses trust authentication only on the disposable GitHub-hosted runner; never use that setting for production. CI permissions are contents:read. No provider API key is required. A green workflow must be observed for the specific commit before claiming hosted CI success. The Render configuration is not automatically deployed by CI.
