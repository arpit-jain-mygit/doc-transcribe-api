# User value: This test validates pre-upload warnings so users get clear and consistent intake guidance.
import unittest

from services.intake_precheck import build_precheck_warnings


class IntakePrecheckWarningsUnitTests(unittest.TestCase):
    # User value: validates warning generation for large OCR files.
    def test_warns_large_ocr_file(self):
        warnings = build_precheck_warnings(
            job_type="OCR",
            filename="sample.pdf",
            mime_type="application/pdf",
            file_size_bytes=24 * 1024 * 1024,
            media_duration_sec=None,
            pdf_page_count=1,
        )
        codes = {w["code"] for w in warnings}
        self.assertIn("LARGE_FILE", codes)

    # User value: validates warning generation for long transcription files.
    def test_warns_long_media(self):
        warnings = build_precheck_warnings(
            job_type="TRANSCRIPTION",
            filename="sample.mp3",
            mime_type="audio/mpeg",
            file_size_bytes=1024,
            media_duration_sec=1200,
            pdf_page_count=None,
        )
        codes = {w["code"] for w in warnings}
        self.assertIn("LONG_MEDIA", codes)

    # User value: validates warning generation for high-page OCR input.
    def test_warns_high_page_count(self):
        warnings = build_precheck_warnings(
            job_type="OCR",
            filename="book.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            media_duration_sec=None,
            pdf_page_count=80,
        )
        codes = {w["code"] for w in warnings}
        self.assertIn("HIGH_PAGE_COUNT", codes)

    # User value: validates warning generation for mismatched metadata.
    def test_warns_mime_extension_mismatch(self):
        warnings = build_precheck_warnings(
            job_type="OCR",
            filename="scan.pdf",
            mime_type="audio/mpeg",
            file_size_bytes=1024,
            media_duration_sec=None,
            pdf_page_count=1,
        )
        codes = {w["code"] for w in warnings}
        self.assertIn("MIME_EXTENSION_MISMATCH", codes)

    # User value: validates stable no-warning behavior for healthy, small files.
    def test_no_warning_for_small_clean_input(self):
        warnings = build_precheck_warnings(
            job_type="OCR",
            filename="scan.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            media_duration_sec=None,
            pdf_page_count=1,
        )
        self.assertEqual(warnings, [])

    # User value: validates warning generation when file type cannot be inferred reliably.
    def test_warns_uncertain_file_type(self):
        warnings = build_precheck_warnings(
            job_type="OCR",
            filename="payload.bin",
            mime_type="application/octet-stream",
            file_size_bytes=1024,
            media_duration_sec=None,
            pdf_page_count=1,
        )
        codes = {w["code"] for w in warnings}
        self.assertIn("UNCERTAIN_FILE_TYPE", codes)


if __name__ == "__main__":
    unittest.main()
