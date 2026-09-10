from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ROOT / "kernel/src/acpi/aml_regions.sotlas"
INVENTORY = ROOT / "kernel/src/platform/inventory.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"


class AmlRegionsTests(unittest.TestCase):
    def test_region_core_is_bounded_and_uses_native_backends(self):
        text = REGIONS.read_text(encoding="utf-8")
        for token in (
            "AML_REGION_SYSTEM_MEMORY",
            "AML_REGION_SYSTEM_IO",
            "AML_REGION_PCI_CONFIG",
            "AML_REGION_MAX_LENGTH",
            "aml_region_bounds_valid",
            "active_page_tables_map_mmio_identity_4k",
            "x86_mmio_read32",
            "x86_mmio_write32",
            "__inl",
            "__outl",
            "pci_read_config32",
            "pci_write_config32",
        ):
            self.assertIn(token, text)
        for forbidden in ("kernel_heap", "malloc", "calloc", "realloc"):
            self.assertNotIn(forbidden, text)

    def test_field_geometry_is_single_dword_and_fail_closed(self):
        text = REGIONS.read_text(encoding="utf-8")
        for token in (
            "AML_FIELD_MAX_BITS: u32 = 32",
            "shift + bit_length as u64 > 32",
            "aml_field_geometry_valid",
            "aml_field_read_integer",
            "aml_field_write_integer",
            "if (value & ~mask) != 0",
        ):
            self.assertIn(token, text)

    def test_index_and_bank_are_not_silently_emulated(self):
        text = REGIONS.read_text(encoding="utf-8")
        self.assertIn("AML_FIELD_KIND_INDEX", text)
        self.assertIn("AML_FIELD_KIND_BANK", text)
        self.assertIn("(*field).kind != AML_FIELD_KIND_REGION", text)

    def test_init_does_not_touch_hardware(self):
        text = REGIONS.read_text(encoding="utf-8")
        body = text.split("pub fn aml_regions_init()", 1)[1]
        body = body.split("pub fn aml_regions_emit_ready_marker", 1)[0]
        for forbidden in (
            "aml_region_read32(",
            "aml_region_write32(",
            "__inl(",
            "__outl(",
            "pci_write_config32(",
            "x86_mmio_write32(",
        ):
            self.assertNotIn(forbidden, body)

    def test_platform_barrier_and_smoke_require_region_marker(self):
        inventory = INVENTORY.read_text(encoding="utf-8")
        smoke = SMOKE.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::aml_regions::*;", inventory)
        self.assertIn("aml_regions_init()", inventory)
        self.assertIn("aml_regions_emit_ready_marker()", inventory)
        self.assertIn("ACPI_AML_REGIONS_READY", smoke)
        self.assertIn("ACPI_AML_REGIONS_FAILED", smoke)


if __name__ == "__main__":
    unittest.main()
