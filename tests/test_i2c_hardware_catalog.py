import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "kernel/src/drivers/i2c_hardware_catalog.sotlas"
DISCOVERY = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"
DESIGNWARE = ROOT / "kernel/src/drivers/i2c_designware.sotlas"
FIXTURES = ROOT / "tests/fixtures/acpi/i2c"


class I2cHardwareCatalogContract(unittest.TestCase):
    def test_catalog_is_versioned_and_controller_driven(self):
        text = CATALOG.read_text(encoding="utf-8")
        self.assertIn("I2C_CATALOG_SCHEMA_VERSION", text)
        self.assertIn("i2c_catalog_pci(vendor: u16, device: u16)", text)
        self.assertNotIn("cpuid", text.lower())

    def test_designware_revision_is_checked_before_init(self):
        discovery = DISCOVERY.read_text(encoding="utf-8")
        dw = DESIGNWARE.read_text(encoding="utf-8")
        self.assertIn("DW_IC_COMP_VERSION", dw)
        self.assertIn("DW_IC_COMP_TYPE", dw)
        check = discovery.index("i2c_catalog_component_allowed")
        init = discovery.index("i2c_dw_init_with_clock", check)
        self.assertLess(check, init)

    def test_psp_owned_bus_is_fail_closed(self):
        text = CATALOG.read_text(encoding="utf-8")
        self.assertIn("I2C_CATALOG_ACCESS_PSP_SEMAPHORE", text)
        self.assertIn("I2C_CATALOG_REASON_PSP_ARBITRATION", text)
        fixture = json.loads((FIXTURES / "amd_amdi0019_psp.json").read_text())
        self.assertTrue(fixture["requires_psp_arbitration"])
        self.assertEqual("reject-before-mmio", fixture["expected_policy"])

    def test_fixtures_do_not_pretend_to_be_physical_captures(self):
        for path in FIXTURES.glob("*.json"):
            fixture = json.loads(path.read_text())
            self.assertEqual(1, fixture["schema"])
            self.assertFalse(fixture["captured_from_hardware"])
            self.assertEqual("synthetic-contract-fixture", fixture["provenance"])

    def test_runtime_probes_pci_and_acpi_platforms(self):
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text()
        self.assertIn("i2c_physical_probe_pci();", runtime)
        self.assertIn("i2c_physical_probe_acpi_platform();", runtime)


if __name__ == "__main__":
    unittest.main()
