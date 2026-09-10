"""Tests AML-6b: resolução dinâmica bounded e read-only para discovery."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DYNAMIC = ROOT / "kernel/src/acpi/aml_dynamic_discovery.sotlas"
PLATFORM = ROOT / "kernel/src/platform/inventory.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
SMP_RUNNER = ROOT / "tools/scripts/run_smp_qemu.py"
SMP_WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class AcpiAmlDynamicDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DYNAMIC.read_text(encoding="utf-8")
        cls.platform = PLATFORM.read_text(encoding="utf-8")
        cls.smoke = SMOKE.read_text(encoding="utf-8")
        cls.smp_runner = SMP_RUNNER.read_text(encoding="utf-8")
        cls.smp_workflow = SMP_WORKFLOW.read_text(encoding="utf-8")

    def test_overlay_is_fixed_capacity_read_only_and_hardware_free(self):
        for token in (
            "AML_DYNAMIC_MAX_DEVICES: usize = 512",
            "AML_DYNAMIC_MAX_COMPAT_IDS: usize = 1024",
            "AML_DYNAMIC_MAX_COMPAT_IDS_PER_DEVICE: usize = 32",
            "AML_DYNAMIC_MAX_RESOURCE_DESCRIPTORS: usize = 4096",
            "import kernel::acpi::aml_discovery::*;",
            "import kernel::acpi::aml_evaluator::*;",
            "static mut AML_DYNAMIC_DEVICES:",
            "static mut AML_DYNAMIC_COMPAT_IDS:",
        ):
            self.assertIn(token, self.source)

        lower = self.source.lower()
        for forbidden in (
            "malloc(", "free(", "kmalloc", "heap_alloc", "bootservices",
            "systemtable", "mmio_write", "pci_write", "__out",
            "aml_operation_region", "fieldop(", "notify(", "sleep(", "stall(",
        ):
            self.assertNotIn(forbidden, lower)

    def test_only_predefined_discovery_methods_are_targeted(self):
        expected = {
            "AML_DYNAMIC_NAME_HID": "0x4449485F",
            "AML_DYNAMIC_NAME_CID": "0x4449435F",
            "AML_DYNAMIC_NAME_UID": "0x4449555F",
            "AML_DYNAMIC_NAME_STA": "0x4154535F",
            "AML_DYNAMIC_NAME_CRS": "0x5352435F",
        }
        for name, value in expected.items():
            self.assertIn(f"pub const {name}: u32 = {value}", self.source)
        for flag in (
            "hid_requires_evaluator", "cid_requires_evaluator",
            "uid_requires_evaluator", "status_requires_evaluator",
            "crs_requires_evaluator",
        ):
            self.assertIn(flag, self.source)

    def test_method_gate_is_zero_arg_nonserialized_and_uses_certified_evaluator(self):
        body = self.source.split("fn aml_dynamic_execute_zero_arg", 1)[1].split(
            "fn aml_dynamic_new_result", 1
        )[0]
        self.assertIn("AML_NAMESPACE_KIND_METHOD", body)
        self.assertIn("((*node).flags & 0x07) != 0", body)
        self.assertIn("((*node).flags & 0xF8) != 0", body)
        self.assertIn(
            "method_index, null as *const AmlEvalValue, 0, result", body
        )
        self.assertIn("aml_evaluator_execute_method(", body)

    def test_return_types_are_validated_per_predefined_object(self):
        self.assertIn("aml_dynamic_hid_string_valid", self.source)
        self.assertIn("aml_dynamic_eisa_id_valid", self.source)
        self.assertIn("aml_dynamic_parse_cid_value", self.source)
        self.assertIn("aml_dynamic_string_printable", self.source)
        self.assertIn("result.integer_value <= AML_DYNAMIC_STA_VALID_MASK as u64", self.source)
        self.assertIn("(result.integer_value & 0x03) != 0x02", self.source)
        self.assertIn("result.kind == AML_EVAL_VALUE_BUFFER", self.source)

    def test_crs_requires_exact_materialized_buffer_and_bounded_endtag(self):
        body = self.source.split("if (*source).crs_requires_evaluator", 1)[1].split(
            "AML_DYNAMIC_DEVICES[device_slot].valid", 1
        )[0]
        self.assertIn("result.integer_value == result.data_length as u64", body)
        self.assertIn("aml_dynamic_resource_template_valid", body)
        parser = self.source.split("fn aml_dynamic_resource_template_valid", 1)[1].split(
            "fn aml_dynamic_execute_zero_arg", 1
        )[0]
        self.assertIn("AML_DYNAMIC_MAX_RESOURCE_DESCRIPTORS", parser)
        self.assertIn("AML_DYNAMIC_RESOURCE_END_TAG_NAME", parser)
        self.assertIn("AML_DYNAMIC_RESOURCE_END_TAG_LENGTH", parser)
        self.assertIn("(sum & 0xFF) != 0", parser)

    def test_cid_package_is_bounded_exact_and_rolls_back_partial_results(self):
        body = self.source.split("fn aml_dynamic_parse_cid_value", 1)[1].split(
            "fn aml_dynamic_resource_template_valid", 1
        )[0]
        self.assertIn("AML_DYNAMIC_MAX_COMPAT_IDS_PER_DEVICE", body)
        self.assertIn("count != value.element_count", body)
        self.assertIn("first + count > AML_DYNAMIC_MAX_COMPAT_IDS", body)
        self.assertIn("AML_DYNAMIC_COMPAT_ID_COUNT = first", body)
        self.assertIn("aml_cursor_remaining(&cursor) != 0", body)

    def test_unsupported_firmware_method_is_left_unresolved_not_fabricated(self):
        resolve = self.source.split("fn aml_dynamic_resolve_device", 1)[1].split(
            "pub fn aml_dynamic_discovery_init", 1
        )[0]
        self.assertIn("let mut resolved = false;", resolve)
        self.assertIn("aml_dynamic_record_attempt(device_slot, resolved);", resolve)
        self.assertNotIn("return aml_dynamic_fail", resolve)

    def test_platform_publication_order_is_evaluator_dynamic_platform(self):
        init = self.platform.split("pub fn platform_inventory_init", 1)[1].split(
            "pub fn platform_inventory", 1
        )[0]
        self.assertIn("aml_evaluator_self_test()", init)
        self.assertIn("aml_dynamic_discovery_init()", init)
        self.assertIn("aml_dynamic_discovery_emit_failure_marker()", init)
        self.assertLess(
            init.index("aml_evaluator_self_test()"),
            init.index("aml_dynamic_discovery_init()"),
        )

        marker = self.platform.split("pub fn platform_inventory_emit_ready_marker", 1)[1]
        self.assertIn("aml_evaluator_emit_ready_marker()", marker)
        self.assertIn("aml_dynamic_discovery_emit_ready_marker()", marker)
        self.assertLess(
            marker.index("aml_evaluator_emit_ready_marker()"),
            marker.index("aml_dynamic_discovery_emit_ready_marker()"),
        )
        self.assertLess(
            marker.index("aml_dynamic_discovery_emit_ready_marker()"),
            marker.index("let marker: [u8; 21]"),
        )

    def test_all_runtime_gates_require_dynamic_ready_and_reject_explicit_failure(self):
        from tools.scripts.verify_kernel_smoke import REQUIRED, validate
        from tools.scripts.run_smp_qemu import REQUIRED_MARKERS, validate as validate_smp

        self.assertIn("ACPI_AML_DYNAMIC_READY", REQUIRED)
        self.assertIn("BAKEN:ACPI_AML_DYNAMIC_READY", REQUIRED_MARKERS)
        self.assertIn("python3 tests/test_acpi_aml_dynamic_discovery.py", self.smp_workflow)
        self.assertIn("BAKEN:ACPI_AML_DYNAMIC_FAILED", self.smp_workflow)
        self.assertIn(
            "require_marker 'BAKEN:ACPI_AML_DYNAMIC_READY'", self.smp_workflow
        )

        explicit = "BAKEN:ACPI_AML_DYNAMIC_FAILED\n"
        self.assertTrue(any("AML dynamic discovery failed" in e for e in validate(explicit)))
        self.assertTrue(any("AML dynamic discovery failed" in e for e in validate_smp(explicit)))

    def test_markers_are_explicit(self):
        self.assertIn("BAKEN:ACPI_AML_DYNAMIC_READY", self.source)
        self.assertIn("let marker: [u8; 29]", self.source)
        self.assertIn("BAKEN:ACPI_AML_DYNAMIC_FAILED", self.source)
        self.assertIn("let marker: [u8; 30]", self.source)


if __name__ == "__main__":
    unittest.main()
