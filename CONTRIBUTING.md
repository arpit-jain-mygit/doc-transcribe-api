# Contributing (API)

## Architecture rule
Follow `/ARCHITECTURE.md` boundaries before adding or moving code.

## Mandatory checklist for every backlog item fix
- Mention backlog ID (`PRS-xxx`).
- Add/adjust logs (request start, success, failure).
- Add explicit exception mapping for new failure types.
- Keep response contract stable (document if changed).
- Add test notes (manual + automated if available).

## Logging minimum
- Include: `request_id`, `job_id` (if available), `route`, `latency_ms`, `error_code`.
- Avoid logging tokens, credentials, or private payload data.

## Review checklist
- No direct infra calls from routes when service/repository exists.
- Keep heavy endpoint orchestration in `services/` (routes remain request/response adapters).
- No generic uncaught exceptions in new code paths.
- No contract drift without schema/doc update.
