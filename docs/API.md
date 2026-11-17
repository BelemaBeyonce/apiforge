# API contract and examples

Base URL: `http://127.0.0.1:8000/api/v1`. JSON request/response bodies, except 204 deletion responses. No authentication in this local MVP.

## Create a task

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Predict sum","description":"Predict sum([1,2,3]) without running code.","language":"python","difficulty":"easy","expected_outcome":"6","criteria":[{"name":"output","kind":"exact","reference":"6","weight":1,"case_sensitive":true}]}'
```

Returns 201 with all supplied fields plus `id`, `revision=1`, `created_at`, and `updated_at`. Use the returned ID below.

```bash
curl -sS 'http://127.0.0.1:8000/api/v1/tasks?language=python&difficulty=easy&limit=20&offset=0'
curl -sS http://127.0.0.1:8000/api/v1/tasks/1
curl -sS -X POST http://127.0.0.1:8000/api/v1/tasks/1/evaluations \
  -H 'Content-Type: application/json' -d '{"response":"6"}'
curl -sS 'http://127.0.0.1:8000/api/v1/tasks/1/evaluations?limit=10&offset=0'
curl -sS http://127.0.0.1:8000/api/v1/evaluations/1
```

An evaluation contains `id`, `task_id`, `response`, `score`, `feedback`, `task_snapshot`, `engine_version`, and `created_at`. Example feedback:

```json
{"criterion":"output","passed":true,"earned_weight":1,"possible_weight":1,"message":"Reference matched"}
```

To replace a task, `PUT /tasks/{id}` with the same complete input shape as creation. Omitted required fields produce 422. Each successful replacement increments the revision. `DELETE /tasks/{id}` returns 204 with no body and removes its evaluations. Missing resources return 404. Malformed/invalid IDs return 422. There is no partial PATCH endpoint.

## Criteria semantics

`kind` is `exact` or `contains`. Both the response and reference are stripped of leading/trailing whitespace. `contains` uses literal substring matching, never regex. If `case_sensitive=false`, both values use Unicode case folding. Internal whitespace and punctuation are significant. Criteria have unique names, integer weights from 1 to 100, and nonempty references. Each passes or fails independently.

`score = round(100 × passed_weight / total_weight, 2)`. All rules carry positive weights. `expected_outcome` documents the task; only the explicit criteria influence scoring. A score is not proof of functional correctness.

## Validation and pagination

- Title: 1–200 characters; description and expected outcome: 1–20,000.
- Language: 1–40 lowercase characters matching `[a-z0-9+#.-]+`; difficulty: easy/medium/hard.
- Criteria: 1–50; names: 1–120; references: 1–10,000.
- Response: 1–50,000 characters after trimming. Whitespace-only fields are invalid. Unknown body fields are rejected.
- `limit`: default 20, range 1–100. `offset`: default 0, minimum 0.
- List response: `{"items":[],"total":0,"limit":20,"offset":0}`. `total` counts all matching rows before pagination. Filters are exact and case sensitive. An offset beyond the result set returns an empty list.
- JSON integer coercion follows Pydantic defaults; this is not a strict JSON-type API.

## Errors and observability

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [{"location":["body","response"],"message":"Field required","type":"missing"}],
    "request_id": "server-generated-uuid"
  }
}
```

All application errors follow this envelope. Statuses: 404 missing resource/route, 405 unsupported method, 422 invalid request, 503 database failure, 500 unexpected failure. `http_error`, `validation_error`, `database_unavailable`, and `internal_error` are stable code categories. Raw SQL, credentials, submitted inputs, and stack traces are not returned. Every response carries `X-Request-ID`; completion logs use the same value. Reverse proxy rejection responses are outside this application contract.

`GET /health` executes `SELECT 1`, so it checks connectivity rather than migration currency. Deployments must run migrations independently. Swagger UI and ReDoc expose the generated schema interactively.
