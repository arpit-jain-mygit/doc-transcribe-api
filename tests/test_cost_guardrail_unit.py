# User value: This test validates cost guardrail decisions so users get predictable allow/warn/block behavior.
import unittest

from services.cost_guardrail import evaluate_cost_guardrail


class CostGuardrailUnitTests(unittest.TestCase):
    # User value: verifies small jobs stay frictionless and are allowed by policy.
    def test_allow_for_small_ocr(self):
        out = evaluate_cost_guardrail(
            job_type="OCR",
            file_size_bytes=150_000,
            media_duration_sec=None,
            pdf_page_count=1,
        )
        self.assertEqual(out["policy_decision"], "ALLOW")
        self.assertEqual(out["estimated_effort"], "LOW")

    # User value: verifies larger but acceptable jobs produce warning guidance before submit.
    def test_warn_for_medium_transcription(self):
        out = evaluate_cost_guardrail(
            job_type="TRANSCRIPTION",
            file_size_bytes=18 * 1024 * 1024,
            media_duration_sec=50 * 60,
            pdf_page_count=None,
        )
        self.assertIn(out["policy_decision"], {"WARN", "BLOCK"})
        self.assertIn(out["estimated_effort"], {"MEDIUM", "HIGH"})

    # User value: verifies very expensive jobs are blocked deterministically.
    def test_block_for_very_large_ocr(self):
        out = evaluate_cost_guardrail(
            job_type="OCR",
            file_size_bytes=80 * 1024 * 1024,
            media_duration_sec=None,
            pdf_page_count=220,
        )
        self.assertEqual(out["policy_decision"], "BLOCK")
        self.assertEqual(out["estimated_cost_band"], "VERY_HIGH")


if __name__ == "__main__":
    unittest.main()
