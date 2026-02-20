# User value: This test ensures users always receive deterministic Hindi assist guidance for key statuses/errors.
import unittest

from services.user_assist import derive_user_assist


class UserAssistUnitTests(unittest.TestCase):
    # User value: verifies queued users get clear wait guidance when queue delay is high.
    def test_queued_high_wait_assist(self):
        assist = derive_user_assist(status="QUEUED", queue_wait_sec=120)
        self.assertIsNotNone(assist)
        self.assertEqual(assist["action_type"], "OPEN_HISTORY")
        self.assertIn("कतार", assist["title"])

    # User value: verifies auth failure maps to re-login action instead of generic retry confusion.
    def test_failed_auth_assist(self):
        assist = derive_user_assist(status="FAILED", error_code="AUTH_INVALID_TOKEN")
        self.assertIsNotNone(assist)
        self.assertEqual(assist["action_type"], "RELOGIN")

    # User value: verifies unsupported media errors map to re-upload guidance.
    def test_failed_media_assist(self):
        assist = derive_user_assist(status="FAILED", error_code="MEDIA_DECODE_FAILED")
        self.assertIsNotNone(assist)
        self.assertEqual(assist["action_type"], "REUPLOAD")

    # User value: verifies cancelled jobs guide users to start a fresh upload path.
    def test_cancelled_assist(self):
        assist = derive_user_assist(status="CANCELLED")
        self.assertIsNotNone(assist)
        self.assertEqual(assist["action_type"], "REUPLOAD")


if __name__ == "__main__":
    unittest.main()
