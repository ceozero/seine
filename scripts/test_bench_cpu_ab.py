#!/usr/bin/env python3
"""Exercise the CPU A/B shell workflow without allocating mining arenas."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("bash"), "requires Bash")
class CpuBenchmarkTimingTests(unittest.TestCase):
    def run_pair(self, baseline_schema, candidate_schema, kind):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            binaries = []
            for name, schema in [("baseline", baseline_schema), ("candidate", candidate_schema)]:
                binary = directory / name
                binary.write_text(
                    "#!/usr/bin/env python3\n"
                    "import json, sys\n"
                    "from pathlib import Path\n"
                    "args=sys.argv[1:]\n"
                    "path=Path(args[args.index('--bench-output')+1])\n"
                    "kind=args[args.index('--bench-kind')+1].replace('-', '_')\n"
                    f"report=dict(schema_version={schema}, bench_kind=kind, avg_hps=10, "
                    "median_hps=10, total_counted_hashes=10, total_late_hashes=0)\n"
                    "path.write_text(json.dumps(report))\n"
                )
                binary.chmod(0o700)
                binaries.append(binary)
            output = directory / "results"
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/bench_cpu_ab.sh"),
                 "--baseline-dir", str(ROOT), "--candidate-dir", str(ROOT),
                 "--baseline-binary", str(binaries[0]), "--candidate-binary", str(binaries[1]),
                 "--bench-kind", kind, "--pairs", "1", "--bench-secs", "1",
                 "--bench-rounds", "1", "--bench-warmup-rounds", "0",
                 "--cooldown-secs", "0", "--output-dir", str(output)],
                capture_output=True, text=True, timeout=30,
            )
            return result, (output / "summary.txt").exists()

    def test_new_kernel_reports_can_be_compared(self):
        result, summarized = self.run_pair(15, 15, "kernel")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(summarized)

    def test_legacy_or_mixed_kernel_reports_never_produce_a_gain_summary(self):
        for baseline, candidate in [(14, 14), (14, 15), (15, 14)]:
            with self.subTest(baseline=baseline, candidate=candidate):
                result, summarized = self.run_pair(baseline, candidate, "kernel")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("CPU kernel A/B requires schema-15", result.stderr)
                self.assertFalse(summarized)

    def test_legacy_lifecycle_reports_remain_comparable(self):
        result, summarized = self.run_pair(14, 15, "kernel-effective")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(summarized)


if __name__ == "__main__":
    unittest.main()
