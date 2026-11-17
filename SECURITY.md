# Security boundaries

APIForge is a local portfolio MVP, not a hardened public multi-tenant service.

- Submitted responses remain inert strings. No `exec`, `eval`, subprocess execution, dynamic imports, or test runner is applied to submitted content.
- Exact/contains criteria are deterministic and intentionally limited. Keyword stuffing and nonfunctional code can score highly. Scores must not be presented as reliable hiring decisions or functional correctness results.
- Authentication, authorization, tenant isolation, quotas, and rate limiting are not implemented. Any caller can read the reference rubric and manipulate tasks. Keep the service on loopback or behind an authenticated private gateway.
- Field limits bound accepted content, but parsing happens before validation. Configure a reverse proxy with body size limits, timeouts, TLS, and rate limits before accepting untrusted network traffic.
- Environment variables supply database credentials. `.env` is ignored, `.env.example` contains no usable password, containers run unprivileged, and request logs omit payloads and query strings. Use a secret manager in production. Do not put secrets into task text or submissions; these are stored in plaintext.
- Database errors and unexpected failures return sanitized messages. Protected operational monitoring should capture diagnostic categories without logging credentials or sensitive payloads.
- Deletion cascades to evaluation history. Define retention, backup, restore, and audit policies before storing valuable data.
- Dependency versions are captured in lock files. Scan and update dependencies and base images before deployment. The CI PostgreSQL service uses passwordless trust only on its disposable runner; this must never be copied into a production database configuration.

## Future executable evaluation

Executing untrusted code requires an isolated worker service, not an endpoint calling Python locally. Use disposable sandboxes with strong isolation (such as microVMs), no application/database secrets, denied network egress, read-only images, unprivileged users, seccomp/capability restrictions, CPU/memory/process/file/time/output limits, and bounded queues. Handle malicious infinite loops and fork bombs; kill the entire sandbox on timeout. Separate test artifacts and scoring from the public API. Containers alone are not a sufficient security claim for hostile code.

Future LLM judges need explicit consent for external processing, prompt-injection defenses, output-schema validation, provider timeout/retry budgets, data minimization, model/prompt versioning, human review, and calibration against a curated benchmark. Never interpolate task content into privileged instructions or give a judge execution tools by default.
