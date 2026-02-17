# doc-transcribe-api
[![API CI](https://github.com/arpit-jain-mygit/doc-transcribe-api/actions/workflows/ci.yml/badge.svg)](https://github.com/arpit-jain-mygit/doc-transcribe-api/actions/workflows/ci.yml)

## Production env vars (Render)

Required:
- `GOOGLE_CLIENT_ID`
- `REDIS_URL`
- `QUEUE_NAME`
- `GCS_BUCKET_NAME`
- `CORS_ALLOW_ORIGINS`

Feature flags:
- `FEATURE_QUEUE_PARTITIONING=0|1`
- `FEATURE_UPLOAD_QUOTAS=0|1`
- `FEATURE_DURATION_PAGE_LIMITS=0|1`

Queue partition vars (when `FEATURE_QUEUE_PARTITIONING=1`):
- `QUEUE_NAME_OCR` (default `doc_jobs_ocr`)
- `QUEUE_NAME_TRANSCRIPTION` (default `doc_jobs_transcription`)

Quota/limit vars:
- `DAILY_JOB_LIMIT_PER_USER` (`0` disables)
- `ACTIVE_JOB_LIMIT_PER_USER` (`0` disables)
- `MAX_OCR_PAGES` (`0` disables)
- `MAX_TRANSCRIPTION_DURATION_SEC` (`0` disables)

Operational:
- `MAX_OCR_FILE_SIZE_MB`
- `MAX_TRANSCRIPTION_FILE_SIZE_MB`
