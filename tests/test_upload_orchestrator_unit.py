# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import unittest
from io import BytesIO
from fastapi import HTTPException

from services.upload_orchestrator import (
    derive_total_pages,
    derive_idempotent_job_id,
    idempotency_redis_key,
    make_output_filename,
    normalize_idempotency_key,
    resolve_target_queue,
    validate_upload_constraints,
)


class DummyUploadFile:
    # User value: supports __init__ so the OCR/transcription journey stays clear and reliable.
    def __init__(self, filename: str, content_type: str):
        self.filename = filename
        self.content_type = content_type
        self.file = BytesIO(b"dummy")


class UploadOrchestratorUnitTests(unittest.TestCase):
    # User value: normalizes data so users see consistent OCR/transcription results.
    def test_make_output_filename_normalizes(self):
        self.assertEqual(make_output_filename("  नमस्ते रिपोर्ट (v1).pdf"), "v1.txt")
        self.assertEqual(make_output_filename("***.pdf"), "transcript.txt")

    # User value: normalizes data so users see consistent OCR/transcription results.
    def test_normalize_idempotency_key(self):
        self.assertEqual(normalize_idempotency_key(" idem key #1 "), "idemkey1")
        self.assertEqual(normalize_idempotency_key(None), "")
        self.assertEqual(len(normalize_idempotency_key("x" * 200)), 128)

    # User value: supports test_derive_idempotent_job_id_is_deterministic so the OCR/transcription journey stays clear and reliable.
    def test_derive_idempotent_job_id_is_deterministic(self):
        a = derive_idempotent_job_id("a@b.com", "OCR", "same")
        b = derive_idempotent_job_id("a@b.com", "OCR", "same")
        c = derive_idempotent_job_id("a@b.com", "OCR", "different")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 32)

    # User value: supports test_idempotency_redis_key_shape so the OCR/transcription journey stays clear and reliable.
    def test_idempotency_redis_key_shape(self):
        key = idempotency_redis_key("user@example.com", "TRANSCRIPTION", "abc")
        self.assertEqual(key, "upload_idempotency:user@example.com:TRANSCRIPTION:abc")

    # User value: submits user files safely for OCR/transcription processing.
    def test_validate_upload_constraints_ocr_happy_path(self):
        file = DummyUploadFile("sample.pdf", "application/pdf")
        validate_upload_constraints(file=file, job_type="OCR", input_size_bytes=1024)

    # User value: submits user files safely for OCR/transcription processing.
    def test_validate_upload_constraints_transcription_bad_mime(self):
        file = DummyUploadFile("sample.mp3", "application/octet-stream")
        with self.assertRaises(HTTPException) as ctx:
            validate_upload_constraints(file=file, job_type="TRANSCRIPTION", input_size_bytes=1024)
        self.assertEqual(ctx.exception.status_code, 400)
        detail = ctx.exception.detail
        self.assertIsInstance(detail, dict)
        self.assertEqual(detail.get("error_code"), "UNSUPPORTED_MIME_TYPE")

    # User value: routes work so user OCR/transcription jobs are processed correctly.
    def test_resolve_target_queue_default(self):
        q = resolve_target_queue("OCR")
        self.assertIsInstance(q, str)
        self.assertNotEqual(q.strip(), "")

    # User value: supports test_derive_total_pages_for_image so the OCR/transcription journey stays clear and reliable.
    def test_derive_total_pages_for_image(self):
        file = DummyUploadFile("img.png", "image/png")
        self.assertEqual(derive_total_pages(file, "OCR"), 1)


if __name__ == "__main__":
    unittest.main()
