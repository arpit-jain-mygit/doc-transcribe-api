#!/usr/bin/env bash
set -e

API_BASE="http://localhost:8080"

PDF_PATH="/Users/arpitjain/PycharmProjects/doc-transcribe-worker/samples/sample.pdf"
AUDIO_PATH="/Users/arpitjain/PycharmProjects/doc-transcribe-api/sample.mp3"

poll() {
  JOB_ID=$1
  echo "Polling status for $JOB_ID"
  while true; do
    RESP=$(curl -s "$API_BASE/status/$JOB_ID")
    STATUS=$(echo "$RESP" | jq -r .status)
    echo "  status=$STATUS"
    [ "$STATUS" = "COMPLETED" ] && break
    [ "$STATUS" = "FAILED" ] && exit 1
    sleep 1
  done
}

echo "=== OCR TEST ==="
OCR_RESP=$(curl -s -X POST "$API_BASE/upload" \
  -F "file=@$PDF_PATH" \
  -F "type=OCR")

echo "OCR response: $OCR_RESP"
OCR_JOB_ID=$(echo "$OCR_RESP" | jq -r .job_id)
poll "$OCR_JOB_ID"

echo
echo "=== TRANSCRIPTION TEST ==="
TR_RESP=$(curl -s -X POST "$API_BASE/upload" \
  -F "file=@$AUDIO_PATH" \
  -F "type=TRANSCRIPTION")

echo "TRANSCRIPTION response: $TR_RESP"
TR_JOB_ID=$(echo "$TR_RESP" | jq -r .job_id)
poll "$TR_JOB_ID"

echo
echo "=== ALL TESTS PASSED ==="
