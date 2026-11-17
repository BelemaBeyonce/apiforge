# Optional AI evaluation

The optional AI service is separate from baseline scoring. The default app works without an API key and never sends data to a model. The implementation includes a real OpenAI-compatible HTTP adapter plus a synthetic local mock. Tests exercise the adapter through HTTPX MockTransport; no live-model quality or paid call is claimed.

## Enable deliberately

Development contract demo:

```dotenv
AI_ENABLED=true
AI_PROVIDER=mock
```

The mock reports the baseline score, labels itself synthetic, and performs no semantic assessment. Production settings reject it.

Real provider:

```dotenv
AI_ENABLED=true
AI_PROVIDER=openai
AI_ALLOW_EXTERNAL=true
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
# Set AI_API_KEY privately; do not copy keys into source or logs.
AI_TIMEOUT_SECONDS=15
AI_RETRIES=1
```

Replace the URL/model with a provider that supports Chat Completions plus JSON-schema structured output. HTTPS is required. The configured URL is an operator trust boundary, not caller-supplied. Provider proxies/redirects/ambient credentials are disabled in the adapter. Private gateways needing enterprise CA trust must be configured with an explicit trusted certificate bundle at deployment; never disable TLS verification.

`POST /evaluations/{id}/ai` additionally requires `consent_to_external=true`. Consent permits transmitting the stored task/rubric/revision, response, baseline score and criterion feedback to that configured provider. Do not submit real candidate, proprietary, or personal data unless its transmission is authorized. The record stores no API key or raw provider envelope. Authorization is rechecked against the parent task before requesting advice.

## Provider contract and bounds

A provider implements `evaluate(payload) -> (AIFeedback, safe_metadata)`. Feedback has score 0–100, bounded summary, bounded strengths/weaknesses, and uncertainty text; unknown fields and non-finite scores are rejected. The real adapter:

- Calls `POST {AI_BASE_URL}/chat/completions` with fixed system instructions and untrusted JSON user data; no tools or execution capability.
- Requests JSON-schema output, temperature 0, and at most 1,500 output tokens. Temperature 0 does not guarantee reproducibility.
- Caps serialized input at 80,000 characters and output at 64 KiB.
- Uses configured HTTP timeouts (default 15 s), at most two configured retries (default one), and short bounded backoff. Only network/timeouts, 429 and server failures retry; invalid output/other HTTP errors do not.
- Stores only numeric token usage, attempt count and latency from known metadata fields.

Provider errors become persisted `failed` records with sanitized codes: provider_timeout, provider_unavailable, provider_rejected_request, provider_output_limit, invalid_provider_output. HTTP 201 means the advice record was created; inspect status before treating it as generated feedback. The baseline remains unchanged and usable after failures.

## Human review and comparison

Successful advice starts `pending_review`. A **different** authorized admin/evaluator with write permission on the task must accept or reject it with a note. The transition is conditional, so competing decisions cannot overwrite a completed review. Viewers and requesters cannot approve it. Acceptance records human judgment, not proof of correctness. Advice remains separate from the deterministic score forever.

`GET /evaluations/{id}/ai` returns advice, review metadata, the baseline score and advisory score deltas. `GET /evaluations/{id}/compare/{other}` compares two baseline evaluations. Different rubrics/models/engines can produce incomparable scores. Use a human-labeled benchmark before making quality claims.

## Threats and limits

Fixed instructions, typed output, bounded budgets, no tools, explicit consent and independent review reduce risk; they do not defeat all prompt injection, hallucination or bias. Rubric/task/response text is untrusted. No secrets appear in prompts. Model/provider/version changes can change results. The recorded model is the configured requested name, not a cryptographic guarantee of provider internals. Prompt version is `rubric-judge-v1`.

This synchronous MVP does not provide durable jobs, idempotency, a global spend ledger, calibrated confidence, a benchmarked judge, or model fine-tuning. Add gateway concurrency/cost quotas before exposing paid endpoints. Provider output is untrusted text and must be escaped by any future UI. Never turn model recommendations into automatic code execution or hiring decisions.
