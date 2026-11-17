# Seven-minute technical interview walkthrough

Preparation: install the dev lock, migrate/bootstrap a local database, open Swagger, and keep a terminal ready. Alternatively run `python -m examples.demo --in-process` for the entire isolated, synthetic workflow with mock AI. No paid key is required and no passwords/tokens are printed.

| Minute | Demonstration | Engineering point |
|---|---|---|
| 0–1 | State the problem; show route → service → evaluator → DB diagram | Preserve assessment evidence and access boundaries; inert rubric matching is not program correctness |
| 1–2 | Register a viewer, log in, authorize Swagger, show denied task creation; use admin to promote an evaluator and re-login | Argon2id, JWT expiration, DB-backed roles, token-version revocation, no public privilege selection |
| 2–3 | Create the weighted rubric from API.md; submit the full and partial sorting explanations | Category normalization yields 100 vs 75; inspect each criterion contribution and reason |
| 3–4 | Read history, update with expected_revision=1, repeat the stale update | Atomic compare-and-swap, 409 conflict, immutable earlier task snapshot |
| 4–5 | Compare the two evaluations; grant viewer access; archive using current If-Match | Both records authorized, reader/editor separation, history preserved after archival |
| 5–6 | Use the isolated mock-AI demo or configured dev mock; inspect pending advice, then review as another evaluator | Provider abstraction, no paid-call claim, structured output, explicit external consent for real models, human review |
| 6–7 | Show executed verification and a CI run for the actual commit; discuss remaining limits | SQLite/PostgreSQL migrations and concurrency, mocked network failures, dependency scan, operational honesty |

Suggested answers:

- **Why a deterministic baseline?** Cheap, explainable, reproducible ordinary matches, plus a reference for model-assisted deltas. Regex timeouts are explicitly flagged and may depend on load.
- **How do you stop cross-user reads?** Parent-task visibility is enforced in shared service methods for tasks, history, comparisons and AI; list filters apply before count/pagination. Grants intentionally share all task history.
- **How do you avoid lost updates?** One SQL UPDATE includes the expected revision and active state; rowcount zero means conflict. The tests run competing writers, not just repeated sequential calls.
- **What changes when AI fails?** A safe failed advice record is retained; baseline history remains unchanged. Output is validated, retries/time/output are bounded, and no tools execute.
- **Why no executable tests?** Hostile code requires a separate isolation architecture. This project makes no code-correctness guarantee.
- **Is it production-ready?** No claim of that. Discuss shared rate limiting, email verification/MFA, quotas/spend controls, queue/idempotency, least-privilege DB roles, monitoring, and rehearsed backups.

The isolated demo's local mock mirrors the baseline score and is clearly labeled. Do not describe that output as semantic AI judgment or benchmarked accuracy. Real provider integration is transport-tested with mocks; obtain authorized data and explicit consent for any live demonstration.
