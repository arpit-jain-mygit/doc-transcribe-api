# API Architecture (`doc-transcribe-api`)

## Purpose
Define strict boundaries between HTTP layer, business logic, and infrastructure access.

## Layers and dependency direction
Allowed direction:
- `routes/` -> `services/` -> `repositories/` (or existing data access module)
- `services/` -> `schemas/` and `config.py`
- `repositories/` -> external systems (Redis/storage)

Disallowed direction:
- `routes/` directly performing low-level Redis/storage operations
- `schemas/` importing from routes/services

## Canonical contract
- Job status contract source: `JOB_STATUS_CONTRACT.md`

## Current modules (as-is)
- `routes/`: upload/status/jobs/health/auth endpoints
- `services/`: queue/auth/redis helpers + orchestration modules (e.g., `services/upload_orchestrator.py`)
- `schemas/`: request/response models
- `app.py`: app bootstrap and router registration

## Target boundary (incremental)
- Keep route handlers thin (request/response only)
- Move business decisions to services
- Centralize data access in repository-style modules

## Logging requirements for every backlog item fix
- Every request flow logs:
  - start (`route`, `request_id`)
  - result (`status_code`, `latency_ms`)
  - failure (`error_code`, exception class)
- Never log secrets/tokens.

## PR placement checklist
- Is route logic thin and delegated to service layer?
- Are external system calls centralized?
- Are errors mapped to stable API payloads?
- Are logs added for new paths and failure modes?
