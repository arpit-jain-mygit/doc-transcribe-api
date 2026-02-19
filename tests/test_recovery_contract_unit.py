# User value: This test ensures recovery metadata remains stable for user-visible retry transparency.
import unittest

from schemas.responses import JobStatusResponse


class RecoveryContractUnitTests(unittest.TestCase):
    # User value: verifies full recovery fields are accepted for failed job diagnostics.
    def test_accepts_recovery_fields(self):
        resp = JobStatusResponse(
            job_id="job-r1",
            status="FAILED",
            job_type="OCR",
            input_type="pdf",
            attempts=1,
            output_path=None,
            error="failed",
            updated_at="2026-02-19T00:00:00Z",
            recovery_action="retry_with_backoff",
            recovery_reason="TRANSIENT_INFRA",
            recovery_attempt=1,
            recovery_max_attempts=2,
            recovery_trace=[{"action": "retry_with_backoff", "attempt": 1}],
        )
        self.assertEqual(resp.recovery_action, "retry_with_backoff")
        self.assertEqual(resp.recovery_reason, "TRANSIENT_INFRA")
        self.assertEqual(resp.recovery_attempt, 1)
        self.assertEqual(resp.recovery_max_attempts, 2)
        self.assertEqual(len(resp.recovery_trace), 1)

    # User value: keeps older records compatible when recovery fields are not present.
    def test_defaults_when_recovery_fields_missing(self):
        resp = JobStatusResponse(
            job_id="job-r2",
            status="COMPLETED",
            job_type="TRANSCRIPTION",
            input_type="audio",
            attempts=1,
            output_path="gs://bucket/job-r2/out.txt",
            error=None,
            updated_at="2026-02-19T00:00:00Z",
        )
        self.assertIsNone(resp.recovery_action)
        self.assertIsNone(resp.recovery_reason)
        self.assertIsNone(resp.recovery_attempt)
        self.assertIsNone(resp.recovery_max_attempts)
        self.assertEqual(resp.recovery_trace, [])


if __name__ == "__main__":
    unittest.main()
