# User value: This file verifies feature-flag safety so users get predictable OCR/transcription behavior.
import importlib
import os
import unittest

import startup_env


class FeatureFlagsUnitTests(unittest.TestCase):
    # User value: supports setUp so users get deterministic behavior regardless of local env leftovers.
    def setUp(self):
        self._old = os.environ.get("FEATURE_SMART_INTAKE")

    # User value: supports tearDown so users get deterministic behavior regardless of local env leftovers.
    def tearDown(self):
        if self._old is None:
            os.environ.pop("FEATURE_SMART_INTAKE", None)
        else:
            os.environ["FEATURE_SMART_INTAKE"] = self._old

    # User value: confirms explicit enablement works so intake guidance can be rolled out safely.
    def test_smart_intake_flag_enabled(self):
        os.environ["FEATURE_SMART_INTAKE"] = "1"
        import services.feature_flags as ff

        ff = importlib.reload(ff)
        self.assertTrue(ff.is_smart_intake_enabled())

    # User value: confirms default/disabled path keeps current OCR/transcription flow unchanged.
    def test_smart_intake_flag_disabled(self):
        os.environ["FEATURE_SMART_INTAKE"] = "0"
        import services.feature_flags as ff

        ff = importlib.reload(ff)
        self.assertFalse(ff.is_smart_intake_enabled())

    # User value: prevents bad deploy config that could break OCR/transcription startup behavior.
    def test_validate_bool_flag_env_rejects_invalid(self):
        errors = []
        os.environ["FEATURE_SMART_INTAKE"] = "maybe"
        startup_env._validate_bool_flag_env("FEATURE_SMART_INTAKE", errors)
        self.assertTrue(errors)
        self.assertIn("FEATURE_SMART_INTAKE must be one of", errors[0])


if __name__ == "__main__":
    unittest.main()
