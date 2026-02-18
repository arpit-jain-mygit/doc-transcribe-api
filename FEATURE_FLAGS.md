# Feature Flags (API)

## Upload and intake flags
- `FEATURE_SMART_INTAKE`
  - `1`: enables Smart Intake capability exposure for pre-upload guidance.
  - `0` (default): keeps Smart Intake disabled and preserves current upload behavior.

- `FEATURE_QUEUE_PARTITIONING`
  - `1`: routes OCR and TRANSCRIPTION to dedicated queues.

- `FEATURE_UPLOAD_QUOTAS`
  - `1`: enforces daily and active-user quota policies.

- `FEATURE_DURATION_PAGE_LIMITS`
  - `1`: enforces OCR page and transcription duration limits.

## Rollout pattern
1. Deploy with flag `0`.
2. Enable in one environment and monitor logs/metrics.
3. Roll back quickly by setting flag back to `0`.
