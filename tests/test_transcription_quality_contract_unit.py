# User value: This test keeps transcription quality contract fields stable for reliable UI guidance.
import unittest

from schemas.responses import JobStatusResponse


class TranscriptionQualityContractUnitTests(unittest.TestCase):
    # User value: validates transcription quality payload accepts full metadata for explainable outcomes.
    def test_accepts_transcription_quality_fields(self):
        payload = JobStatusResponse(
            job_id="job-1",
            status="COMPLETED",
            job_type="TRANSCRIPTION",
            input_type="audio",
            attempts=1,
            output_path="gs://bucket/jobs/job-1/out.txt",
            error=None,
            updated_at="2026-02-19T00:00:00Z",
            transcript_quality_score=0.82,
            low_confidence_segments=[2, 5],
            segment_quality=[
                {"segment_index": 1, "score": 0.91, "hint": ""},
                {"segment_index": 2, "score": 0.44, "hint": "High noise"},
            ],
            transcript_quality_hints=["Segment 2 has high noise"],
        )
        self.assertAlmostEqual(payload.transcript_quality_score, 0.82, places=2)
        self.assertEqual(payload.low_confidence_segments, [2, 5])
        self.assertEqual(len(payload.segment_quality), 2)
        self.assertEqual(payload.transcript_quality_hints[0], "Segment 2 has high noise")

    # User value: ensures defaults remain backward-compatible for older transcription jobs.
    def test_defaults_when_transcription_quality_missing(self):
        payload = JobStatusResponse(
            job_id="job-2",
            status="COMPLETED",
            job_type="TRANSCRIPTION",
            input_type="audio",
            attempts=1,
            output_path=None,
            error=None,
            updated_at="2026-02-19T00:00:00Z",
        )
        self.assertIsNone(payload.transcript_quality_score)
        self.assertEqual(payload.low_confidence_segments, [])
        self.assertEqual(payload.segment_quality, [])
        self.assertEqual(payload.transcript_quality_hints, [])


if __name__ == "__main__":
    unittest.main()
