"""Contrato do primeiro driver migrado para ownership da plataforma."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "kernel/src/platform/storage_binding.sotlas"


class PlatformStorageBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_bind_requires_real_controller_and_block_device(self):
        self.assertIn("storage_generic_block_io_is_ready()", self.source)
        self.assertIn("block_device_has_native_target()", self.source)
        self.assertIn("storage_discovery_candidate()", self.source)

    def test_ahci_and_nvme_have_distinct_driver_owners(self):
        self.assertIn("PLATFORM_DRIVER_AHCI", self.source)
        self.assertIn("PLATFORM_DRIVER_NVME", self.source)
        self.assertIn("(*candidate).pci_index", self.source)

    def test_claim_precedes_active_transition(self):
        body = self.source.split("pub fn platform_storage_bind_active_driver", 1)[1]
        self.assertLess(body.index("platform_device_claim"), body.index("platform_device_set_state"))
        self.assertIn("PLATFORM_DEVICE_STATE_ACTIVE", body)

    def test_native_block_device_is_authoritative_and_catalog_is_advisory(self):
        body = self.source.split("pub fn platform_storage_bind_active_driver", 1)[1]
        self.assertIn("block_device_index() != index", body)
        self.assertIn("block_device_kind() != expected_block_kind", body)
        self.assertIn("PLATFORM_STORAGE_CATALOG_LINKED = catalog_linked", body)
        self.assertIn("PLATFORM_STORAGE_BIND_CATALOG_UNLINKED", self.source)

    def test_serial_marker_cannot_invalidate_a_bound_driver(self):
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        body = runtime.split("if platform_storage_binding_required()", 1)[1]
        bind_gate, after_gate = body.split("platform_storage_emit_bound_marker();", 1)
        self.assertIn("if !platform_storage_bind_active_driver()", bind_gate)
        self.assertNotIn("|| !platform_storage_emit_bound_marker()", bind_gate)
        self.assertTrue(after_gate)

    def test_storage_failure_replaces_stale_aml_detail(self):
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        body = runtime.split("hda_discover_pci();", 1)[1].split("i2c_compatibility_diagnostics_init();", 1)[0]
        self.assertIn("baken_early_boot_clear_failure_details();", body)
        self.assertIn("platform_storage_bind_status()", body)
        self.assertIn("platform_storage_device_index()", body)

    def test_boot_requires_real_storage_binding(self):
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(body.index("platform_device_catalog_init()"), body.index("platform_storage_bind_active_driver()"))
        self.assertLess(body.index("platform_storage_bind_active_driver()"), body.index("smp_initialize_base()"))
        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("STORAGE_DRIVER_BOUND", REQUIRED)


if __name__ == "__main__":
    unittest.main()
