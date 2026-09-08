"""Contratos de ownership e ciclo de vida do catálogo de dispositivos."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/platform/device_catalog.sotlas"


class PlatformDeviceCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_catalog_copies_pci_identity_and_resources(self):
        for token in ("vendor_id", "device_id", "class_code", "subclass", "prog_if",
                      "bar0_base", "bar0_size", "bar5_base", "bar5_size"):
            self.assertIn(token, self.source)
        self.assertIn("pub fn platform_device_snapshot", self.source)
        self.assertNotIn("pub fn platform_device(index: u32) -> *const", self.source)

    def test_catalog_has_explicit_lifecycle(self):
        for state in ("STATE_EMPTY", "STATE_DISCOVERED", "STATE_CLAIMED",
                      "STATE_ACTIVE", "STATE_FAILED"):
            self.assertIn(state, self.source)
        self.assertIn("owner_driver", self.source)

    def test_claim_is_exclusive_and_state_change_checks_owner(self):
        claim = self.source.split("pub fn platform_device_claim", 1)[1].split(
            "pub fn platform_device_set_state", 1)[0]
        self.assertIn("state == PLATFORM_DEVICE_STATE_DISCOVERED", claim)
        change = self.source.split("pub fn platform_device_set_state", 1)[1].split(
            "pub fn platform_device_catalog_emit_ready_marker", 1)[0]
        self.assertIn("owner_driver == driver", change)
        self.assertIn("state == PLATFORM_DEVICE_STATE_CLAIMED", change)

    def test_mutations_are_irq_safe_and_smp_serialized(self):
        lock = self.source.split("fn platform_device_lock_irq", 1)[1].split(
            "fn platform_device_unlock_irq", 1)[0]
        self.assertLess(lock.index("x86_irq_save_disable()"), lock.index("spinlock_lock"))
        self.assertIn("platform_device_lock_irq()", self.source)
        self.assertIn("platform_device_unlock_irq(flags)", self.source)

    def test_catalog_is_boot_gated_after_inventory(self):
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(body.index("platform_inventory_init()"), body.index("platform_device_catalog_init()"))
        self.assertLess(body.index("platform_device_catalog_init()"), body.index("smp_initialize_base()"))
        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("DEVICE_CATALOG_READY", REQUIRED)


if __name__ == "__main__":
    unittest.main()
