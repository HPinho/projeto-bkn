"""Keep the fast local SMP runner aligned with the GitHub gate."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.scripts.run_smp_qemu import FINAL_MARKER, REQUIRED_MARKERS, validate


class LocalSmpRunnerTests(unittest.TestCase):
    def test_direct_execution_without_pythonpath(self):
        # Exercise the CI entry point in a fresh interpreter. Discovery in the
        # repository root can hide a missing import path in a standalone test.
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()),
                 "LocalSmpRunnerTests.test_validator_fails_closed"],
                cwd=directory, env=environment, capture_output=True, text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Ran 1 test", result.stderr)

    def test_runner_uses_same_machine_shape_as_workflow(self):
        source = (ROOT / "tools/scripts/run_smp_qemu.py").read_text(encoding="utf-8")
        for token in ('"q35"', '"-smp", "2"', '"512M"', '"qemu-xhci,id=xhci"'):
            self.assertIn(token, source)

    def test_every_local_marker_is_required_by_workflow(self):
        workflow = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        for marker in REQUIRED_MARKERS:
            self.assertIn(marker, workflow)

    def test_validator_fails_closed(self):
        self.assertTrue(validate(FINAL_MARKER + "\n"))
        complete = "\n".join(REQUIRED_MARKERS) + "\n"
        self.assertEqual(validate(complete), [])
        self.assertIn("CPU exception", validate(complete + "BAKEN:HEX=E:0000000E\n")[0])

    def test_runner_defaults_to_three_independent_boots(self):
        source = (ROOT / "tools/scripts/run_smp_qemu.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--runs", type=int, default=3)', source)

    def test_probe_failure_rejected_even_when_all_success_markers_exist(self):
        complete = "\n".join(REQUIRED_MARKERS) + "\n"
        for stage in (2, 3, 4, 5, 6, 9, 10):
            failure = f"BAKEN:HEX=Q:{0x80000000 | stage:08X}\n"
            for log in (failure + complete, complete + failure):
                self.assertTrue(any("Ring3/TLB probe failed" in e for e in validate(log)))
        self.assertEqual(validate(complete + "BAKEN:HEX=Q:00000004\n"), [])


if __name__ == "__main__":
    unittest.main()
