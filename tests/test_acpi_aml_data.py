"""Contratos AML-3 para DataObject e skip grammar-aware fail-closed."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "kernel/src/acpi/aml_data.sotlas"
NAMESPACE = ROOT / "kernel/src/acpi/aml_namespace.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class AcpiAmlDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DATA.read_text(encoding="utf-8")

    def test_data_object_subset_is_explicit_and_bounded(self):
        for token in (
            "AML_STRING_PREFIX: u8 = 0x0D",
            "AML_BUFFER_OP: u8 = 0x11",
            "AML_PACKAGE_OP: u8 = 0x12",
            "AML_VAR_PACKAGE_OP: u8 = 0x13",
            "AML_DATA_MAX_DEPTH: usize = 8",
            "AML_DATA_MAX_OBJECTS: usize = 1024",
            "AML_DATA_MAX_PACKAGE_ELEMENTS: usize = 255",
            "AML_DATA_MAX_STRING_BYTES: usize = 4096",
        ):
            self.assertIn(token, self.source)

    def test_parser_is_pkg_length_bounded_and_never_scans_unknown_bytes(self):
        body = self.source.split("fn aml_decode_value_internal", 1)[1].split(
            "pub fn aml_decode_term_arg_constant", 1
        )[0]
        self.assertIn("aml_decode_pkg_length(cursor)", body)
        self.assertIn("aml_cursor_take(cursor, package.body_bytes)", body)
        self.assertIn("aml_cursor_remaining(&body) != 0", body)
        self.assertIn("aml_data_fail(cursor)", body)
        self.assertNotIn("offset += 1", body)

    def test_nested_packages_have_depth_and_global_object_budget(self):
        body = self.source.split("fn aml_decode_value_internal", 1)[1].split(
            "pub fn aml_decode_term_arg_constant", 1
        )[0]
        self.assertIn("depth >= AML_DATA_MAX_DEPTH", body)
        self.assertIn("aml_data_consume_budget(cursor, budget)", body)
        self.assertIn(
            "aml_decode_value_internal(&mut body, depth + 1, budget, true)",
            body,
        )
        budget = self.source.split("fn aml_data_consume_budget", 1)[1].split(
            "fn aml_data_is_integer_opcode", 1
        )[0]
        self.assertIn("if (*budget) == 0", budget)
        self.assertIn("(*budget) -= 1", budget)

    def test_term_arg_subset_is_constant_only(self):
        body = self.source.split("fn aml_decode_term_arg_constant_internal", 1)[1].split(
            "fn aml_decode_value_internal", 1
        )[0]
        self.assertIn("return aml_decode_integer(cursor)", body)
        for forbidden in ("evaluate_method", "execute_opcode", "operation_region"):
            self.assertNotIn(forbidden, body.lower())

    def test_package_elements_accept_known_data_or_namestring_only(self):
        body = self.source.split("fn aml_decode_value_internal", 1)[1].split(
            "pub fn aml_decode_term_arg_constant", 1
        )[0]
        self.assertIn("allow_name && aml_data_is_name_start(opcode)", body)
        self.assertIn("aml_decode_name_string(cursor)", body)
        self.assertIn("name.segment_count == 0", body)
        for token in (
            "AML_BUFFER_OP", "AML_PACKAGE_OP", "AML_VAR_PACKAGE_OP",
            "AML_STRING_PREFIX", "aml_data_is_integer_opcode(opcode)",
        ):
            self.assertIn(token, body)

    def test_runtime_self_test_covers_data_objects_and_fail_closed_cases(self):
        body = self.source.split("pub fn aml_data_self_test", 1)[1].split(
            "pub fn aml_data_emit_ready_marker", 1
        )[0]
        for token in (
            "let string_bytes: [u8; 5]",
            "let buffer_bytes: [u8; 7]",
            "let package_bytes: [u8; 8]",
            "let var_package_bytes: [u8; 6]",
            "let nested_bytes: [u8; 7]",
            "aml_skip_package_element(&mut name_element_cursor)",
            "let truncated_string: [u8; 2]",
            "let unsupported_bytes: [u8; 1] = [0x5B]",
            "AML_DATA_READY = true",
        ):
            self.assertIn(token, body)
        marker = self.source.split("pub fn aml_data_emit_ready_marker", 1)[1]
        self.assertIn("if !aml_data_is_ready()", marker)
        self.assertIn("x86_serial_write_buffer", marker)

    def test_data_layer_does_not_execute_aml_or_touch_platform_hardware(self):
        lower = self.source.lower()
        for forbidden in (
            "evaluate_method", "execute_opcode", "operation_region",
            "mmio_write", "pci_write", "__out", "io_write",
            "heap_alloc", "kmalloc", "malloc(", "free(",
        ):
            self.assertNotIn(forbidden, lower)

    def test_namespace_chains_data_foundation_fail_closed(self):
        namespace = NAMESPACE.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::aml_data::*;", namespace)
        init = namespace.split("pub fn aml_namespace_foundation_init", 1)[1].split(
            "pub fn aml_namespace_emit_ready_marker", 1
        )[0]
        self.assertIn("if !aml_data_self_test() { return false; }", init)
        marker = namespace.split("pub fn aml_namespace_emit_ready_marker", 1)[1]
        self.assertIn("if !aml_data_emit_ready_marker() { return false; }", marker)

    def test_all_qemu_gates_require_data_marker(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("aml_namespace_foundation_init()", runtime)
        self.assertIn("aml_namespace_emit_ready_marker()", runtime)

        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("ACPI_AML_DATA_READY", REQUIRED)
        from tools.scripts.run_smp_qemu import REQUIRED_MARKERS
        self.assertIn("BAKEN:ACPI_AML_DATA_READY", REQUIRED_MARKERS)

        nvme = (ROOT / ".github/workflows/baken_nvme_only.yml").read_text(encoding="utf-8")
        smp = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        self.assertIn("verify_kernel_smoke.py", nvme)
        self.assertIn("run_smp_qemu.py --validate-log", smp)


if __name__ == "__main__":
    unittest.main()
