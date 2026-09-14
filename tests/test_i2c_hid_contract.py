from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_hid_acpi.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"


class I2cHidContractTests(unittest.TestCase):
    """Contratos de runtime, limites de memória e integridade de boot para I2C-HID-0."""

    def test_zero_dynamic_heap_allocation(self):
        text = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("kernel_heap", text)
        self.assertNotIn("alloc(", text)
        self.assertNotIn("malloc(", text)

    def test_bounded_storage_capacity(self):
        text = MODULE.read_text(encoding="utf-8")
        self.assertIn("pub const I2C_HID_MAX_DEVICES: usize = 4;", text)
        self.assertIn("I2C_HID_DEVICES: [I2cHidAcpiDescriptor; I2C_HID_MAX_DEVICES]", text)

    def test_canonical_boot_route_invokes_hid_acpi_scan(self):
        rt_text = RUNTIME.read_text(encoding="utf-8")
        # Deve ser chamado após controladores físicos e ACPI
        self.assertIn("i2c_discovery_scan_acpi_controllers();", rt_text)
        self.assertIn("i2c_physical_probe_pci();", rt_text)
        self.assertIn("i2c_hid_acpi_scan_devices();", rt_text)

        acpi_idx = rt_text.index("i2c_discovery_scan_acpi_controllers();")
        pci_idx = rt_text.index("i2c_physical_probe_pci();")
        hid_idx = rt_text.index("i2c_hid_acpi_scan_devices();")
        self.assertLess(acpi_idx, pci_idx)
        self.assertLess(pci_idx, hid_idx)

    def test_qemu_boot_smoke_gate_invariants_preserved(self):
        smoke_text = SMOKE.read_text(encoding="utf-8")
        self.assertIn("REQUIRED = (", smoke_text)
        self.assertIn("BARE_METAL_READY", smoke_text)
        self.assertIn("USER_FAULT_ISOLATED_READY", smoke_text)
        # O scan de I2C HID não deve ter panics nem loops infinitos
        mod_text = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("panic(", mod_text)
        self.assertNotIn("loop {", mod_text)


if __name__ == "__main__":
    unittest.main()
