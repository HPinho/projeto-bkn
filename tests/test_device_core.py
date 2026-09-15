"""DF-1: registro global entra no grafo sem comandar o boot ou hardware."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = (ROOT / "kernel/src/device/types.sotlas").read_text(encoding="utf-8")
REGISTRY = (ROOT / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class DeviceCoreTests(unittest.TestCase):
    def test_universal_bus_and_class_taxonomy(self):
        for name in ("PCI", "USB", "I2C", "ACPI", "VIRTUAL"):
            self.assertIn(f"DEVICE_BUS_{name}", TYPES)
        for name in ("BLOCK", "INPUT", "DISPLAY", "AUDIO", "NETWORK"):
            self.assertIn(f"DEVICE_CLASS_{name}", TYPES)

    def test_fixed_capacity_and_no_hardware_side_effects(self):
        self.assertIn("DEVICE_CORE_CAPACITY: usize = 128", TYPES)
        self.assertIn("[DeviceRecord; DEVICE_CORE_CAPACITY]", REGISTRY)
        for forbidden in ("pci_enable_command_bits", "active_page_tables_map_mmio",
                          "dma_alloc", "lapic_send", "__outb"):
            self.assertNotIn(forbidden, REGISTRY)

    def test_reachable_from_kernel_graph_without_boot_call(self):
        for module in ("types", "registry", "lifecycle"):
            self.assertIn(f"import kernel::device::{module}::*;", MAIN)
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("device_core_init()", runtime)


if __name__ == "__main__":
    unittest.main()
