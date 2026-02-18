# User value: This test protects users from intake contract drift before UI integration.
import unittest

from schemas.requests import IntakePrecheckRequest
from schemas.responses import IntakePrecheckResponse


class TestIntakeContract(unittest.TestCase):
    # User value: Ensures users can send minimal precheck metadata safely.
    def test_request_schema_minimal(self):
        req = IntakePrecheckRequest(filename="sample.pdf")
        self.assertEqual(req.filename, "sample.pdf")

    # User value: Ensures users always receive stable precheck response defaults.
    def test_response_schema_defaults(self):
        resp = IntakePrecheckResponse(detected_job_type="OCR")
        self.assertEqual(resp.detected_job_type, "OCR")
        self.assertEqual(resp.warnings, [])
        self.assertEqual(resp.reasons, [])
        self.assertEqual(resp.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
