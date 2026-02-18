# User value: This test protects users from intake contract drift before UI integration.
import unittest

from pydantic import ValidationError
from schemas.requests import IntakePrecheckRequest
from schemas.responses import IntakePrecheckResponse


class TestIntakeContract(unittest.TestCase):
    # User value: Ensures users can send minimal precheck metadata safely.
    def test_request_schema_minimal(self):
        req = IntakePrecheckRequest(filename="sample.pdf")
        self.assertEqual(req.filename, "sample.pdf")

    # User value: Prevents invalid empty filenames from entering precheck flow.
    def test_request_schema_rejects_empty_filename(self):
        with self.assertRaises(ValidationError):
            IntakePrecheckRequest(filename="")

    # User value: Prevents null filenames from entering precheck flow.
    def test_request_schema_rejects_none_filename(self):
        with self.assertRaises(ValidationError):
            IntakePrecheckRequest(filename=None)

    # User value: Ensures users always receive stable precheck response defaults.
    def test_response_schema_defaults(self):
        resp = IntakePrecheckResponse(detected_job_type="OCR")
        self.assertEqual(resp.detected_job_type, "OCR")
        self.assertEqual(resp.warnings, [])
        self.assertEqual(resp.reasons, [])
        self.assertEqual(resp.confidence, 0.0)

    # User value: Protects users from invalid confidence ranges in precheck output.
    def test_response_schema_rejects_invalid_confidence(self):
        with self.assertRaises(ValidationError):
            IntakePrecheckResponse(detected_job_type="OCR", confidence=1.5)

    # User value: Protects users from invalid route labels in precheck output.
    def test_response_schema_rejects_invalid_job_type(self):
        with self.assertRaises(ValidationError):
            IntakePrecheckResponse(detected_job_type="VIDEO")


if __name__ == "__main__":
    unittest.main()
