# API Guide (End-to-End)

This guide explains how to run and verify `doc-transcribe-api` locally and how it interacts with UI/Worker.

## 1. Repo Path

`/Users/arpitjain/PycharmProjects/doc-transcribe-api`

## 2. What This API Does

- Validates Google user token
- Accepts file upload requests
- Pushes jobs to Redis queue
- Exposes job status and job history
- Canonical contract source: `JOB_STATUS_CONTRACT.md`
- Supports job cancellation
- Returns signed download URLs for GCS outputs

## 3. Key Endpoints

- `POST /upload`
- `GET /status/{job_id}`
- `GET /jobs`
- `POST /jobs/{job_id}/cancel`
- `GET /health` (from health router)

## 4. Required Environment Variables

Core:
- `GOOGLE_CLIENT_ID`
- `REDIS_URL` (default fallback: `redis://localhost:6379/0`)
- `QUEUE_NAME` (default: `doc_jobs`)
- `DLQ_NAME` (default: `doc_jobs_dead`)
- `GCS_BUCKET_NAME`
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` (base64 json credentials, if used by your GCS helper)

Notes:
- `.env` is loaded by `app.py` before route imports.
- Keep `.env` out of git.

## 5. Install Dependencies

```bash
cd /Users/arpitjain/PycharmProjects/doc-transcribe-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 6. Run API Locally

```bash
cd /Users/arpitjain/PycharmProjects/doc-transcribe-api
source .venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8080 --reload
```

If port `8080` is busy, use another port and update UI proxy `API_ORIGIN`.

## 7. CORS Behavior

API allows:
- `http://localhost:4200`
- `http://127.0.0.1:4200`
- `https://*.vercel.app` via regex

If UI is served from a different origin, update CORS allow list.

## 8. End-to-End Local Flow

1. Start Redis.
2. Start Worker (separate repo).
3. Start API on `127.0.0.1:8080`.
4. Start UI (`python3 server.py` in UI repo).
5. Open UI with local mode:
   - `http://localhost:4200/?api=local`
6. Sign in.
7. Upload file.
8. Verify:
   - API `/upload` returns `job_id`
   - API `/status/{job_id}` updates progress/status
   - `/jobs` returns paginated history

## 9. `/jobs` Pagination Contract

When `limit` is provided, API returns:
- `items`
- `offset`
- `limit`
- `next_offset`
- `has_more`
- `total` (when `include_counts=1`)
- `counts_by_status` (when `include_counts=1`)
- `counts_by_type` (when `include_counts=1`)

Query params:
- `job_type` (`OCR` or `TRANSCRIPTION`)
- `status` (`COMPLETED`, `FAILED`, `CANCELLED`)
- `limit`
- `offset`
- `include_counts`

## 10. Job Cancellation

`POST /jobs/{job_id}/cancel` sets:
- `cancel_requested=1`
- `status=CANCELLED`
- `stage=Cancelled by user`

Worker checks this field and stops processing.

## 11. Signed Download URL

For completed jobs with `gs://` output, API converts to signed URL and sets:
- `download_url`

UI uses this to download output.

## 12. Quick Troubleshooting

### A) `404 /api/jobs` from UI

Cause:
- UI not running via proxy server.

Fix:
- Start UI with `python3 server.py`, not a plain static host.

### B) `Unexpected token '<' ... not valid JSON`

Cause:
- API returned HTML error page instead of JSON (often wrong route/proxy).

Fix:
- Verify UI API mode and server/proxy routing.

### C) CORS blocked

Cause:
- Origin not in allow list.

Fix:
- Use local proxy mode (`?api=local`) or update CORS config.

### D) Jobs stay queued

Cause:
- Worker not running or queue mismatch.

Fix:
- Ensure API `QUEUE_NAME` matches worker queue targets.

## 13. Useful Commands

Run API:
```bash
source .venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8080
```

Smoke script:
```bash
./test_api_local.sh
```

Inspect Redis queue depth (example):
```bash
redis-cli -u "$REDIS_URL" LLEN "${QUEUE_NAME:-doc_jobs}"
```
