import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "kernel/src/drivers/i2c_compatibility_diagnostics.sotlas"
DISCOVERY = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class I2cCompatibilityDiagnosticsContract(unittest.TestCase):
    def test_report_is_bounded_and_versioned(self):
        text = DIAG.read_text(encoding="utf-8")
        self.assertIn("I2C_DIAGNOSTIC_SCHEMA_VERSION", text)
        self.assertIn("I2C_DIAGNOSTIC_CAPACITY: usize = 32", text)
        self.assertNotIn("alloc", text.lower())

    def test_report_contains_identity_reason_and_controller_revision(self):
        text = DIAG.read_text(encoding="utf-8")
        for field in ("vendor_id", "device_id", "namespace_index", "family", "reason", "component_version"):
            self.assertIn("pub " + field + ":", text)
        self.assertIn("BAKEN:I2C=", text)
        self.assertIn("BAKEN:I2C_DIAG_READY", text)

    def test_unknown_controller_and_psp_paths_are_reported(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("pci_profile.reason", text)
        self.assertIn("I2C_CATALOG_REASON_BAD_COMPONENT", text)
        self.assertIn("profile.family != I2C_CATALOG_FAMILY_NONE && !profile.valid", text)

    def test_runtime_initializes_before_probe_and_emits_after_probe(self):
        text = RUNTIME.read_text(encoding="utf-8")
        init = text.index("i2c_compatibility_diagnostics_init();")
        pci = text.index("i2c_physical_probe_pci();")
        acpi = text.index("i2c_physical_probe_acpi_platform();")
        emit = text.index("i2c_compatibility_emit_serial_report();")
        self.assertLess(init, pci)
        self.assertLess(pci, acpi)
        self.assertLess(acpi, emit)


if __name__ == "__main__":
    unittest.main()
