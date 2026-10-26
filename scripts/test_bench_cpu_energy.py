#!/usr/bin/env python3
"""Counter arithmetic, evidence rejection and owned-process cleanup checks."""
import argparse
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import bench_cpu_energy as energy


def report():
    backend = {key: 0 for key in energy.ERROR_COUNTERS}
    backend.update(backend="cpu", backend_id=1, hashes=12, memory_regular_workers=1,
                   memory_regular_bytes=2 * energy.GIB)
    return {"schema_version": 14, "bench_kind": "end_to_end", "backends": ["cpu#1"],
            "pow_fingerprint": {"m": 2097152, "t": 1, "p": 1},
            "environment": {"cpu_identity": {"family": 26}},
            "warmup_rounds": 0, "cpu_threads": 1, "rounds": 1, "bench_secs": 1,
            "total_hashes": 12,
            "config_fingerprint": {"cpu_page_mode": "regular", "cpu_autotune_threads": False,
                                   "cpu_affinity": "auto",
                                   "cpu_kernel": "avx2", "cpu_kernel_requested": "avx2"},
            "runs": [{"hashes": 12, "counted_hashes": 10, "late_hashes": 2,
                      "backend_runs": [backend]}]}


@unittest.skipUnless(sys.platform == "linux", "Linux powercap paths and process groups")
class EnergyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.zone = self.root / "intel-rapl:0"
        self.zone.mkdir()
        (self.zone / "name").write_text("package-0\n")
        (self.zone / "energy_uj").write_text("0\n")
        (self.zone / "max_energy_range_uj").write_text("1000000000\n")
        self.zones = energy.discover(self.root)

    def sample(self, seconds, uj):
        return {"monotonic": seconds, "read_span_secs": 0,
                "energy_uj": {str(self.zone): uj}}

    def test_single_wrap_and_ordinary_increase(self):
        self.assertEqual(energy.interval_joules(self.sample(0, 10_000_000), self.sample(.25, 20_000_000),
                                               self.zones, 1000)[str(self.zone)], 10)
        self.assertEqual(energy.interval_joules(self.sample(0, 950_000_000), self.sample(.25, 50_000_000),
                                               self.zones, 1000)[str(self.zone)], 100)

    def test_ambiguous_wraps_and_implausible_resets_are_rejected(self):
        for start, end, duration in [(0, 0, 2), (100_000_000, 10_000_000, .25), (0, 1, 0)]:
            with self.subTest(start=start, end=end, duration=duration), self.assertRaises(energy.EnergyError):
                energy.interval_joules(self.sample(0, start), self.sample(duration, end), self.zones, 1000)

    def test_child_domains_and_aliases_are_not_double_counted(self):
        child = self.zone / "intel-rapl:0:0"
        child.mkdir()
        for name, value in {"name": "core", "energy_uj": "0", "max_energy_range_uj": "1000000000"}.items():
            (child / name).write_text(value)
        (self.root / "intel-rapl:alias").symlink_to(self.zone)
        zones = energy.discover(self.root)
        self.assertEqual(len(zones), 2)
        self.assertEqual(energy.select_packages(zones, None), self.zones)
        with self.assertRaises(energy.EnergyError):
            energy.select_packages(zones, [child])

    def test_duplicate_package_drivers_require_explicit_selection(self):
        duplicate = dict(self.zones[0], path=str(self.root / "intel-rapl-mmio:0"))
        with self.assertRaises(energy.EnergyError):
            energy.select_packages(self.zones + [duplicate], None)
        self.assertEqual(energy.select_packages(self.zones + [duplicate], [self.zone]), self.zones)

    def test_source_selection_cannot_silently_omit_another_socket(self):
        other_path = self.root / "intel-rapl:1"
        other = dict(self.zones[0], name="package-1", path=str(other_path))
        zones = self.zones + [other]
        with self.assertRaisesRegex(energy.EnergyError, "every available CPU package"):
            energy.select_packages(zones, [self.zone])
        self.assertEqual(energy.select_packages(zones, [self.zone, other_path]), zones)

    def test_complete_hashes_include_fence_completions(self):
        self.assertEqual(energy.validate_report(report(), 1, "regular", 1, 1, "avx2"), 12)

    def test_streaming_kernel_can_be_selected_and_validated(self):
        args = energy.parser().parse_args(["run", "--binary", "seine", "--threads", "1",
                                           "--kernel", "avx512-256-stream", "--output-dir", "new"])
        r = report()
        r["config_fingerprint"].update(cpu_kernel=args.kernel, cpu_kernel_requested=args.kernel)
        self.assertEqual(energy.validate_report(r, 1, "regular", 1, 1, args.kernel), 12)

    def test_sweep_pairs_are_adjacent_alternating_and_rotate_challengers(self):
        plan = energy.sweep_plan([4, 8, 12], 8, 3)
        self.assertEqual(len(plan), 12)
        self.assertEqual(len({leg["directory"] for leg in plan}), 12)
        for first, second in zip(plan[::2], plan[1::2]):
            self.assertEqual(first["candidate_threads"], second["candidate_threads"])
            self.assertEqual(first["pair"], second["pair"])
            self.assertEqual({first["role"], second["role"]}, {"baseline", "candidate"})
            self.assertEqual(first["role"], "candidate" if first["pair"] % 2 == 0 else "baseline")
        self.assertEqual([plan[i]["candidate_threads"] for i in (0, 4, 8)], [4, 12, 4])
        for counts, baseline, pairs in [([4], 4, 3), ([4, 4], 4, 3), ([0, 4], 4, 3),
                                        ([4, 8], 12, 3), ([4, 8], 4, 2)]:
            with self.assertRaises(energy.EnergyError):
                energy.sweep_plan(counts, baseline, pairs)

    def test_warmups_partial_backing_missing_telemetry_and_partial_reports_fail(self):
        edits = [lambda r: r.update(warmup_rounds=1),
                 lambda r: r["runs"][0]["backend_runs"][0].update(memory_regular_bytes=energy.GIB),
                 lambda r: r["runs"][0]["backend_runs"][0].pop("control_execution_timeouts"),
                 lambda r: r.update(rounds=2),
                 lambda r: r.update(total_hashes=10),
                 lambda r: r["config_fingerprint"].update(cpu_autotune_threads=True)]
        for edit in edits:
            r = copy.deepcopy(report())
            edit(r)
            with self.assertRaises((energy.EnergyError, KeyError)):
                energy.validate_report(r, 1, "regular", 1, 1, "avx2")

    def args(self, binary, name="result"):
        return argparse.Namespace(binary=binary, output_dir=self.root / name, threads=1,
                                  page_mode="regular", kernel="avx2", seconds=1, rounds=1,
                                  interval=.02, timeout=5, max_domain_watts=1000,
                                  label="test-fixture-not-hardware", zone=None)

    def context(self):
        return {"vmstat": {"pswpin": 0, "pswpout": 0, "oom_kill": 0},
                "boot_id": "test-boot",
                "frequency_policies": {}, "power_constraints": {}, "allowed_cpus": [0], "cpuinfo": "fixture"}

    def test_capture_uses_matching_invocation_energy_and_preserves_raw_samples(self):
        binary = self.root / "fake-miner"
        binary.write_text("#!/usr/bin/env python3\nimport sys,time,json\nfrom pathlib import Path\n"
                          f"counter=Path({str(self.zone / 'energy_uj')!r})\n"
                          "for i in range(1,11):\n time.sleep(.025)\n"
                          " tmp=counter.with_suffix('.tmp')\n tmp.write_text(str(i*1000000))\n tmp.replace(counter)\n"
                          f"Path(sys.argv[sys.argv.index('--bench-output')+1]).write_text({json.dumps(report())!r})\n")
        binary.chmod(0o755)
        with patch.object(energy, "check_capacity"), patch.object(energy, "cpu_context", side_effect=lambda _: self.context()):
            result = energy.run(self.args(binary), self.zones)
        self.assertEqual(result["status"], "complete")
        self.assertAlmostEqual(result["total_package_joules"], 10)
        self.assertAlmostEqual(result["invocation_joules_per_completed_hash"], 10 / 12)
        self.assertGreater(len(result["samples"]), 2)
        self.assertEqual(json.loads((self.root / "result/energy.json").read_text())["status"], "complete")

    def test_missing_counters_prevent_process_launch(self):
        with patch.object(energy.subprocess, "Popen") as start:
            with self.assertRaises(energy.EnergyError):
                energy.run(self.args(self.root / "absent"), [])
            start.assert_not_called()

    def test_timeout_stops_owned_process_and_records_failure(self):
        binary = self.root / "sleeping-miner"
        binary.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(60)\n")
        binary.chmod(0o755)
        args = self.args(binary)
        args.timeout = .08
        with patch.object(energy, "check_capacity"), patch.object(energy, "cpu_context", side_effect=lambda _: self.context()):
            with self.assertRaisesRegex(energy.EnergyError, "timeout"):
                energy.run(args, self.zones)
        result = json.loads((self.root / "result/energy.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("invocation_joules_per_completed_hash", result)

    def measurement(self, name, joules):
        folder = self.root / name
        folder.mkdir()
        (folder / "bench.json").write_text(json.dumps(report()))
        record = {"status": "complete", "scope": "whole_invocation_package_energy",
                  "binary_sha256": "fixture", "domains": self.zones,
                  "benchmark_sha256": energy.sha256(folder / "bench.json"),
                  "completed_hashes": 12, "samples": [self.sample(0, 0), self.sample(.5, int(joules * 1e6))],
                  "max_domain_watts_assumption": 1000, "invocation_secs": .5,
                  "total_package_joules": joules, "invocation_joules_per_completed_hash": joules / 12,
                  "invocation_completed_hashes_per_second": 24, "average_package_watts": joules * 2,
                  "context_before": self.context()}
        (folder / "energy.json").write_text(json.dumps(record))
        return folder

    def sweep_measurements(self):
        plan = energy.sweep_plan([1, 2, 3], 2, 3)
        # 2 workers peaks at 100 H/s; 1 retains 96% for less energy/hash;
        # 3 consumes more while achieving less throughput than 2.
        for leg in plan:
            workers = leg["threads"]
            hashes, joules = {1: (48, 20), 2: (50, 25), 3: (49, 30)}[workers]
            folder = self.measurement(leg["directory"], joules)
            r = report()
            r.update(cpu_threads=workers, total_hashes=hashes)
            r["runs"][0].update(hashes=hashes, counted_hashes=hashes - 2)
            r["runs"][0]["backend_runs"][0].update(hashes=hashes, memory_regular_workers=workers,
                                                   memory_regular_bytes=workers * 2 * energy.GIB)
            (folder / "bench.json").write_text(json.dumps(r))
            record = json.loads((folder / "energy.json").read_text())
            record.update(benchmark_sha256=energy.sha256(folder / "bench.json"), completed_hashes=hashes,
                          invocation_joules_per_completed_hash=joules / hashes,
                          invocation_completed_hashes_per_second=hashes / .5)
            (folder / "energy.json").write_text(json.dumps(record))
        return plan

    def test_sweep_shortlists_energy_with_a_throughput_floor_and_rejects_tampering(self):
        plan = self.sweep_measurements()
        result = energy.summarize_sweep(self.root, plan, .95)
        self.assertEqual(result["observed_peak_threads"], 2)
        self.assertEqual(result["efficiency_shortlist_threads"], 1)
        self.assertEqual([p["on_observed_frontier"] for p in result["points"]], [True, True, False])
        self.assertEqual([p["samples"] for p in result["points"]], [3, 6, 3])
        self.assertEqual(energy.summarize_sweep(self.root, plan, .99)["efficiency_shortlist_threads"], 2)
        path = self.root / plan[-1]["directory"] / "energy.json"
        record = json.loads(path.read_text())
        record["average_package_watts"] = 1
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(energy.EnergyError, "raw observations"):
            energy.summarize_sweep(self.root, plan, .95)

    def test_sweep_rejects_power_changes_even_when_each_pair_is_compatible(self):
        plan = self.sweep_measurements()
        for leg in plan:
            if leg["candidate_threads"] == 3:
                path = self.root / leg["directory"] / "energy.json"
                record = json.loads(path.read_text())
                record["context_before"]["power_constraints"] = {"changed": True}
                path.write_text(json.dumps(record))
        with self.assertRaisesRegex(energy.EnergyError, "changed across the sweep"):
            energy.summarize_sweep(self.root, plan, .95)

    def test_sweep_failure_and_budget_exhaustion_do_not_produce_a_ranking(self):
        args = energy.parser().parse_args(["sweep", "--binary", "/nonexistent", "--threads", "1", "2",
                                           "--baseline-threads", "1", "--settle-secs", "0",
                                           "--output-dir", str(self.root / "sweep")])
        with patch.object(energy, "check_capacity"), patch.object(energy, "run", side_effect=energy.EnergyError("fixture failure")):
            with self.assertRaisesRegex(energy.EnergyError, "fixture failure"):
                energy.sweep(args, self.zones)
        record = json.loads((args.output_dir / "sweep.json").read_text())
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["completed"], [])
        self.assertFalse((args.output_dir / "summary.json").exists())
        args.output_dir = self.root / "timed-out"
        args.max_seconds = .001
        with patch.object(energy, "check_capacity"), patch.object(energy, "run") as run:
            with self.assertRaisesRegex(energy.EnergyError, "time budget"):
                energy.sweep(args, self.zones)
            run.assert_not_called()
        self.assertFalse((args.output_dir / "summary.json").exists())

    def test_sweep_missing_counters_leaves_no_output_or_child(self):
        args = energy.parser().parse_args(["sweep", "--binary", "/nonexistent", "--threads", "1", "2",
                                           "--baseline-threads", "1", "--output-dir", str(self.root / "absent")])
        with patch.object(energy, "run") as run:
            with self.assertRaises(energy.EnergyError):
                energy.sweep(args, [])
            run.assert_not_called()
        self.assertFalse(args.output_dir.exists())

    def test_complete_sweep_launches_fixture_children_and_retains_evidence(self):
        binary = self.root / "fixture-miner"
        binary.write_text("#!/usr/bin/env python3\nimport sys,time,json\nfrom pathlib import Path\n"
                          f"counter=Path({str(self.zone / 'energy_uj')!r})\n"
                          "workers=int(sys.argv[sys.argv.index('--threads')+1])\n"
                          f"report=json.loads({json.dumps(report())!r})\n"
                          "report['cpu_threads']=workers\n"
                          "backend=report['runs'][0]['backend_runs'][0]\n"
                          "backend['memory_regular_workers']=workers\n"
                          f"backend['memory_regular_bytes']=workers*2*{energy.GIB}\n"
                          "start=int(counter.read_text())\n"
                          "for i in range(1,6):\n time.sleep(.025)\n"
                          " tmp=counter.with_suffix('.tmp')\n tmp.write_text(str(start+i*1000000))\n tmp.replace(counter)\n"
                          "Path(sys.argv[sys.argv.index('--bench-output')+1]).write_text(json.dumps(report))\n")
        binary.chmod(0o755)
        args = energy.parser().parse_args(["sweep", "--binary", str(binary), "--threads", "1", "2",
                                           "--baseline-threads", "1", "--settle-secs", "0",
                                           "--seconds", "1", "--rounds", "1", "--interval", ".02",
                                           "--kernel", "avx2", "--output-dir", str(self.root / "complete")])
        with patch.object(energy, "check_capacity"), patch.object(energy, "cpu_context", side_effect=lambda _: self.context()):
            result = energy.sweep(args, self.zones)
        manifest = json.loads((args.output_dir / "sweep.json").read_text())
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(len(manifest["completed"]), 6)
        self.assertEqual([point["samples"] for point in result["points"]], [3, 3])
        for directory in manifest["completed"]:
            record, _ = energy.load_measurement(args.output_dir / directory)
            self.assertAlmostEqual(record["total_package_joules"], 5)
        self.assertTrue((args.output_dir / "summary.json").exists())

    def test_paired_comparison_recomputes_metrics_and_checks_compatibility(self):
        baseline = [self.measurement(f"a{i}", 10) for i in range(3)]
        candidate = [self.measurement(f"b{i}", 8) for i in range(3)]
        compared = energy.compare(baseline, candidate)
        metric = compared["metrics"]["invocation_joules_per_completed_hash"]
        self.assertAlmostEqual(metric["comparison"]["paired_geometric_delta_pct"], -20)
        self.assertEqual(metric["comparison"]["sign_consistency"]["candidate_lower_pairs"], 3)
        altered = candidate[0] / "energy.json"
        record = json.loads(altered.read_text())
        record["invocation_joules_per_completed_hash"] *= .5
        altered.write_text(json.dumps(record))
        with self.assertRaisesRegex(energy.EnergyError, "raw observations"):
            energy.compare(baseline, candidate)

    def test_comparison_rejects_missing_pairs_reused_inputs_and_changed_report(self):
        baseline = [self.measurement(f"a{i}", 10) for i in range(3)]
        candidate = [self.measurement(f"b{i}", 8) for i in range(3)]
        for a, b in [(baseline[:2], candidate[:2]), (baseline, baseline)]:
            with self.assertRaises(energy.EnergyError):
                energy.compare(a, b)
        (candidate[0] / "bench.json").write_text("{}")
        with self.assertRaisesRegex(energy.EnergyError, "checksum"):
            energy.compare(baseline, candidate)

    def test_comparison_rejects_context_changes_between_matched_pairs(self):
        baseline = [self.measurement(f"a{i}", 10) for i in range(3)]
        candidate = [self.measurement(f"b{i}", 8) for i in range(3)]
        for folder in (baseline[1], candidate[1]):
            path = folder / "energy.json"
            record = json.loads(path.read_text())
            record["binary_sha256"] = "different-build-in-second-pair"
            path.write_text(json.dumps(record))
        with self.assertRaisesRegex(energy.EnergyError, "binary_sha256"):
            energy.compare(baseline, candidate)

    def test_comparison_allows_power_changes_but_requires_same_allowed_cpus(self):
        baseline = [self.measurement(f"a{i}", 10) for i in range(3)]
        candidate = [self.measurement(f"b{i}", 8) for i in range(3)]
        for folder in candidate:
            path = folder / "energy.json"
            record = json.loads(path.read_text())
            record["context_before"]["power_constraints"] = {"package-0": {"limit": "100"}}
            path.write_text(json.dumps(record))
        energy.compare(baseline, candidate)
        for folder in candidate:
            path = folder / "energy.json"
            record = json.loads(path.read_text())
            record["context_before"]["allowed_cpus"] = [1]
            path.write_text(json.dumps(record))
        with self.assertRaisesRegex(energy.EnergyError, "allowed_cpus"):
            energy.compare(baseline, candidate)

    def test_sigterm_cleans_up_the_benchmark_process(self):
        self.assert_sigterm_cleanup("run")

    def test_sweep_sigterm_cleans_up_child_and_records_partial_campaign(self):
        self.assert_sigterm_cleanup("sweep")

    def assert_sigterm_cleanup(self, action):
        pidfile = self.root / "child.pid"
        binary = self.root / "sleeping-miner"
        binary.write_text("#!/usr/bin/env python3\nimport os,time\nfrom pathlib import Path\n"
                          f"Path({str(pidfile)!r}).write_text(str(os.getpid()))\ntime.sleep(60)\n")
        binary.chmod(0o755)
        driver = self.root / "driver.py"
        driver.write_text(f"import sys\nsys.path.insert(0,{str(Path(energy.__file__).parent)!r})\n"
                          "import bench_cpu_energy as e\ne.check_capacity=lambda *a: None\nsys.exit(e.main())\n")
        command = [sys.executable, "-B", str(driver), "--counter-root", str(self.root), action,
                   "--binary", str(binary), "--threads", "1", "--interval", ".02",
                   "--output-dir", str(self.root / "signal-result")]
        if action == "sweep":
            command.extend(["--threads", "1", "2", "--baseline-threads", "1", "--settle-secs", "0"])
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        child_pid = None
        try:
            deadline = time.monotonic() + 3
            while not pidfile.exists() and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(pidfile.exists(), "fixture child did not start")
            child_pid = int(pidfile.read_text())
            proc.terminate()
            proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 130)
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            if action == "sweep":
                result = json.loads((self.root / "signal-result/sweep.json").read_text())
                self.assertEqual(result["status"], "failed")
                self.assertFalse((self.root / "signal-result/summary.json").exists())
                record_path = self.root / "signal-result" / result["plan"][0]["directory"] / "energy.json"
            else:
                record_path = self.root / "signal-result/energy.json"
            result = json.loads(record_path.read_text())
            self.assertEqual(result["status"], "failed")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)
            if child_pid:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()
