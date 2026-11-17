# API 0.2 contract

Base: `http://127.0.0.1:8000/api/v1`. JSON bodies. Data endpoints require `Authorization: Bearer ACCESS_TOKEN`. Swagger's Authorize control supports this directly. Do not put tokens into URLs or logs.

| Method | Path | Authorization / behavior |
|---|---|---|
| POST | `/auth/register` | Public, rate limited; email/password only; always viewer |
| POST | `/auth/login` | Public, rate limited; JSON email/password; expiring JWT |
| GET | `/auth/me` | Active authenticated identity |
| GET | `/users?limit=20&offset=0` | Admin only |
| PUT | `/users/{id}` | Admin; role/is_active; revokes old tokens; no self-demotion/disable |
| GET | `/live` | Public process liveness |
| GET | `/health` | Public database connectivity (compatibility endpoint) |
| GET | `/ready` | Public DB connectivity plus migration-head check |
| POST | `/tasks` | Admin/evaluator; new task owned by caller |
| GET | `/tasks` | Authorized tasks only, filters/pagination, optional include_archived |
| GET | `/tasks/{id}` | Authorized task, optional include_archived |
| PUT | `/tasks/{id}` | Owner/editor with evaluator role, or admin; expected_revision required |
| DELETE | `/tasks/{id}` | Same write permission; integer If-Match revision; archives (204) |
| PUT | `/tasks/{id}/access/{user_id}` | Owner/admin only; permission reader/editor |
| DELETE | `/tasks/{id}/access/{user_id}` | Owner/admin only; revoke grant (204) |
| POST | `/tasks/{id}/evaluations` | Write permission; active task; inert response |
| GET | `/tasks/{id}/evaluations` | Authorized history, including after archive |
| GET | `/evaluations/{id}` | Parent-task authorization |
| GET | `/evaluations/{id}/compare/{other_id}` | Both parent tasks must be authorized |
| POST | `/evaluations/{id}/ai` | Write permission; optional feature flag and consent |
| GET | `/evaluations/{id}/ai` | Parent-task authorization; advice/baseline deltas |
| POST | `/ai-evaluations/{id}/review` | Different authorized admin/evaluator editor |

## Authentication

```json
{"email":"your-user@example.com","password":"your-own-private-password"}
```

Use that shape for registration and login. Login returns `access_token`, `token_type=bearer`, and `expires_in` seconds. Passwords are 12–128 characters and are not whitespace-normalized. Emails are validated and lowercased. Registration rejects privileged role fields. Bootstrap the first admin through `python -m app.bootstrap`, then an admin can promote a registered viewer:

```json
{"role":"evaluator","is_active":true}
```

Re-login after the change. Throttling defaults to 10 combined registration/login attempts per direct peer per minute per process. 429 includes Retry-After. See deployment limitations before using multiple workers or a proxy.

## Task creation and rubric

```json
{
  "title":"Explain stable sorting",
  "description":"Describe Python sorting and equal-item order.",
  "language":"python",
  "difficulty":"easy",
  "expected_outcome":"Mention sorted and stable ordering.",
  "categories":[{"name":"correctness","weight":3},{"name":"explanation","weight":1}],
  "criteria":[
    {"name":"builtin","kind":"contains","reference":"sorted","category":"correctness","weight":1},
    {"name":"stability","kind":"contains","reference":"stable","category":"explanation","weight":1}
  ]
}
```

Returns 201 with ID, owner ID, revision, archive state and timestamps. Defaults remain backward-compatible for single-category rubrics: omit categories and each criterion's category to use `general`. Criteria kinds are exact, contains or regex. Leading/trailing whitespace is stripped; internal whitespace is significant. Case sensitivity defaults true. Regex uses search semantics; anchors can require whole-response matches.

Task title <=200 characters; description/expected outcome <=20,000 each; lowercase language <=40; difficulty easy/medium/hard. Rubrics have 1–50 uniquely named criteria and 1–10 uniquely named, used categories. Criterion/category weights are integers 1–100. Reference <=10,000 characters (regex <=512). Unknown body fields are rejected. Pydantic's normal numeric coercion applies. Full HTTP body cap defaults to 256 KiB before JSON parsing.

PUT uses the complete creation shape **plus `expected_revision`**. Use the latest returned revision; stale values produce 409, never overwrite silently. DELETE uses `If-Match: 2` for revision 2; missing/invalid headers produce 422. The header is a positive integer revision, not an HTTP ETag string.

List filters: `language`, `difficulty`, `include_archived`. `limit` defaults 20, range 1–100; `offset` defaults 0, minimum 0. Task/history pages return items, total, limit, offset in stable ID order. Totals count only authorized matching rows. Out-of-range offsets return empty items. Unauthorized IDs deliberately appear missing.

## Evaluation and comparison

```json
{"response":"Use sorted for stable ordering."}
```

`POST /tasks/{id}/evaluations` returns 201 with score, feedback, task snapshot/revision, author, status, engine version and timestamp. The example above scores 100. `Use sorted.` scores 75 because correctness has 3/4 of the category weight. Feedback includes passed, earned/possible criterion weight, category, contribution, reason and message. Responses are limited to 50,000 trimmed characters. Scores are inert rubric matches, not code execution or correctness guarantees.

Comparison returns both scores, delta (`right-left`), feedback, and flags for same task/rubric/engine. Cross-rubric deltas require interpretation. Comparisons never change stored results. Historical v1 snapshots remain unchanged even if newer schemas add fields.

## AI advice and human review

```json
{"consent_to_external":true}
```

Use this for a configured external provider; local mock requests can use `{}`. A created record returns 201 even when its **status is failed**: inspect status/error_code. Model feedback never replaces the baseline. GET returns advisory deltas and bounded pagination. Review body:

```json
{"decision":"accepted","note":"Compared the advice with the reference manually."}
```

The requester cannot review their own advice. Only a pending record can transition, and accepted/rejected review cannot be overwritten. See AI documentation for provider errors and data transmission.

## Errors and headers

```json
{"error":{"code":"http_error","message":"Task revision conflict; reload before updating","details":[],"request_id":"server-generated-uuid"}}
```

401 authentication, 403 forbidden, 404 missing or unauthorized resource, 409 revision/uniqueness/state conflict, 413 body/AI budget, 422 validation, 429 throttling, 503 database/disabled feature, 500 sanitized unexpected failure. Request limits may also return 400 malformed Content-Length or 408 body timeout. Every application response has X-Request-ID. Error details expose location, message and type, never raw input. CORS is opt-in to exact configured origins. Infrastructure errors outside the app may use the gateway's contract.
