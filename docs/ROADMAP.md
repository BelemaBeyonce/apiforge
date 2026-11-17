# Evaluation roadmap

1. **Operational foundation:** authentication and role-based task ownership; PostgreSQL concurrency tests; optimistic update conflicts; rate limits; body limits; audit events; backups and restore drills; pagination cursors for large datasets.
2. **Evaluation abstraction:** versioned evaluator interface, explicit modes, normalized rubric/result contracts, idempotency keys, asynchronous queue workers, retry policy and cancellation. Retain the deterministic baseline for regression comparisons.
3. **Safe test cases:** separate sandbox service with signed test bundles, hidden cases, explicit input/output contracts, resource budgets, network isolation, and adversarial sandbox verification. Never execute submitted code in the API process.
4. **LLM-assisted feedback:** opt-in provider adapter with environment credentials, strict structured outputs, rubric-grounded feedback, model/prompt/version metadata, latency/token budgets, and a clear distinction between deterministic score and model judgment.
5. **Judge quality lab:** curated human-labeled cases, train/evaluation splits, inter-rater agreement, false-positive/negative analysis, prompt-injection fixtures, reproducibility reports, uncertainty thresholds, and human escalation. Compare judge upgrades against the baseline before rollout.
6. **Recruiter-facing extensions:** authenticated dashboard, evaluation comparison reports, observability metrics, deployment guide, dependency scanning, and repeatable load testing with documented concurrency limits.

Success is measured by quality and reproducibility on held-out cases, cost/latency budgets, sandbox containment, and clear human override paths. An LLM score alone is not an objective correctness oracle.
