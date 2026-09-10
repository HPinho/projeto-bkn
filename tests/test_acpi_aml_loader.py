"""Contratos AML-4 para loader real DSDT/SSDT -> namespace."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LOADER = ROOT / "kernel/src/acpi/aml_loader.sotlas"
NAMESPACE = ROOT / "kernel/src/acpi/aml_namespace.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class AcpiAmlLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = LOADER.read_text(encoding="utf-8")
        cls.namespace = NAMESPACE.read_text(encoding="utf-8")

    def test_loader_is_bounded_and_uses_catalogued_definition_blocks(self):
        for token in (
            "AML_LOADER_MAX_DEPTH: usize = 16",
            "AML_LOADER_MAX_TERMS: usize = 32768",
            "aml_definition_block_payload(table)",
            "aml_definition_block_payload_length(table)",
            "aml_loader_consume_budget(budget)",
            "depth >= AML_LOADER_MAX_DEPTH",
        ):
            self.assertIn(token, self.source)
        lower = self.source.lower()
        for forbidden in ("heap_alloc", "kmalloc", "malloc(", "free("):
            self.assertNotIn(forbidden, lower)

    def test_definition_blocks_are_loaded_dsdt_then_all_ssdts(self):
        init = self.source.split("pub fn aml_loader_init", 1)[1].split(
            "pub fn aml_loader_emit_failure_markers", 1
        )[0]
        self.assertIn("aml_loader_load_definition_block(aml_dsdt(), 0, &mut budget)", init)
        self.assertIn("let ssdt_count = aml_ssdt_count()", init)
        self.assertIn("while index < ssdt_count", init)
        self.assertIn("aml_loader_load_definition_block(aml_ssdt(index), index + 1, &mut budget)", init)
        self.assertIn("AML_LOADER_TABLES_LOADED != ssdt_count + 1", init)

    def test_namespace_declarations_are_grammar_aware(self):
        body = self.source.split("fn aml_loader_parse_term_list", 1)[1].split(
            "fn aml_loader_load_definition_block", 1
        )[0]
        for token in (
            "opcode == AML_NAME_OP",
            "aml_decode_data_object(cursor)",
            "opcode == AML_SCOPE_OP",
            "opcode == AML_METHOD_OP",
            "ext == AML_EXT_DEVICE_OP",
            "ext == AML_EXT_PROCESSOR_OP",
            "ext == AML_EXT_POWER_RESOURCE_OP",
            "ext == AML_EXT_THERMAL_ZONE_OP",
            "aml_namespace_loader_define_leaf",
            "aml_namespace_loader_open_scope",
            "aml_loader_parse_term_list(&mut body, child_scope, depth + 1",
        ):
            self.assertIn(token, body)

    def test_method_bodies_and_control_flow_are_not_executed(self):
        body = self.source.split("fn aml_loader_parse_term_list", 1)[1].split(
            "fn aml_loader_load_definition_block", 1
        )[0]
        self.assertIn("let method_body = aml_loader_pointer_at(&body, body.offset)", body)
        self.assertIn("AML_NAMESPACE_KIND_METHOD", body)
        self.assertIn("opcode == AML_IF_OP || opcode == AML_ELSE_OP || opcode == AML_WHILE_OP", body)
        self.assertIn("let opaque = aml_cursor_take(cursor, package.body_bytes)", body)
        lower = self.source.lower()
        for forbidden in (
            "evaluate_method", "execute_opcode", "operation_region_write",
            "mmio_write", "pci_write", "__out", "io_write",
        ):
            self.assertNotIn(forbidden, lower)

    def test_known_structural_objects_have_bounded_skip_rules(self):
        for token in (
            "AML_EXT_OPERATION_REGION_OP",
            "AML_EXT_FIELD_OP",
            "AML_EXT_INDEX_FIELD_OP",
            "AML_EXT_BANK_FIELD_OP",
            "AML_EXT_DATA_REGION_OP",
            "AML_EXT_CREATE_FIELD_OP",
            "AML_CREATE_DWORD_FIELD_OP",
            "aml_loader_skip_static_term_arg",
            "aml_loader_skip_remaining",
            "aml_decode_pkg_length(cursor)",
        ):
            self.assertIn(token, self.source)

    def test_unknown_opcode_fails_closed_with_diagnostics(self):
        body = self.source.split("fn aml_loader_parse_term_list", 1)[1].split(
            "fn aml_loader_load_definition_block", 1
        )[0]
        self.assertIn("AML_LOADER_ERROR_OPCODE", body)
        self.assertNotIn("offset += 1", body)
        diagnostics = self.source.split("pub fn aml_loader_emit_failure_markers", 1)[1].split(
            "pub fn aml_loader_emit_ready_marker", 1
        )[0]
        self.assertIn("x86_serial_write_hex32_marker('A' as u8", diagnostics)
        self.assertIn("x86_serial_write_hex32_marker('B' as u8", diagnostics)

    def test_namespace_builder_window_is_explicit_and_closes_on_finish(self):
        for token in (
            "AML_NAMESPACE_MAX_NODES: usize = 1024",
            "static mut AML_NAMESPACE_LOADING: bool = false",
            "pub fn aml_namespace_loader_begin",
            "pub fn aml_namespace_loader_abort",
            "pub fn aml_namespace_loader_define_leaf",
            "pub fn aml_namespace_loader_open_scope",
            "pub fn aml_namespace_loader_finish",
            "if !AML_NAMESPACE_LOADING || AML_NAMESPACE_READY",
            "AML_NAMESPACE_LOADING = false",
            "AML_NAMESPACE_READY = true",
        ):
            self.assertIn(token, self.namespace)
        self.assertIn("AML_NAMESPACE_FLAG_IMPLICIT_SCOPE", self.namespace)
        self.assertNotIn("pub fn aml_namespace_define_path", self.namespace)

    def test_runtime_loads_namespace_before_platform_and_all_gates_require_marker(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::aml_loader::*;", runtime)
        run = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(run.index("aml_namespace_emit_ready_marker()"), run.index("aml_loader_init()"))
        self.assertLess(run.index("aml_loader_emit_ready_marker()"), run.index("platform_inventory_init()"))
        self.assertIn("aml_loader_emit_failure_markers()", run)

        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("ACPI_AML_NAMESPACE_LOADED", REQUIRED)
        from tools.scripts.run_smp_qemu import REQUIRED_MARKERS
        self.assertIn("BAKEN:ACPI_AML_NAMESPACE_LOADED", REQUIRED_MARKERS)

        nvme = (ROOT / ".github/workflows/baken_nvme_only.yml").read_text(encoding="utf-8")
        smp = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        self.assertIn("'BAKEN:ACPI_AML_NAMESPACE_LOADED'", nvme)
        self.assertIn("python3 tests/test_acpi_aml_loader.py", smp)
        self.assertIn("require_marker 'BAKEN:ACPI_AML_NAMESPACE_LOADED'", smp)


if __name__ == "__main__":
    unittest.main()
