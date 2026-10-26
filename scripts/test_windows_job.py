"""Native Windows lifecycle tests; these launch only short Python fixtures."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == "nt", "native Windows required")
class JobTests(unittest.TestCase):
    def setUp(self):
        import _winapi
        from windows_job import WindowsJobProcess
        self.api = _winapi
        self.launch = WindowsJobProcess

    def fixture(self, directory, parent_exits):
        marker = Path(directory) / "pid.txt"
        child = "import os,time;from pathlib import Path;Path(" + repr(str(marker)) + ").write_text(str(os.getpid()));time.sleep(30)"
        parent = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);time.sleep(" + ("0.5" if parent_exits else "30") + ")"
        return marker, [sys.executable, "-c", parent]

    def child_handle(self, marker):
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(marker.exists(), "child never started")
        return self.api.OpenProcess(0x100000 | 0x1000, False, int(marker.read_text()))

    def test_terminate_stops_launcher_and_child(self):
        with tempfile.TemporaryDirectory() as directory, open(os.devnull, "w") as output:
            marker, command = self.fixture(directory, False)
            process = self.launch(command, output)
            child = None
            try:
                child = self.child_handle(marker)
                with self.assertRaises(subprocess.TimeoutExpired):
                    process.wait(timeout=0.01)
                process.terminate()
                self.assertNotEqual(process.wait(timeout=5), 0)
                self.assertEqual(self.api.WaitForSingleObject(child, 5000), self.api.WAIT_OBJECT_0)
            finally:
                process.close()
                if child is not None:
                    self.api.CloseHandle(child)

    def test_close_stops_child_after_launcher_exits(self):
        with tempfile.TemporaryDirectory() as directory, open(os.devnull, "w") as output:
            marker, command = self.fixture(directory, True)
            process = self.launch(command, output)
            child = None
            try:
                child = self.child_handle(marker)
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertEqual(self.api.WaitForSingleObject(child, 0), self.api.WAIT_TIMEOUT)
                process.close()
                self.assertEqual(self.api.WaitForSingleObject(child, 5000), self.api.WAIT_OBJECT_0)
                process.close()  # Idempotent failure/cleanup paths.
            finally:
                process.close()
                if child is not None:
                    self.api.CloseHandle(child)

    def test_failed_launch_does_not_leave_job_handle(self):
        with open(os.devnull, "w") as output:
            with self.assertRaises(FileNotFoundError):
                self.launch([r"C:\nonexistent-seine-fixture\missing.exe"], output)


if __name__ == "__main__":
    unittest.main()
