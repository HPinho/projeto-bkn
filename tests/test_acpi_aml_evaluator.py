"""Contratos AML-6a para o evaluator controlado e sem efeitos de hardware."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EVALUATOR = ROOT / "kernel/src/acpi/aml_evaluator.sotlas"
PLATFORM = ROOT / "kernel/src/platform/inventory.sotlas"
SMP_WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class AcpiAmlEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = EVALUATOR.read_text(encoding="utf-8")
        cls.platform = PLATFORM.read_text(encoding="utf-8")
        cls.smp_workflow = SMP_WORKFLOW.read_text(encoding="utf-8")

    def test_execution_context_has_fixed_limits_and_no_heap_or_hardware(self):
        for token in (
            "AML_EVAL_MAX_ARGS: usize = 7",
            "AML_EVAL_MAX_LOCALS: usize = 8",
            "AML_EVAL_MAX_DEPTH: usize = 8",
            "AML_EVAL_DEFAULT_FUEL: usize = 4096",
            "args: [AmlEvalValue; AML_EVAL_MAX_ARGS]",
            "locals: [AmlEvalValue; AML_EVAL_MAX_LOCALS]",
            "aml_eval_consume_fuel",
        ):
            self.assertIn(token, self.source)
        lower = self.source.lower()
        for forbidden in (
            "malloc(", "free(", "kmalloc", "heap_alloc", "bootservices",
            "systemtable", "mmio_write", "pci_write", "__out",
            "aml_operation_region", "fieldop(", "sleep(", "stall(", "notify(",
        ):
            self.assertNotIn(forbidden, lower)

    def test_arg_local_opcode_ranges_are_exact(self):
        expected = {
            "AML_LOCAL0_OP": "0x60", "AML_LOCAL7_OP": "0x67",
            "AML_ARG0_OP": "0x68", "AML_ARG6_OP": "0x6E",
        }
        for name, value in expected.items():
            self.assertIn(f"pub const {name}: u8 = {value}", self.source)
        self.assertIn("opcode >= AML_LOCAL0_OP && opcode <= AML_LOCAL7_OP", self.source)
        self.assertIn("opcode >= AML_ARG0_OP && opcode <= AML_ARG6_OP", self.source)

    def test_store_targets_are_frame_only(self):
        body = self.source.split("fn aml_eval_write_target", 1)[1].split(
            "fn aml_eval_integer_required", 1
        )[0]
        self.assertIn("AML_NULL_NAME", body)
        self.assertIn("(*frame).locals", body)
        self.assertIn("(*frame).args", body)
        self.assertIn("AML_EVAL_ERROR_TARGET", body)
        self.assertNotIn("aml_namespace_loader_define", body)

    def test_integer_arithmetic_logic_and_control_subset_is_explicit(self):
        expected = (
            ("AML_STORE_OP", "0x70"), ("AML_ADD_OP", "0x72"),
            ("AML_SUBTRACT_OP", "0x74"), ("AML_MULTIPLY_OP", "0x77"),
            ("AML_SHIFT_LEFT_OP", "0x79"), ("AML_SHIFT_RIGHT_OP", "0x7A"),
            ("AML_AND_OP", "0x7B"), ("AML_OR_OP", "0x7D"),
            ("AML_XOR_OP", "0x7F"), ("AML_NOT_OP", "0x80"),
            ("AML_LAND_OP", "0x90"), ("AML_LOR_OP", "0x91"),
            ("AML_LNOT_OP", "0x92"), ("AML_LEQUAL_OP", "0x93"),
            ("AML_LGREATER_OP", "0x94"), ("AML_LLESS_OP", "0x95"),
            ("AML_IF_EVAL_OP", "0xA0"), ("AML_ELSE_EVAL_OP", "0xA1"),
            ("AML_RETURN_OP", "0xA4"),
        )
        for name, value in expected:
            self.assertIn(f"pub const {name}: u8 = {value}", self.source)

    def test_control_flow_is_pkg_length_bounded_and_return_terminates_body(self):
        term_list = self.source.split("fn aml_eval_term_list", 1)[1].split(
            "fn aml_eval_execute_body", 1
        )[0]
        self.assertIn("aml_decode_pkg_length(cursor)", term_list)
        self.assertIn("aml_cursor_take(cursor, package.body_bytes)", term_list)
        self.assertIn("aml_cursor_take(cursor, else_package.body_bytes)", term_list)
        self.assertIn("(*frame).returned", term_list)
        execute = self.source.split("fn aml_eval_execute_body", 1)[1].split(
            "pub fn aml_evaluator_execute_method", 1
        )[0]
        self.assertIn("if !aml_eval_term_list", execute)
        self.assertIn("if (*frame).returned { return true; }", execute)
        self.assertIn("aml_cursor_remaining(&cursor) == 0", execute)

    def test_method_invocation_validates_arity_flags_and_kind(self):
        execute = self.source.split("pub fn aml_evaluator_execute_method", 1)[1].split(
            "pub fn aml_evaluator_is_ready", 1
        )[0]
        self.assertIn("AML_NAMESPACE_KIND_METHOD", execute)
        self.assertIn("let declared_args = (flags & 0x07) as usize", execute)
        self.assertIn("declared_args != argument_count", execute)
        self.assertIn("(flags & 0xF8) != 0", execute)
        self.assertIn("AML_EVAL_ERROR_FLAGS", execute)

    def test_nested_methods_and_global_writes_are_fail_closed(self):
        namespace = self.source.split("fn aml_eval_from_namespace", 1)[1].split(
            "fn aml_eval_read_slot", 1
        )[0]
        self.assertIn("AML_NAMESPACE_KIND_METHOD", namespace)
        self.assertIn("AML_EVAL_ERROR_METHOD", namespace)
        self.assertNotIn("aml_evaluator_execute_method(", namespace)
        self.assertNotIn("aml_namespace_loader_define_leaf", self.source)

    def test_self_tests_cover_arithmetic_branch_and_fuel_failure(self):
        self_test = self.source.split("pub fn aml_evaluator_self_test", 1)[1].split(
            "pub fn aml_evaluator_emit_failure_markers", 1
        )[0]
        for token in (
            "Store(0x2A, Local0)", "frame.return_value.integer_value != 0x2B",
            "If (LEqual(Arg0, One))", "frame.return_value.integer_value != 0xAA",
            "frame.return_value.integer_value != 0x55", "fuel = 1",
            "aml_namespace_is_ready()", "aml_loader_is_ready()",
        ):
            self.assertIn(token, self_test)

    def test_platform_and_all_runtime_validators_require_unambiguous_evaluator_proof(self):
        self.assertIn("import kernel::acpi::aml_evaluator::*;", self.platform)
        init = self.platform.split("pub fn platform_inventory_init", 1)[1].split(
            "pub fn platform_inventory", 1
        )[0]
        self.assertIn("aml_evaluator_self_test()", init)
        self.assertIn("platform_emit_aml_evaluator_failure_marker()", init)
        self.assertIn("aml_evaluator_emit_failure_markers()", init)
        marker = self.platform.split("pub fn platform_inventory_emit_ready_marker", 1)[1]
        self.assertIn("aml_evaluator_emit_ready_marker()", marker)
        self.assertLess(marker.index("aml_evaluator_emit_ready_marker()"),
                        marker.index("let marker: [u8; 21]"))

        from tools.scripts.verify_kernel_smoke import REQUIRED, validate
        from tools.scripts.run_smp_qemu import REQUIRED_MARKERS, validate as validate_smp

        self.assertIn("ACPI_AML_EVALUATOR_READY", REQUIRED)
        self.assertIn("BAKEN:ACPI_AML_EVALUATOR_READY", REQUIRED_MARKERS)
        self.assertIn("python3 tests/test_acpi_aml_evaluator.py", self.smp_workflow)
        self.assertIn("BAKEN:ACPI_AML_EVALUATOR_FAILED", self.smp_workflow)
        self.assertIn(
            "require_marker 'BAKEN:ACPI_AML_EVALUATOR_READY'",
            self.smp_workflow,
        )

        shared_diagnostics = "BAKEN:HEX=T:00000001\nBAKEN:HEX=U:00000013\n"
        self.assertFalse(any("AML evaluator failed" in error
                             for error in validate(shared_diagnostics)))
        self.assertFalse(any("AML evaluator failed" in error
                             for error in validate_smp(shared_diagnostics)))

        explicit_failure = (
            "BAKEN:ACPI_AML_EVALUATOR_FAILED\n"
            "BAKEN:HEX=T:03000000\n"
            "BAKEN:HEX=U:00000004\n"
        )
        self.assertTrue(any("AML evaluator failed" in error
                            for error in validate(explicit_failure)))
        self.assertTrue(any("AML evaluator failed" in error
                            for error in validate_smp(explicit_failure)))

    def test_marker_and_diagnostic_channels_are_explicit_and_collision_safe(self):
        self.assertIn("BAKEN:ACPI_AML_EVALUATOR_READY", self.source)
        marker = self.source.split("pub fn aml_evaluator_emit_ready_marker", 1)[1]
        self.assertIn("let marker: [u8; 31]", marker)
        self.assertIn("x86_serial_write_byte(marker[index])", marker)
        self.assertIn("'T' as u8", self.source)
        self.assertIn("'U' as u8", self.source)

        self.assertIn("BAKEN:ACPI_AML_EVALUATOR_FAILED", self.platform)
        failure_marker = self.platform.split(
            "fn platform_emit_aml_evaluator_failure_marker", 1
        )[1].split("pub fn platform_inventory_init", 1)[0]
        self.assertIn("let marker: [u8; 32]", failure_marker)
        self.assertIn("x86_serial_write_byte(marker[index])", failure_marker)


if __name__ == "__main__":
    unittest.main()
