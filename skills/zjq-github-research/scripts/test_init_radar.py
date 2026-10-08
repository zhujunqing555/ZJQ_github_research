"""Check activation boundaries and preservation of user-owned state."""
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from init_radar import activation_date, codex_home, initialize


class InitializationTests(unittest.TestCase):
    def test_activation_window_is_thirty_inclusive_days(self):
        with tempfile.TemporaryDirectory(prefix="zjq-radar-init-") as directory:
            initialize(Path(directory), dt.date(2026, 10, 8), "Asia/Shanghai")
            config = json.loads((Path(directory) / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["bootstrap_until_inclusive"], "2026-11-06")
            self.assertEqual(config["continuous_from"], "2026-11-07")
            self.assertIsNone(config["automation_id"])

    def test_reinitializing_preserves_config_feedback_and_candidates(self):
        with tempfile.TemporaryDirectory(prefix="zjq-radar-init-") as directory:
            root = Path(directory)
            initialize(root, dt.date(2026, 10, 8), "Asia/Shanghai")
            for name in ("config.json", "feedback.json", "candidates.json"):
                (root / name).write_text('{"user_owned":"keep"}\n', encoding="utf-8")
            original = {name:path.read_bytes() for name,path in ((name,root/name) for name in ("config.json","feedback.json","candidates.json"))}
            result = initialize(root, dt.date(2027, 1, 1), "UTC")
            self.assertEqual(result["created"], [])
            for name, content in original.items():
                self.assertEqual((root / name).read_bytes(), content)

    def test_codex_home_override_is_respected(self):
        with patch.dict(os.environ, {"CODEX_HOME": "custom-codex-home"}):
            self.assertEqual(codex_home(), Path("custom-codex-home"))

    def test_bad_date_does_not_become_today(self):
        with self.assertRaises(ValueError):
            activation_date("2026-02-30", "Asia/Shanghai")


if __name__ == "__main__":
    unittest.main()
