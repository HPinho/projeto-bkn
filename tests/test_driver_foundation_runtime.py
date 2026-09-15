"""DF-3.1: lifecycle transacional provado no runtime sem tocar hardware."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = (ROOT / "kernel/src/device/types.sotlas").read_text(encoding="utf-8")
DEVICES = (ROOT / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")
DRIVERS = (ROOT / "kernel/src/device/driver_registry.sotlas").read_text(encoding="utf-8")
RESOURCES = (ROOT / "kernel/src/device/resource_manager.sotlas").read_text(encoding="utf-8")
SELF_TEST = (ROOT / "kernel/src/device/foundation_self_test.sotlas").read_text(encoding="utf-8")
SMOKE = (ROOT / "tools/scripts/verify_kernel_smoke.py").read_text(encoding="utf-8")
SMP_WORKFLOW = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
NVME_WORKFLOW = (ROOT / ".github/workflows/baken_nvme_only.yml").read_text(encoding="utf-8")


class DriverFoundationRuntimeTests(unittest.TestCase):
    def test_binding_allows_probe_resources_before_active(self):
        self.assertIn("DEVICE_STATE_BINDING", TYPES)
        acquire = DEVICES.split("pub fn device_core_acquire_resource", 1)[1].split(
            "pub fn device_core_release_resource", 1)[0]
        self.assertIn("DEVICE_STATE_BINDING", acquire)
        bind = DRIVERS.split("pub fn driver_bind", 1)[1].split("pub fn driver_unbind", 1)[0]
        self.assertLess(bind.index("device_core_begin_bind"), bind.index("descriptor.probe(device)"))
        self.assertLess(bind.index("descriptor.probe(device)"), bind.index("device_core_commit_bind"))

    def test_unbinding_allows_drain_then_requires_zero(self):
        prepare = DEVICES.split("pub fn device_core_prepare_unbind", 1)[1].split(
            "pub fn device_core_finish_unbind", 1)[0]
        self.assertNotIn("resource_count == 0", prepare)
        finish = DEVICES.split("pub fn device_core_finish_unbind", 1)[1].split(
            "pub fn device_core_acquire_resource", 1)[0]
        self.assertIn("remove_ok && DEVICE_RECORDS[slot].resource_count == 0", finish)
        claim = DEVICES.split("pub fn device_core_acquire_resource", 1)[1].split(
            "pub fn device_core_release_resource", 1)[0]
        self.assertNotIn("DEVICE_STATE_UNBINDING", claim)

    def test_partial_remove_never_returns_to_active(self):
        finish = DEVICES.split("pub fn device_core_finish_unbind", 1)[1].split(
            "pub fn device_core_acquire_resource", 1)[0]
        self.assertIn("resource_epoch == initial_epoch", finish)
        self.assertIn("DEVICE_STATE_FAILED", finish)

    def test_device_stores_full_generation_safe_driver_handle(self):
        record = TYPES.split("pub struct DeviceRecord", 1)[1].split("pub struct ResourceClaim", 1)[0]
        self.assertIn("pub driver: DriverHandle", record)
        self.assertNotIn("pub driver_id", record)
        self.assertIn("driver_handle_equal(DEVICE_RECORDS[slot].driver, driver)", DEVICES)

    def test_pci_bar_is_logical_ownership_not_mmio_range(self):
        self.assertIn("PCI_BAR identifica ownership logico", RESOURCES)
        validation = RESOURCES.split("fn resource_request_valid", 1)[1].split(
            "fn resource_ranges_overlap", 1)[0]
        self.assertIn("request.length == 1 && request.auxiliary < 6", validation)

    def test_runtime_exercises_full_success_lifecycle_and_is_a_gate(self):
        for token in ("device_core_attach", "driver_register", "driver_bind",
                      "resource_count != 2", "driver_unbind", "device_core_detach",
                      "second.generation == first.generation",
                      "BAKEN:DRIVER_FOUNDATION_READY"):
            self.assertIn(token, SELF_TEST)
        self.assertIn('"DRIVER_FOUNDATION_READY"', SMOKE)
        self.assertIn("require_marker 'BAKEN:DRIVER_FOUNDATION_READY'", SMP_WORKFLOW)
        self.assertIn("'BAKEN:DRIVER_FOUNDATION_READY'", NVME_WORKFLOW)


if __name__ == "__main__":
    unittest.main()
