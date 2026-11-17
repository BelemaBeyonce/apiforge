# Security boundaries and limitations

APIForge is a portfolio backend with concrete controls, not a certification of public-production safety.

## Implemented controls

- Argon2id password hashes through argon2-cffi; plaintext passwords are never stored or returned. Registration validates email and password length, rejects role fields, and always creates viewers.
- Explicit operator-only first-admin CLI. Existing registered emails cannot be promoted by bootstrap. A singleton database guard prevents simultaneous first-admin creation. Additional role changes require an authenticated admin; admins cannot disable/demote themselves through the API.
- PyJWT HS256 with a fixed algorithm allowlist, issuer/audience/expiration/issued-at/subject/JTI/token-version requirements. Every request checks active user/role state in the DB. Role/activation changes revoke existing tokens by advancing token version.
- Task ownership and reader/editor grants checked by reusable service logic. Hidden resources return 404. Evaluations, comparisons, AI advice and reviews inherit task visibility; viewer role never grants write permissions. Bearer tokens are never accepted in query strings.
- Conditional revision updates and archive operations, immutable baseline snapshots, preserved history, and restricted parent deletion.
- Bounded pattern/text/rubric limits and regex timeouts. No eval, exec, compile, subprocess, dynamic import, or execution is applied to submitted content.
- Optional external AI disabled by default, explicit deployment/request consent, no execution tools, structured output validation, bounded transport/output/retries, and different-person human review. Provider errors are sanitized.
- Request-body cap before parsing, body receive timeout, explicit CORS origins, application JSON logs that omit payloads/query strings/authorization headers, request IDs, non-root container runtime, and dependency audit in CI.

## Deployment obligations

Authentication rate limiting uses the established limits library with in-memory per-process storage. It caps combined login/registration attempts per direct peer per minute and bounds peer tracking. It is **not shared across replicas**, and NAT/proxy peers may share a limit. Use one worker for a private demo and an upstream shared limiter, concurrency cap, TLS and bot controls before public exposure. Default commands disable proxy headers; only enable forwarded-IP handling when a correctly configured trusted gateway sanitizes them. Never trust arbitrary X-Forwarded-For.

JWT_SECRET must be random, private and stable across workers; production requires an explicit >=32-character secret and PostgreSQL. Development without a configured secret generates an ephemeral one, so tokens stop working after restart. Production CORS allows only explicit HTTPS origins. CORS is a browser policy, not authorization. Configure allowed origins deliberately; use a secret manager, rotate keys, and establish incident procedures. Use encrypted PostgreSQL connections and least-privilege runtime DB credentials; migration operators need additional DDL privileges.

Reader access exposes all authorized task history, including responses and AI advice. Stored content is plaintext in the database. Protect backups, define retention and user-erasure policy, and do not use real candidate data in public demos. Archive retention is intentional; there is no public hard-delete endpoint. API permissions cannot prevent an administrator with direct database access from changing records.

There is no verified-email flow, password reset/change endpoint, refresh token, MFA, per-token logout, durable audit ledger, global quota or spend manager. Disabling users/reissuing role state revokes their tokens. Model advice can be gamed; exact/contains matching can reward nonfunctional code, regex timeouts depend on load, and AI can hallucinate. Never present these scores as automatic hiring decisions or correctness guarantees.

## Future execution infrastructure

If executable tests are added, use a separate isolated worker with disposable microVM/sandbox boundaries, denied egress, no app/database secrets, CPU/memory/process/time/output limits, read-only base images, and adversarial containment tests. Containers alone are not a sufficient claim of safety for hostile code. Do not add local execution to the API process.

## Vulnerability handling

Run the supplied dependency audit and regression suite before release; pins age and new advisories appear. Secrets, .env, virtual environments, generated SQLite files, credential files and private key files are ignored. Report suspected vulnerabilities privately to the repository owner; do not post secrets in public issues. Follow the documented backup/restore procedure before migrations.
