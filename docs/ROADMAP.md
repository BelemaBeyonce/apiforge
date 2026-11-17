# Roadmap after Phase 2

- Verified-email onboarding, password recovery/change, MFA, refresh/revocation strategy and durable admin audit events.
- Shared rate limits and per-user/provider quotas; queue-based AI jobs with idempotency, cancellation and durable attempts.
- A labeled evaluation benchmark, human inter-rater agreement, judge calibration, prompt-injection cases, cost/latency budgets and model/prompt upgrade reports.
- Restricted linear-time regex engine to remove time-budget variability; stronger DB rubric constraints where portability allows.
- Data retention/erasure policy and protected administrative archival/restore tooling; rehearsed backups and restore drills.
- Authenticated UI with escaped model output and an explicit human-review inbox.
- Optional RAG retrieval grounded in authorized documents; evaluate retrieval quality separately from answer quality.
- Future executable evaluation only in a separately isolated worker with denied egress and resource limits, never in the API process.

Success means demonstrated correctness, safe boundaries and honest limits, not adding infrastructure for its own sake.
