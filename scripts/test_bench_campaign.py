"""Campaign integration tests use small subprocesses, never mining hardware."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_campaign as campaign
import benchctl


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "source.txt"
        self.input.write_text("original source")
        self.artifact = self.root / "miner"
        self.artifact.write_text("frozen binary")
        self.plan = self.root / "plan.json"
        self.output = self.root / "results"
        self.trace = self.root / "trace"
        self.experiment = {
            "id": "candidate", "hypothesis": "Reduce dependencies", "cwd": ".",
            "inputs": ["source.txt"], "artifacts": ["miner"],
            "stages": {
                "build": self.command("build"),
                "correctness": self.command("correctness"),
                "screen": self.measurement("screen", 2, 110),
                "confirm": self.measurement("confirm", 4, 110),
            },
        }
        self.write_plan()
        for target, value in (
            ("bench_campaign.admission", None),
            ("bench_campaign.lab.collect_preflight", {"host": "fixture"}),
            ("bench_campaign.lab.tool_version", "test-toolchain"),
        ):
            patch = mock.patch(target, return_value=value)
            patch.start()
            self.addCleanup(patch.stop)
        self.lock_patch = mock.patch("bench_campaign.Path.home", return_value=self.root)
        self.lock_patch.start()
        self.addCleanup(self.lock_patch.stop)

    def command(self, stage, extra=""):
        script = ("from pathlib import Path\n"
                  f"with Path({str(self.trace)!r}).open('a') as f: f.write({stage!r} + '\\n')\n" + extra)
        return {"argv": ["{python}", "-c", script], "timeout_seconds": 10}

    def measurement(self, stage, pairs, candidate):
        rows = "variant\tpair\torder\tavg_hps\n"
        for pair in range(pairs):
            rows += f"baseline\t{pair}\t{1 if pair % 2 == 0 else 2}\t100\n"
            rows += f"candidate\t{pair}\t{2 if pair % 2 == 0 else 1}\t{candidate}\n"
        spec = self.command(stage, f"Path('{{stage_dir}}/results.tsv').write_text({rows!r})\n")
        spec["pairs"] = pairs
        return spec

    def write_plan(self, experiments=None):
        self.plan.write_text(json.dumps({"schema": campaign.SCHEMA, "experiments": experiments or [self.experiment]}))

    def run_campaign(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return campaign.run_campaign(self.plan, self.output, **kwargs)

    def state(self):
        return json.loads((self.output / "campaign.json").read_text())

    def test_success_records_provenance_budgets_fresh_evidence_and_skips_completed(self):
        self.assertEqual(self.run_campaign(), 0)
        state = self.state()
        entry = state["experiments"]["candidate"]
        self.assertEqual(entry["status"], "accepted")
        self.assertEqual(entry["artifacts"][str(self.artifact)], benchctl.sha256_file(self.artifact))
        self.assertEqual((self.output / "candidate/inputs/0-source.txt").read_text(), "original source")
        screen = entry["stages"]["screen"][0]
        confirm = entry["stages"]["confirm"][0]
        self.assertNotEqual(screen["directory"], confirm["directory"])
        self.assertEqual(confirm["comparison"]["pair_count"], 4)
        self.assertGreater(state["phase_seconds"]["confirm"], 0)
        trace = self.trace.read_text()
        self.assertEqual(self.run_campaign(resume=True), 0)
        self.assertEqual(self.trace.read_text(), trace)

    def test_clear_screen_loser_never_gets_confirmation(self):
        self.experiment["stages"]["screen"] = self.measurement("screen", 2, 90)
        self.write_plan()
        self.assertEqual(self.run_campaign(), 0)
        self.assertEqual(self.state()["experiments"]["candidate"]["status"], "rejected")
        self.assertNotIn("confirm", self.trace.read_text())

    def test_tie_passes_screen_but_fails_confirmation_without_automatic_retry(self):
        for stage, pairs in [("screen", 2), ("confirm", 4)]:
            self.experiment["stages"][stage] = self.measurement(stage, pairs, 100)
        self.write_plan()
        self.assertEqual(self.run_campaign(), 0)
        self.assertIn("improvement", self.state()["experiments"]["candidate"]["reason"])
        self.assertEqual(self.run_campaign(resume=True), 0)
        self.assertEqual(self.trace.read_text().count("confirm"), 1)

    def test_bad_evidence_is_failure_not_rejection_and_queue_continues(self):
        self.experiment["stages"]["screen"] = self.command("screen")
        second = copy.deepcopy(self.experiment)
        second["id"] = "second"
        second["stages"]["screen"] = self.measurement("screen", 2, 110)
        self.write_plan([self.experiment, second])
        self.assertEqual(self.run_campaign(), 1)
        entries = self.state()["experiments"]
        self.assertEqual(entries["candidate"]["status"], "failed")
        self.assertEqual(entries["second"]["status"], "accepted")

    def test_nonzero_correctness_stops_candidate(self):
        self.experiment["stages"]["correctness"] = self.command("correctness", "raise SystemExit(7)")
        self.write_plan()
        self.assertEqual(self.run_campaign(), 1)
        self.assertNotIn("screen", self.trace.read_text())
        self.assertIn("exit 7", self.state()["experiments"]["candidate"]["reason"])

    def test_timeout_is_persisted(self):
        self.experiment["stages"]["build"] = self.command("build", "import time; time.sleep(10)")
        self.experiment["stages"]["build"]["timeout_seconds"] = 0.1
        self.write_plan()
        self.assertEqual(self.run_campaign(), 1)
        attempt = self.state()["experiments"]["candidate"]["stages"]["build"][0]
        self.assertEqual(attempt["status"], "timed_out")
        self.assertEqual(attempt["exit_code"], 124)

    def test_interruption_reruns_only_unfinished_stage_with_new_directory(self):
        real_run = campaign.run_command
        def interrupt_confirm(argv, cwd, directory, timeout, lock_fd):
            if directory.parent.name == "confirm":
                return {"status": "interrupted", "exit_code": 130, "duration_seconds": 0.05}
            return real_run(argv, cwd, directory, timeout, lock_fd)
        with mock.patch("bench_campaign.run_command", side_effect=interrupt_confirm):
            self.assertEqual(self.run_campaign(), 130)
        self.assertEqual(self.run_campaign(resume=True), 0)
        entry = self.state()["experiments"]["candidate"]
        self.assertEqual(len(entry["stages"]["confirm"]), 2)
        self.assertTrue(entry["stages"]["confirm"][1]["directory"].endswith("attempt-2"))
        self.assertEqual(self.trace.read_text().splitlines(), ["build", "correctness", "screen", "confirm"])

    def test_resume_rejects_changed_source_binary_plan_and_results(self):
        self.assertEqual(self.run_campaign(), 0)
        changes = [self.input, self.artifact, self.plan,
                   Path(self.state()["experiments"]["candidate"]["stages"]["screen"][0]["directory"]) / "results.tsv"]
        for path in changes:
            original = path.read_text()
            if path == self.plan:
                self.experiment["hypothesis"] = "Different hypothesis"
                self.write_plan()
            else:
                path.write_text(original + "changed")
            with self.subTest(path=path), self.assertRaises(campaign.CampaignError):
                self.run_campaign(resume=True)
            path.write_text(original)

    def test_build_artifact_identity_frozen_before_interruption(self):
        real_run = campaign.run_command
        def interrupted(argv, cwd, directory, timeout, lock_fd):
            if directory.parent.name == "correctness":
                return {"status": "interrupted", "exit_code": 130}
            return real_run(argv, cwd, directory, timeout, lock_fd)
        with mock.patch("bench_campaign.run_command", side_effect=interrupted):
            self.assertEqual(self.run_campaign(), 130)
        self.artifact.write_text("replaced")
        with self.assertRaisesRegex(campaign.CampaignError, "artifacts changed"):
            self.run_campaign(resume=True)

    def test_literal_arguments_are_not_shell_evaluated(self):
        marker = self.root / "should-not-exist"
        spec = self.command("build", "import sys; assert sys.argv[1].startswith('$(touch')")
        spec["argv"].append(f"$(touch {marker})")
        self.experiment["stages"]["build"] = spec
        self.write_plan()
        self.assertEqual(self.run_campaign(), 0)
        self.assertFalse(marker.exists())

    def test_fixed_pair_budget_cannot_be_shortened_or_extended(self):
        for pairs in [1, 3]:
            spec = self.measurement("screen", pairs, 110)
            spec["pairs"] = 2
            self.experiment["stages"]["screen"] = spec
            self.write_plan()
            self.output = self.root / f"results-{pairs}"
            self.assertEqual(self.run_campaign(), 1)
            self.assertNotIn("confirm", self.state()["experiments"]["candidate"]["stages"])

    def test_schema_errors_rejected_before_any_command(self):
        for field, value in [("timeout_seconds", -1), ("timeout_seconds", float("nan")),
                             ("argv", "echo bad"), ("unknown", 1)]:
            original = copy.deepcopy(self.experiment)
            self.experiment["stages"]["build"][field] = value
            self.write_plan()
            with self.subTest(field=field), self.assertRaises(campaign.CampaignError):
                self.run_campaign()
            self.experiment = original
        self.assertFalse(self.trace.exists())

    def test_concurrent_campaign_is_rejected_and_lock_released(self):
        lock = self.root / ".cache/seine-benchctl/campaign.lock"
        with campaign.exclusive_lock(lock):
            with self.assertRaisesRegex(campaign.CampaignError, "another campaign"):
                self.run_campaign()
        self.assertEqual(self.run_campaign(), 0)

    def test_status_does_not_touch_host_or_run_commands(self):
        self.assertEqual(self.run_campaign(), 0)
        trace = self.trace.read_text()
        self.input.unlink()
        with mock.patch("bench_campaign.provenance", side_effect=AssertionError("no host capture")):
            self.assertEqual(self.run_campaign(status_only=True), 0)
        self.assertEqual(trace, self.trace.read_text())

    def test_host_change_and_unclean_crash_block_resume(self):
        self.assertEqual(self.run_campaign(), 0)
        with mock.patch("bench_campaign.platform.node", return_value="different-host"):
            with self.assertRaisesRegex(campaign.CampaignError, "host, toolchain"):
                self.run_campaign(resume=True)
        state = self.state()
        state["experiments"]["candidate"]["stages"]["confirm"][-1]["status"] = "running"
        (self.output / "campaign.json").write_text(json.dumps(state))
        with self.assertRaisesRegex(campaign.CampaignError, "without cleanup"):
            self.run_campaign(resume=True)

    def test_changed_artifact_during_measurement_never_passes(self):
        spec = self.experiment["stages"]["screen"]
        spec["argv"][2] += f"Path({str(self.artifact)!r}).write_text('mutated')\n"
        self.write_plan()
        self.assertEqual(self.run_campaign(), 1)
        self.assertIn("artifacts changed", self.state()["experiments"]["candidate"]["reason"])

    def test_capture_failure_is_persisted_as_failure(self):
        with mock.patch("bench_campaign.lab.collect_preflight", side_effect=OSError("capture unavailable")):
            self.assertEqual(self.run_campaign(), 1)
        entry = self.state()["experiments"]["candidate"]
        self.assertEqual(entry["status"], "failed")
        self.assertIn("capture unavailable", entry["reason"])

    def test_unbalanced_order_is_not_accepted(self):
        spec = self.measurement("screen", 2, 110)
        spec["argv"][2] = spec["argv"][2].replace("baseline\\t1\\t2", "baseline\\t1\\t1").replace("candidate\\t1\\t1", "candidate\\t1\\t2")
        self.experiment["stages"]["screen"] = spec
        self.write_plan()
        self.assertEqual(self.run_campaign(), 1)
        self.assertIn("balanced", self.state()["experiments"]["candidate"]["reason"])

    def test_admission_blocks_before_commands_or_telemetry(self):
        with mock.patch("bench_campaign.admission", side_effect=campaign.CampaignError("Gaming Mode")):
            with self.assertRaisesRegex(campaign.CampaignError, "Gaming Mode"):
                self.run_campaign()
        self.assertFalse(self.trace.exists())
        self.assertEqual(self.run_campaign(resume=True), 0)

    def test_interruption_during_analysis_never_skips_confirmation_gate(self):
        real_compare = campaign.compare_stage
        def interrupted(stage, spec, directory):
            if stage == "confirm":
                raise KeyboardInterrupt
            return real_compare(stage, spec, directory)
        with mock.patch("bench_campaign.compare_stage", side_effect=interrupted):
            self.assertEqual(self.run_campaign(), 130)
        entry = self.state()["experiments"]["candidate"]
        self.assertEqual(entry["stages"]["confirm"][-1]["status"], "interrupted")
        self.assertEqual(self.run_campaign(resume=True), 0)
        self.assertEqual(len(self.state()["experiments"]["candidate"]["stages"]["confirm"]), 2)

    def test_resume_finishes_decision_without_rerunning_rejected_stage(self):
        self.experiment["stages"]["screen"] = self.measurement("screen", 2, 90)
        self.write_plan()
        self.assertEqual(self.run_campaign(), 0)
        state = self.state()
        state["experiments"]["candidate"]["status"] = "running"
        (self.output / "campaign.json").write_text(json.dumps(state))
        trace = self.trace.read_text()
        self.assertEqual(self.run_campaign(resume=True), 0)
        self.assertEqual(trace, self.trace.read_text())
        self.assertEqual(self.state()["experiments"]["candidate"]["status"], "rejected")

    @unittest.skipUnless(shutil.which("bash") and os.name == "posix", "Bash harness on POSIX")
    def test_real_cpu_ab_harness_feeds_campaign_gates(self):
        repo = Path(campaign.__file__).resolve().parents[1]
        binaries = []
        for name, rate in [("baseline", 100), ("candidate", 110)]:
            binary = self.root / name
            binary.write_text(
                f"#!{sys.executable}\nimport sys,json\nfrom pathlib import Path\n"
                "args=sys.argv[1:]\n"
                "dest=Path(args[args.index('--bench-output')+1])\n"
                f"dest.write_text(json.dumps(dict(schema_version=15,bench_kind='backend',avg_hps={rate},"
                f"median_hps={rate},total_counted_hashes={rate},total_late_hashes=0)))\n")
            binary.chmod(0o700)
            binaries.append(str(binary))
        self.experiment["artifacts"] = binaries
        for name, pairs in [("screen", 2), ("confirm", 4)]:
            self.experiment["stages"][name] = {
                "argv": ["bash", str(repo / "scripts/bench_cpu_ab.sh"),
                         "--baseline-dir", str(repo), "--candidate-dir", str(repo),
                         "--baseline-binary", binaries[0], "--candidate-binary", binaries[1],
                         "--bench-kind", "backend", "--pairs", str(pairs), "--bench-secs", "1",
                         "--bench-rounds", "1", "--bench-warmup-rounds", "0", "--cooldown-secs", "0",
                         "--output-dir", "{stage_dir}"], "timeout_seconds": 30, "pairs": pairs}
        self.write_plan()
        self.assertEqual(self.run_campaign(), 0)
        entry = self.state()["experiments"]["candidate"]
        self.assertEqual(entry["status"], "accepted")
        self.assertAlmostEqual(entry["stages"]["confirm"][0]["comparison"]["comparison"]["paired_geometric_delta_pct"], 10)

    @unittest.skipUnless(os.name == "posix", "POSIX signal delivery")
    def test_real_sigterm_cleans_up_and_resume_keeps_completed_work(self):
        marker = self.root / "ready"
        self.experiment["stages"]["confirm"]["argv"][2] += (
            f"\nimport time\nmarker = Path({str(marker)!r})\n"
            "if not marker.exists():\n    marker.touch()\n    time.sleep(30)\n")
        self.write_plan()
        wrapper = (
            f"import sys; sys.path.insert(0, {str(Path(campaign.__file__).parent)!r})\n"
            "import bench_campaign as c\n"
            "c.admission = lambda: None\n"
            "c.lab.collect_preflight = lambda *args: {'host': 'fixture'}\n"
            "c.lab.tool_version = lambda *args: 'test-toolchain'\n"
            f"c.Path.home = classmethod(lambda cls: c.Path({str(self.root)!r}))\n"
            f"sys.exit(c.run_campaign(c.Path({str(self.plan)!r}), c.Path({str(self.output)!r})))\n")
        process = subprocess.Popen([sys.executable, "-c", wrapper], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            process.send_signal(signal.SIGTERM)
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 130, stderr)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
        self.assertEqual(self.state()["experiments"]["candidate"]["status"], "interrupted")
        self.assertEqual(self.run_campaign(resume=True), 0)
        self.assertEqual(self.trace.read_text().splitlines(), ["build", "correctness", "screen", "confirm", "confirm"])

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_timeout_kills_grandchild_even_when_parent_exits_on_term(self):
        directory = self.root / "process-test"
        directory.mkdir()
        marker = self.root / "leaked-child"
        child = f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).touch()"
        script = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(10)"
        with campaign.exclusive_lock(self.root / "process.lock") as fd:
            result = campaign.run_command([sys.executable, "-c", script], str(self.root), directory, 0.2, fd)
        self.assertEqual(result["status"], "timed_out")
        time.sleep(1.1)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
