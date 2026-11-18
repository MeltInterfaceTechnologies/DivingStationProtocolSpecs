# SPDX-License-Identifier: Apache-2.0
"""Regression checks for oracle failures and live-only history retention."""

from contextlib import nullcontext, redirect_stdout
import io
import subprocess
import unittest
from unittest.mock import patch

from ds_mock.core import Station
from ds_mock.replay import packet_from, run
from ds_mock.server import LIVE_HAPTICS_LIMIT
from tools.check_oracle_sensitivity import rejects
from tools import verify_snapshot


class OracleSensitivityTests(unittest.TestCase):
    def test_assertion_failure_detects_mutation(self):
        def fails():
            self.assertEqual(1, 2)
        output = io.StringIO()
        with redirect_stdout(output):
            rejects("example", nullcontext(), unittest.FunctionTestCase(fails))
        self.assertEqual(output.getvalue(), "detected: example\n")

    def test_unexpected_error_does_not_detect_mutation(self):
        def errors():
            raise RuntimeError("broken test setup")
        with self.assertRaisesRegex(SystemExit, "unexpected test error for mutation: example"):
            rejects("example", nullcontext(), unittest.FunctionTestCase(errors))

    def test_error_is_not_hidden_by_an_assertion_failure(self):
        def fails():
            self.fail("expected assertion")
        def errors():
            raise RuntimeError("unrelated error")
        suite = unittest.TestSuite([unittest.FunctionTestCase(fails), unittest.FunctionTestCase(errors)])
        with self.assertRaisesRegex(SystemExit, "unexpected test error for mutation: example"):
            rejects("example", nullcontext(), suite)

    def test_passing_test_does_not_detect_mutation(self):
        with self.assertRaisesRegex(SystemExit, "oracle missed mutation: example"):
            rejects("example", nullcontext(), unittest.FunctionTestCase(lambda: None))


def command(name, types, args):
    return {"message": {"address": "/DS2/HC/" + name, "types": types, "args": args}}


class HapticsRetentionTests(unittest.TestCase):
    source = ("127.0.0.1", 41000)
    connect = command("Connect", "i", [42000])
    haptics = command("MOCK-L/Haptics/Body", "ifff", [2, 250.0, 0.5, 0.25])

    def test_bounded_history_keeps_newest_accepted_commands(self):
        station = Station(haptics_limit=2)
        station.receive(packet_from(self.connect), self.source, 0)
        for now_ms in (1, 2, 3):
            self.assertEqual(station.receive(packet_from(self.haptics), self.source, now_ms), ("haptics", []))
        expected = [{"at_ms": 2, "source": ["127.0.0.1", 41000], "id": "MOCK-L", "frequency": 250.0, "amplitude": 0.5, "duration": 0.25},
                    {"at_ms": 3, "source": ["127.0.0.1", 41000], "id": "MOCK-L", "frequency": 250.0, "amplitude": 0.5, "duration": 0.25}]
        self.assertEqual(station.haptics, expected)
        bad = command("MOCK-L/Haptics/Body", "ifff", [2, 250.0, 2.0, 0.25])
        self.assertEqual(station.receive(packet_from(bad), self.source, 4), ("discard", []))
        self.assertEqual(station.haptics, expected)

    def test_offline_transcript_keeps_more_than_live_limit(self):
        count = LIVE_HAPTICS_LIMIT + 1
        scenario = {"steps": [dict(self.connect, at_ms=0, op="receive", source=list(self.source))]
                    + [dict(self.haptics, at_ms=at_ms, op="receive", source=list(self.source))
                       for at_ms in range(1, count + 1)]}
        transcript = run(scenario)
        self.assertEqual(len(transcript[-1]["haptics"]), count)
        self.assertEqual(transcript[-1]["haptics"][0]["at_ms"], 1)
        self.assertEqual(transcript[-1]["haptics"][-1]["at_ms"], count)
        self.assertEqual(len(transcript[1]["haptics"]), 1)  # earlier snapshots remain complete and unchanged

    def test_offline_replay_rejects_a_truncation_policy(self):
        with self.assertRaisesRegex(ValueError, "complete haptics history"):
            run({"config": {"haptics_limit": 1}, "steps": []})

    def test_invalid_retention_limit_is_rejected(self):
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                Station(haptics_limit=limit)


class SnapshotRevisionTests(unittest.TestCase):
    def test_missing_revision_explains_repository_scope(self):
        with patch.object(verify_snapshot, "git_bytes", side_effect=subprocess.CalledProcessError(128, ["git"])):
            with self.assertRaisesRegex(SystemExit, "Repository-specific commit SHAs are not interchangeable"):
                verify_snapshot.verify_revision("mock_commit", "1" * 40, "example/review")

    def test_revision_rejects_a_mutable_branch_name(self):
        with self.assertRaisesRegex(SystemExit, "full immutable commit SHA"):
            verify_snapshot.verify_revision("mock_commit", "main", "example/review")


if __name__ == "__main__":
    unittest.main()
