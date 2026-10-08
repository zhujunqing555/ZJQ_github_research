"""Fixtures verify coverage, day boundaries and gross/net distinctions without API access."""
import datetime as dt
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from github_radar import aggregate_history, snapshot_growth, UTC


class PortablePathsTests(unittest.TestCase):
    def default_state(self, environment):
        result = subprocess.run(
            [sys.executable, "-c", "from github_radar import DEFAULT_STATE; print(DEFAULT_STATE)"],
            cwd=Path(__file__).resolve().parent, env=environment,
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())

    def test_custom_codex_home_is_used_without_creating_state(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ, CODEX_HOME=directory)
            expected = Path(directory) / "skill-radars" / "zjq-github-research" / "state" / "star_snapshots.json"
            self.assertEqual(self.default_state(environment), expected)
            self.assertFalse(expected.exists())

    def test_unset_codex_home_uses_user_home(self):
        environment = dict(os.environ)
        environment.pop("CODEX_HOME", None)
        expected = Path.home() / ".codex" / "skill-radars" / "zjq-github-research" / "state" / "star_snapshots.json"
        self.assertEqual(self.default_state(environment), expected)


class HeatTests(unittest.TestCase):
    def setUp(self):
        self.as_of = dt.datetime(2026, 10, 8, 12, tzinfo=UTC)
        self.rows = [
            {"week": int(dt.datetime(2026, 10, 4, tzinfo=UTC).timestamp()), "days": [8, 9, 10, 11, 999, 999, 999], "total": 3035},
            {"week": int(dt.datetime(2026, 9, 27, tzinfo=UTC).timestamp()), "days": [1, 2, 3, 4, 5, 6, 7], "total": 28}]

    def test_trailing_seven_bins_excludes_current_future_days(self):
        heat = aggregate_history(self.rows, self.as_of)
        self.assertEqual(heat["trailing_daily_bins"]["count"], 56)
        self.assertEqual(heat["trailing_daily_bins"]["start_utc_label"], "2026-10-01")
        self.assertEqual(heat["latest_completed_reported_week"]["count"], 28)
        self.assertFalse(heat["exact_168_hours"])
        self.assertEqual(heat["metric"], "stars_created_gross")

    def test_missing_week_is_unknown_not_zero(self):
        heat = aggregate_history(self.rows[:1], self.as_of)
        self.assertIsNone(heat["trailing_daily_bins"]["count"])
        self.assertEqual(heat["trailing_daily_bins"]["covered_days"], 4)
        self.assertEqual(aggregate_history([], self.as_of)["status"], "unavailable")

    def test_actual_zero_bins_are_valid(self):
        rows = [{**row, "days": [0] * 7, "total": 0} for row in self.rows]
        self.assertEqual(aggregate_history(rows, self.as_of)["trailing_daily_bins"]["count"], 0)

    def test_invalid_duplicate_rows_fail_closed(self):
        self.assertEqual(aggregate_history([self.rows[0], self.rows[0]], self.as_of)["status"], "unavailable")

    def test_insufficient_snapshot_age_cannot_show_weekly_heat(self):
        history = [{"repository": "a/b", "stars": 40, "observed_at": "2026-10-02T12:00:00Z"}]
        self.assertIsNone(snapshot_growth(history, "a/b", 50, self.as_of)["count"])

    def test_net_change_can_be_negative_and_is_not_gross(self):
        history = [{"repository": "a/b", "stars": 60, "observed_at": "2026-10-01T12:00:00Z"}]
        result = snapshot_growth(history, "A/B", 50, self.as_of)
        self.assertEqual(result["count"], -10)
        self.assertEqual(result["metric"], "net_total_change")
        self.assertTrue(result["weekly_comparable"])

    def test_old_baseline_shows_actual_interval(self):
        history = [{"repository": "a/b", "stars": 5, "observed_at": "2026-09-01T12:00:00Z"}]
        result = snapshot_growth(history, "a/b", 100, self.as_of)
        self.assertEqual(result["elapsed_days"], 37)
        self.assertFalse(result["weekly_comparable"])


if __name__ == "__main__":
    unittest.main()
