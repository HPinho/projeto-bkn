"""Contratos AML-5 para descoberta estática de dispositivos ACPI."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DISCOVERY = ROOT / "kernel/src/acpi/aml_discovery.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class AcpiAmlDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DISCOVERY.read_text(encoding="utf-8")

    def test_discovery_is_fixed_capacity_read_only_and_post_loader(self):
        for token in (
            "AML_DISCOVERY_MAX_DEVICES: usize = 512",
            "AML_DISCOVERY_MAX_COMPAT_IDS: usize = 1024",
            "AML_DISCOVERY_MAX_RESOURCES: usize = 4096",
            "static mut AML_DISCOVERY_DEVICES",
            "static mut AML_DISCOVERY_COMPAT_IDS",
            "static mut AML_DISCOVERY_RESOURCES",
            "aml_namespace_is_ready()",
            "aml_loader_is_ready()",
            "aml_namespace_node(index)",
            "AML_NAMESPACE_KIND_DEVICE",
        ):
            self.assertIn(token, self.source)
        lower = self.source.lower()
        for forbidden in (
            "malloc(", "free(", "kmalloc", "heap_alloc", "bootservices",
            "systemtable", "mmio_write", "pci_write", "__out", "execute_method",
        ):
            self.assertNotIn(forbidden, lower)

    def test_predefined_names_are_looked_up_as_children_of_each_device(self):
        expected = {
            "AML_NAME_HID": "0x4449485F",
            "AML_NAME_CID": "0x4449435F",
            "AML_NAME_UID": "0x4449555F",
            "AML_NAME_ADR": "0x5244415F",
            "AML_NAME_STA": "0x4154535F",
            "AML_NAME_CRS": "0x5352435F",
        }
        for name, value in expected.items():
            self.assertIn(f"pub const {name}: u32 = {value}", self.source)
            self.assertIn(f"aml_namespace_find_child(namespace_index, {name})", self.source)

    def test_hid_accepts_only_spec_static_integer_or_id_string(self):
        hid = self.source.split("fn aml_discovery_hid_string_valid", 1)[1].split(
            "fn aml_discovery_swap_u32", 1
        )[0]
        self.assertIn("length == 7", hid)
        self.assertIn("length == 8", hid)
        self.assertIn("aml_discovery_ascii_upper", hid)
        self.assertIn("aml_discovery_ascii_hex", hid)
        node_id = self.source.split("fn aml_discovery_node_id", 1)[1].split(
            "fn aml_discovery_append_compat_id", 1
        )[0]
        self.assertIn("AML_NAMESPACE_VALUE_INTEGER", node_id)
        self.assertIn("AML_NAMESPACE_VALUE_STRING", node_id)
        self.assertIn("aml_discovery_eisa_id_valid", node_id)

    def test_eisa_id_conversion_is_32_bit_and_byte_swapped(self):
        conversion = self.source.split("pub fn aml_discovery_eisa_id_to_string", 1)[1].split(
            "fn aml_discovery_node_id", 1
        )[0]
        self.assertIn("capacity < 8", conversion)
        self.assertIn("aml_discovery_swap_u32(value as u32)", conversion)
        self.assertIn("(swapped >> 26)", conversion)
        self.assertIn("(swapped >> 21)", conversion)
        self.assertIn("(swapped >> 16)", conversion)
        self.assertIn("output[7] = 0", conversion)
        validator = self.source.split("fn aml_discovery_eisa_id_valid", 1)[1].split(
            "fn aml_discovery_hex_char", 1
        )[0]
        self.assertIn("value > 0xFFFFFFFF", validator)
        self.assertIn("first >= 1 && first <= 26", validator)

    def test_cid_supports_single_id_and_bounded_package(self):
        package = self.source.split("fn aml_discovery_parse_cid_package", 1)[1].split(
            "fn aml_discovery_resource_checksum_valid", 1
        )[0]
        self.assertIn("AML_NAMESPACE_VALUE_PACKAGE", package)
        self.assertIn("AML_NAMESPACE_VALUE_VAR_PACKAGE", package)
        self.assertIn("aml_decode_term_arg_constant(&mut cursor)", package)
        self.assertIn("aml_decode_data_object(&mut cursor)", package)
        self.assertIn("AML_DISCOVERY_MAX_COMPAT_IDS_PER_DEVICE", package)
        self.assertIn("AML_DATA_KIND_INTEGER", package)
        self.assertIn("AML_DATA_KIND_STRING", package)
        self.assertIn("aml_cursor_remaining(&cursor) != 0", package)

    def test_sta_is_constant_only_or_deferred_to_evaluator(self):
        device = self.source.split("fn aml_discovery_read_device", 1)[1].split(
            "pub fn aml_discovery_init", 1
        )[0]
        self.assertIn("AML_STA_DEFAULT", device)
        self.assertIn("status_requires_evaluator = true", device)
        self.assertIn("AML_NAMESPACE_KIND_METHOD", device)
        self.assertIn("AML_NAMESPACE_VALUE_INTEGER", device)
        self.assertIn("status > AML_STA_VALID_MASK as u64", device)
        self.assertIn("(status & 0x03) == 0x02", device)

    def test_crs_resource_template_parser_is_bounded_and_requires_end_tag(self):
        parser = self.source.split("fn aml_discovery_parse_resource_template", 1)[1].split(
            "fn aml_discovery_read_device", 1
        )[0]
        for token in (
            "(tag & 0x80) == 0",
            "payload_length = (tag & 0x07) as usize",
            "item_name = (tag >> 3) & 0x0F",
            "length - offset < 3",
            "item_name = tag & 0x7F",
            "data[offset + 1]",
            "data[offset + 2]",
            "AML_RESOURCE_END_TAG_NAME",
            "AML_RESOURCE_END_TAG_LENGTH",
            "offset != length",
            "aml_discovery_resource_checksum_valid",
        ):
            self.assertIn(token, parser)
        self.assertNotIn("offset += 1", parser)

    def test_dynamic_crs_is_not_executed(self):
        device = self.source.split("let crs_index =", 1)[1].split(
            "AML_DISCOVERY_DEVICES[device_slot].valid", 1
        )[0]
        self.assertIn("AML_NAMESPACE_KIND_METHOD", device)
        self.assertIn("crs_requires_evaluator = true", device)
        self.assertIn("AML_NAMESPACE_VALUE_BUFFER", device)
        self.assertIn("aml_discovery_parse_resource_template", device)
        self.assertNotIn("evaluate", device.lower())

    def test_runtime_and_three_gates_require_device_discovery_marker(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::aml_discovery::*;", runtime)
        run = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(run.index("aml_loader_emit_ready_marker()"), run.index("aml_discovery_init()"))
        self.assertLess(run.index("aml_discovery_emit_ready_marker()"), run.index("platform_inventory_init()"))
        self.assertIn("aml_discovery_emit_failure_markers()", run)

        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("ACPI_AML_DEVICES_READY", REQUIRED)
        from tools.scripts.run_smp_qemu import REQUIRED_MARKERS
        self.assertIn("BAKEN:ACPI_AML_DEVICES_READY", REQUIRED_MARKERS)

        smp = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        nvme = (ROOT / ".github/workflows/baken_nvme_only.yml").read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_acpi_aml_discovery.py", smp)
        self.assertIn("require_marker 'BAKEN:ACPI_AML_DEVICES_READY'", smp)
        self.assertIn("python3 tests/test_acpi_aml_discovery.py", nvme)
        self.assertIn("'BAKEN:ACPI_AML_DEVICES_READY'", nvme)

    def test_discovery_failure_is_fail_fast_in_runners(self):
        from tools.scripts.verify_kernel_smoke import validate as validate_smoke
        from tools.scripts.run_smp_qemu import validate as validate_smp
        sample = "BAKEN:HEX=R:09000010\nBAKEN:HEX=S:00000020\n"
        self.assertTrue(any("AML device discovery" in error for error in validate_smoke(sample)))
        self.assertTrue(any("AML device discovery" in error for error in validate_smp(sample)))


if __name__ == "__main__":
    unittest.main()
