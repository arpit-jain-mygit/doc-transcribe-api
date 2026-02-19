# User value: This test validates intake endpoint behavior so users get predictable pre-upload guidance.
import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from routes.intake import intake_precheck
from schemas.requests import IntakePrecheckRequest


class IntakeEndpointUnitTests(unittest.TestCase):
    # User value: ensures disabled feature gate does not change user flow unexpectedly.
    def test_precheck_disabled_returns_404(self):
        payload = IntakePrecheckRequest(filename="sample.pdf", mime_type="application/pdf")

        async def run_case():
            with patch("routes.intake.is_smart_intake_enabled", return_value=False):
                with self.assertRaises(HTTPException) as ctx:
                    await intake_precheck(payload=payload, user={"email": "u@example.com"})
                self.assertEqual(ctx.exception.status_code, 404)

        asyncio.run(run_case())

    # User value: ensures enabled precheck returns route, warnings, confidence, ETA, and metrics/log hooks.
    def test_precheck_enabled_returns_payload(self):
        payload = IntakePrecheckRequest(
            filename="sample.mp3",
            mime_type="audio/mpeg",
            file_size_bytes=1024,
            media_duration_sec=60,
        )

        async def run_case():
            with patch("routes.intake.is_smart_intake_enabled", return_value=True):
                with patch("routes.intake.incr") as mock_incr:
                    out = await intake_precheck(payload=payload, user={"email": "u@example.com"})
                    self.assertEqual(out.detected_job_type, "TRANSCRIPTION")
                    self.assertGreaterEqual(out.confidence, 0.0)
                    self.assertGreater(out.eta_sec, 0)
                    self.assertEqual(mock_incr.call_count, 3)

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
