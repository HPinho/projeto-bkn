"""DF-2: serialização SMP sem confundir IF=0 com falha."""
import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "kernel/src/device/driver_registry.sotlas").read_text(encoding="utf-8")


class DriverSmpSafetyTests(unittest.TestCase):
    def test_lock_reports_success_separately_from_saved_rflags(self):
        self.assertIn("fn driver_lock_irq(saved_flags: *mut u64) -> bool", SOURCE)
        self.assertIn("*saved_flags = flags", SOURCE)
        self.assertNotIn("if flags == 0", SOURCE)

    def test_callbacks_are_pinned_by_inflight_count(self):
        bind = SOURCE.split("pub fn driver_bind", 1)[1].split("pub fn driver_unbind", 1)[0]
        callback = bind.index("let probe_ok = selected_record.descriptor.probe(device)")
        self.assertLess(bind.index("operations_in_flight += 1"), callback)
        self.assertGreater(bind.rindex("operations_in_flight -= 1"), callback)
        unbind = SOURCE.split("pub fn driver_unbind", 1)[1]
        callback = unbind.index("let remove_ok = selected_record.descriptor.remove(device)")
        self.assertLess(unbind.index("operations_in_flight += 1"), callback)
        self.assertGreater(unbind.index("operations_in_flight -= 1"), callback)


if __name__ == "__main__":
    unittest.main()
