# User value: This test validates ETA estimation so users get stable pre-upload timing guidance.
import unittest

from services.intake_eta import estimate_eta_sec


class IntakeEtaUnitTests(unittest.TestCase):
    # User value: ensures OCR ETA is derived from page count for clearer expectations.
    def test_eta_ocr_by_pages(self):
        eta = estimate_eta_sec(
            job_type="OCR",
            file_size_bytes=1024,
            media_duration_sec=None,
            pdf_page_count=3,
        )
        self.assertEqual(eta, 60)

    # User value: ensures transcription ETA uses media duration when available.
    def test_eta_transcription_by_duration(self):
        eta = estimate_eta_sec(
            job_type="TRANSCRIPTION",
            file_size_bytes=1024,
            media_duration_sec=120,
            pdf_page_count=None,
        )
        self.assertEqual(eta, 24)

    # User value: ensures fallback ETA is stable for unknown/ambiguous inputs.
    def test_eta_fallback_defaults(self):
        eta = estimate_eta_sec(
            job_type="UNKNOWN",
            file_size_bytes=None,
            media_duration_sec=None,
            pdf_page_count=None,
        )
        self.assertGreaterEqual(eta, 20)


if __name__ == "__main__":
    unittest.main()
