# Canonical Job/Status Contract (Source of Truth)

Contract version:
- `2026-02-16-prs-002`

Machine-readable endpoint:
- `GET /contract/job-status`

## Canonical enums

### Job type
- `OCR`
- `TRANSCRIPTION`

### Job status
- `QUEUED`
- `PROCESSING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

### Terminal status
- `COMPLETED`
- `FAILED`
- `CANCELLED`

## Canonical job fields

Required lifecycle fields:
- `contract_version` (string)
- `job_id` (string)
- `job_type` (enum)
- `status` (enum)
- `stage` (string)
- `progress` (0-100 integer)
- `source` (`ocr` or `file`)
- `input_filename` (string)
- `input_size_bytes` (integer)
- `output_filename` (string)
- `created_at` (ISO-8601)
- `updated_at` (ISO-8601)

Optional outcome/metadata fields:
- `output_path` (`gs://...` internally)
- `download_url` (signed URL returned by API)
- `duration_sec` (number)
- `total_pages` (integer for OCR)
- `error` (string)
- `cancel_requested` (`0|1` style string flag)

## Ownership rules
- API owns:
  - contract definition
  - upload-time initialization of canonical fields
  - read-time generation of `download_url`
- Worker owns:
  - stage/progress/status transitions during execution
  - writing `duration_sec`, `total_pages`, `output_path`, `error`
- UI owns:
  - display formatting only
  - must consume canonical fields first (fallback aliases only in one compatibility layer)

## Compatibility policy
- New fields can be added only as optional.
- Renaming/removing canonical fields requires:
  - new `contract_version`
  - UI and worker compatibility update in same backlog item
  - regression pass (local + cloud) before marking tested.
