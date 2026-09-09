import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.scripts.verify_kernel_smoke import REQUIRED, validate


class KernelSmokeGateTests(unittest.TestCase):
    def good_log(self):
        return "\r\n".join(f"BAKEN:{marker}" for marker in REQUIRED)

    def test_complete_execution(self):
        self.assertEqual(validate(self.good_log()), [])

    def test_each_milestone_required(self):
        for marker in REQUIRED:
            with self.subTest(marker=marker):
                self.assertTrue(validate(self.good_log().replace(f"BAKEN:{marker}", "")))

    def test_exception_before_or_after_success_fails(self):
        for log in ("BAKEN:HEX=E:0000000D\n" + self.good_log(),
                    self.good_log() + "\nBAKEN:HEX=E:0000000E"):
            self.assertTrue(validate(log))

    def test_prefix_is_not_a_milestone(self):
        self.assertTrue(validate(self.good_log().replace(
            "BAKEN:SCHEDULER_ROUND_TRIP", "BAKEN:SCHEDULER_ROUND_TRIP_FAILED")))

    def test_empty_log_fails(self):
        self.assertTrue(validate(""))

    def test_both_workflows_use_shared_gate_before_disk_verification(self):
        root = Path(__file__).resolve().parents[1]
        for workflow, log in (("baken_ci.yml", "qemu-serial.log"),
                              ("baken_nvme_only.yml", "qemu-nvme-only-serial.log")):
            with self.subTest(workflow=workflow):
                source = (root / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
                gate = f"python3 tools/scripts/verify_kernel_smoke.py build/{log}"
                self.assertIn(gate, source)
                self.assertLess(source.index(gate), source.index("--verify build/"))
                self.assertIn("timeout-minutes: 20", source)

    def test_all_qemu_workflows_retry_transient_apt_downloads(self):
        root = Path(__file__).resolve().parents[1]
        for workflow in ("baken_ci.yml", "baken_nvme_only.yml", "baken_smp.yml"):
            with self.subTest(workflow=workflow):
                source = (root / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
                self.assertIn("apt_retry()", source)
                self.assertIn("Acquire::Retries=5", source)
                self.assertIn("apt_retry update", source)
                self.assertIn("apt_retry install -y qemu-system-x86", source)
                self.assertIn('test "$attempt" -ge 3', source)
                self.assertIn("timeout-minutes: 20", source)
                self.assertIn("actions/checkout@v6", source)
                self.assertIn("actions/setup-python@v6", source)
                self.assertIn("actions/upload-artifact@v6", source)
