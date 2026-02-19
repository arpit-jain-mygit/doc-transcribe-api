# User value: This test protects OCR quality contract stability so users get consistent quality feedback fields.
import unittest

from pydantic import ValidationError

from schemas.responses import JobStatusResponse


class OCRQualityContractUnitTests(unittest.TestCase):
    # User value: ensures valid OCR quality metadata is accepted and exposed to users.
    def test_job_status_accepts_quality_fields(self):
        resp = JobStatusResponse(
            job_id="job-123",
            status="COMPLETED",
            job_type="OCR",
            input_type="application/pdf",
            attempts=1,
            output_path="gs://bucket/jobs/job-123/sample.txt",
            error=None,
            updated_at="2026-02-18T00:00:00Z",
            ocr_quality_score=0.81,
            low_confidence_pages=[2, 5],
            quality_hints=["Page 2 low contrast", "Page 5 blurry"],
        )
        self.assertEqual(resp.ocr_quality_score, 0.81)
        self.assertEqual(resp.low_confidence_pages, [2, 5])
        self.assertEqual(len(resp.quality_hints), 2)

    # User value: keeps default payload backward-compatible when quality metadata is not yet emitted.
    def test_job_status_quality_defaults(self):
        resp = JobStatusResponse(
            job_id="job-124",
            status="COMPLETED",
            job_type="OCR",
            input_type="application/pdf",
            attempts=1,
            output_path="gs://bucket/jobs/job-124/sample.txt",
            error=None,
            updated_at="2026-02-18T00:00:00Z",
        )
        self.assertIsNone(resp.ocr_quality_score)
        self.assertEqual(resp.low_confidence_pages, [])
        self.assertEqual(resp.quality_hints, [])

    # User value: blocks invalid quality scores that would confuse users and downstream UI logic.
    def test_job_status_rejects_invalid_quality_score(self):
        with self.assertRaises(ValidationError):
            JobStatusResponse(
                job_id="job-125",
                status="COMPLETED",
                job_type="OCR",
                input_type="application/pdf",
                attempts=1,
                output_path="gs://bucket/jobs/job-125/sample.txt",
                error=None,
                updated_at="2026-02-18T00:00:00Z",
                ocr_quality_score=1.5,
            )


if __name__ == "__main__":
    unittest.main()
