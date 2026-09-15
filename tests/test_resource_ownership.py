"""DF-3: claims pertencem ao par DeviceHandle + DriverHandle."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "kernel/src/device/resource_manager.sotlas").read_text(encoding="utf-8")
REGISTRY = (ROOT / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")


class ResourceOwnershipTests(unittest.TestCase):
    def test_claim_requires_live_driver_and_active_owned_device(self):
        claim = SOURCE.split("pub fn resource_claim", 1)[1].split(
            "pub fn resource_snapshot", 1)[0]
        self.assertIn("!driver.valid", claim)
        self.assertIn("device_core_acquire_resource(device, driver)", claim)
        acquire = REGISTRY.split("pub fn device_core_acquire_resource", 1)[1].split(
            "pub fn device_core_release_resource", 1)[0]
        self.assertIn("DEVICE_STATE_BINDING", acquire)
        self.assertIn("DEVICE_STATE_ACTIVE", acquire)
        self.assertIn("driver_handle_equal(DEVICE_RECORDS[slot].driver, driver)", acquire)

    def test_release_requires_exact_generation_safe_owners(self):
        release = SOURCE.split("pub fn resource_release", 1)[1].split(
            "pub fn resource_release_all", 1)[0]
        self.assertIn("device_handle_equal", release)
        self.assertIn("driver_handle_equal", release)
        self.assertIn("device_core_release_resource(device, driver)", release)

    def test_unbind_and_detach_require_zero_resources(self):
        detach = REGISTRY.split("pub fn device_core_detach", 1)[1]
        self.assertIn("resource_count == 0", detach)
        self.assertIn("!DEVICE_RECORDS[slot].driver.valid", detach)

    def test_unbind_closes_claim_window_before_remove_callback(self):
        drivers = (ROOT / "kernel/src/device/driver_registry.sotlas").read_text(encoding="utf-8")
        unbind = drivers.split("pub fn driver_unbind", 1)[1]
        self.assertLess(unbind.index("device_core_prepare_unbind"),
                        unbind.index("descriptor.remove(device)"))
        self.assertLess(unbind.index("descriptor.remove(device)"),
                        unbind.index("device_core_finish_unbind"))
        self.assertIn("DEVICE_STATE_UNBINDING", REGISTRY)


if __name__ == "__main__":
    unittest.main()
