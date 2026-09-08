"""Contratos da primeira camada platform independente de UEFI."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "kernel/src/platform/inventory.sotlas"


class PlatformInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PLATFORM.read_text(encoding="utf-8")

    def test_inventory_copies_architecture_and_device_facts(self):
        for token in ("cpu_count", "ioapic_count", "pci_device_count", "pci_segment_count",
                      "has_hpet", "has_display", "has_storage", "has_xhci"):
            self.assertIn(token, self.source)

    def test_platform_requires_post_cutover_native_sources(self):
        for token in ("acpi_uses_post_cutover_direct_map()", "madt_is_ready()",
                      "lapic_is_ready()", "ioapic_is_ready()", "pci_get_device_count()"):
            self.assertIn(token, self.source)
        lower = self.source.lower()
        self.assertNotIn("bootservices", lower)
        self.assertNotIn("systemtable", lower)

    def test_runtime_initializes_platform_before_smp(self):
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(body.index("platform_inventory_init()"), body.index("smp_initialize_base()"))
        self.assertIn("platform_inventory_emit_ready_marker()", body)

    def test_smoke_gate_requires_platform_marker(self):
        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("PLATFORM_READY", REQUIRED)


if __name__ == "__main__":
    unittest.main()
