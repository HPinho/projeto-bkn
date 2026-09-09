"""Contratos do catálogo seguro de definition blocks AML."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "kernel/src/acpi/tables.sotlas"
FADT = ROOT / "kernel/src/acpi/fadt.sotlas"
AML = ROOT / "kernel/src/acpi/aml_tables.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class AcpiAmlTableTests(unittest.TestCase):
    def test_fadt_prefers_validated_x_dsdt_and_falls_back_to_legacy(self):
        text = FADT.read_text(encoding="utf-8")
        body = text.split("pub fn fadt_dsdt_table", 1)[1].split(
            "pub fn fadt_pm_timer_init", 1
        )[0]
        extended = body.index("fadt_read_u64(table, FADT_X_DSDT_OFFSET)")
        legacy = body.index("fadt_read_u32(table, FADT_DSDT_OFFSET)")
        self.assertLess(extended, legacy)
        self.assertIn("acpi_validated_table_from_physical(extended, ACPI_SIG_DSDT)", body)
        self.assertIn("acpi_validated_table_from_physical(legacy, ACPI_SIG_DSDT)", body)

    def test_catalog_requires_dsdt_and_bounds_all_ssdts(self):
        text = AML.read_text(encoding="utf-8")
        body = text.split("pub fn aml_tables_init", 1)[1].split(
            "pub fn aml_tables_is_ready", 1
        )[0]
        for token in (
            "!acpi_uses_post_cutover_direct_map()",
            "let dsdt = fadt_dsdt_table()",
            "let count = acpi_table_count(ACPI_SIG_SSDT)",
            "if count > AML_MAX_SSDT_COUNT",
            "acpi_find_table_at(ACPI_SIG_SSDT, index)",
            "__dma_fence()",
            "AML_TABLES_READY = true",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("__dma_fence()"), body.index("AML_TABLES_READY = true"))

    def test_interpreter_boundary_exposes_only_validated_payload_ranges(self):
        text = AML.read_text(encoding="utf-8")
        self.assertIn("pub fn aml_dsdt() -> *const u8", text)
        self.assertIn("pub fn aml_ssdt(index: usize) -> *const u8", text)
        self.assertIn("pub fn aml_definition_block_payload(table: *const u8)", text)
        self.assertIn("pub fn aml_definition_block_payload_length(table: *const u8)", text)
        self.assertIn("fn aml_definition_block_catalogued(table: *const u8)", text)
        self.assertIn("if !aml_definition_block_catalogued(table)", text)
        self.assertIn("acpi_table_length(table)", text)
        self.assertIn("length - ACPI_SDT_HEADER_LENGTH", text)

    def test_runtime_and_all_qemu_gates_require_aml_catalog(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(body.index("aml_tables_init()"), body.index("platform_inventory_init()"))
        self.assertIn("aml_tables_emit_ready_marker()", body)
        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("ACPI_AML_TABLES_READY", REQUIRED)
        nvme = (ROOT / ".github/workflows/baken_nvme_only.yml").read_text(encoding="utf-8")
        smp = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        self.assertIn("'BAKEN:ACPI_AML_TABLES_READY'", nvme)
        self.assertIn("require_marker 'BAKEN:ACPI_AML_TABLES_READY'", smp)

    def test_catalog_never_executes_aml_or_writes_hardware(self):
        text = AML.read_text(encoding="utf-8").lower()
        for forbidden in ("__out", "mmio_write", "pci_write", "evaluate_method", "execute_opcode"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
