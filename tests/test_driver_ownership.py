"""DF-2: ownership exclusivo e rollback de probe."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVERS = (ROOT / "kernel/src/device/driver_registry.sotlas").read_text(encoding="utf-8")
DEVICES = (ROOT / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")


class DriverOwnershipTests(unittest.TestCase):
    def test_device_claim_is_atomic_and_exclusive(self):
        body = DEVICES.split("pub fn device_core_claim_driver", 1)[1].split("pub fn device_core_release_driver", 1)[0]
        self.assertIn("DEVICE_RECORDS[slot].driver_id == DRIVER_ID_NONE", body)
        self.assertIn("DEVICE_RECORDS[slot].state == DEVICE_STATE_ATTACHED", body)
        self.assertIn("DEVICE_RECORDS[slot].driver_id = driver_id", body)

    def test_failed_probe_releases_claim(self):
        body = DRIVERS.split("pub fn driver_bind", 1)[1].split("pub fn driver_unbind", 1)[0]
        self.assertIn("if !active { device_core_release_driver(device, selected.driver_id); }", body)
        self.assertIn("if !active { return driver_invalid_handle(); }", body)

    def test_remove_precedes_active_owner_release(self):
        body = DRIVERS.split("pub fn driver_unbind", 1)[1]
        self.assertLess(body.index("let remove_ok = selected_record.descriptor.remove(device)"),
                        body.index("device_core_unbind_active_driver"))
        release = DEVICES.split("pub fn device_core_unbind_active_driver", 1)[1].split("pub fn device_core_detach", 1)[0]
        self.assertIn("DEVICE_RECORDS[slot].driver_id = DRIVER_ID_NONE", release)
        self.assertIn("DEVICE_RECORDS[slot].state = DEVICE_STATE_ATTACHED", release)

    def test_registered_driver_cannot_disappear_while_busy_or_bound(self):
        body = DRIVERS.split("pub fn driver_unregister", 1)[1].split("pub fn driver_bind", 1)[0]
        self.assertIn("bound_count == 0", body)
        self.assertIn("operations_in_flight == 0", body)


if __name__ == "__main__":
    unittest.main()
