# User value: This test verifies deterministic routing so users get predictable OCR/transcription intake decisions.
import unittest

from services.intake_router import detect_route_from_metadata


class IntakeRouterUnitTests(unittest.TestCase):
    # User value: confirms common OCR files route correctly before upload.
    def test_detect_route_pdf_prefers_ocr(self):
        out = detect_route_from_metadata("sample.pdf", "application/pdf")
        self.assertEqual(out["detected_job_type"], "OCR")
        self.assertGreaterEqual(out["confidence"], 0.95)

    # User value: confirms common transcription files route correctly before upload.
    def test_detect_route_mp3_prefers_transcription(self):
        out = detect_route_from_metadata("sample.mp3", "audio/mpeg")
        self.assertEqual(out["detected_job_type"], "TRANSCRIPTION")
        self.assertGreaterEqual(out["confidence"], 0.95)

    # User value: handles missing extension by using MIME so users still get guidance.
    def test_detect_route_mime_only(self):
        out = detect_route_from_metadata("sample", "video/mp4")
        self.assertEqual(out["detected_job_type"], "TRANSCRIPTION")
        self.assertIn("extension_unknown", out["reasons"])

    # User value: keeps routing deterministic even for conflicting metadata.
    def test_detect_route_mismatch_prefers_extension(self):
        out = detect_route_from_metadata("scan.pdf", "audio/mpeg")
        self.assertEqual(out["detected_job_type"], "OCR")
        self.assertIn("mime_extension_mismatch", out["reasons"])

    # User value: returns strict unknown fallback when no signal exists.
    def test_detect_route_unknown(self):
        out = detect_route_from_metadata("archive.bin", "application/octet-stream")
        self.assertEqual(out["detected_job_type"], "UNKNOWN")
        self.assertEqual(out["confidence"], 0.0)
        self.assertIn("no_route_signal", out["reasons"])


if __name__ == "__main__":
    unittest.main()
