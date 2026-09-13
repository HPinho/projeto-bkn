"""Contratos I2C-0b para binding ACPI read-only de ResourceSource/controller."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/acpi/aml_i2c_binding.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    raise AssertionError(f"unterminated function: {signature}")


class AcpiI2cBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_part_of_native_graph_and_depends_on_published_acpi_layers(self):
        self.assertIn("import kernel::acpi::aml_i2c_binding::*;", self.main)
        for token in (
            "import kernel::acpi::aml_decoder::*;",
            "import kernel::acpi::aml_data::*;",
            "import kernel::acpi::aml_namespace::*;",
            "import kernel::acpi::aml_discovery::*;",
            "import kernel::acpi::aml_i2c_resources::*;",
        ):
            self.assertIn(token, self.source)

    def test_resource_source_parser_supports_root_parent_and_namespace_search(self):
        body = function_body(self.source, "pub fn aml_i2c_resolve_resource_source")
        for token in (
            "source[0] == '\\\\' as u8",
            "source[offset] == '^' as u8",
            "source[offset] != '.' as u8",
            "AML_NAME_MAX_SEGMENTS",
            "aml_i2c_namespace_walk",
            "aml_i2c_namespace_parent",
            "if parent_prefixes != 0",
            "if rooted",
            "let mut search_scope = base",
            "while searching",
        ):
            self.assertIn(token, body)
        self.assertIn("length != 4", self.source)
        self.assertIn("aml_i2c_source_lead_char", self.source)
        self.assertIn("aml_i2c_source_name_char", self.source)

    def test_resolved_resource_source_must_be_an_acpi_device(self):
        body = function_body(self.source, "fn aml_i2c_controller_node_valid")
        self.assertIn("aml_namespace_node(index)", body)
        self.assertIn("AML_NAMESPACE_KIND_DEVICE", body)
        resolver = function_body(self.source, "pub fn aml_i2c_resolve_resource_source")
        self.assertIn("aml_i2c_controller_node_valid", resolver)

    def test_pnp0c50_detection_accepts_static_string_or_eisa_id(self):
        for token in (
            "fn aml_i2c_bytes_are_pnp0c50",
            "fn aml_i2c_bytes_are_acpi0c50",
            "AML_DISCOVERY_ID_STRING",
            "AML_DISCOVERY_ID_INTEGER",
            "aml_discovery_eisa_id_to_string",
            "cid_requires_evaluator",
        ):
            self.assertIn(token, self.source)
        body = function_body(self.source, "pub fn aml_i2c_device_has_static_pnp0c50")
        self.assertIn("(*device).cid_requires_evaluator", body)
        self.assertIn("aml_discovery_compat_id", body)

    def test_hidi2c_dsm_contract_is_declared_but_never_executed(self):
        expected = (
            "AML_I2C_NAME_DSM: u32 = 0x4D53445F",
            "AML_I2C_HID_DSM_GUID_DATA1: u32 = 0x3CDFF6F7",
            "AML_I2C_HID_DSM_GUID_DATA2: u16 = 0x4267",
            "AML_I2C_HID_DSM_GUID_DATA3: u16 = 0x4555",
            "AML_I2C_HID_DSM_GUID_DATA4_0: u8 = 0xAD",
            "AML_I2C_HID_DSM_GUID_DATA4_7: u8 = 0xDE",
            "AML_I2C_HID_DSM_REVISION: u64 = 1",
            "AML_I2C_HID_DSM_FUNCTION_QUERY: u64 = 0",
            "AML_I2C_HID_DSM_FUNCTION_DESCRIPTOR_ADDRESS: u64 = 1",
        )
        for token in expected:
            self.assertIn(token, self.source)
        dsm = function_body(self.source, "fn aml_i2c_dsm_method_index")
        self.assertIn("aml_namespace_find_child(namespace_index, AML_I2C_NAME_DSM)", dsm)
        self.assertIn("AML_NAMESPACE_KIND_METHOD", dsm)

    def test_binding_is_scoped_to_one_i2c_resource_and_its_owner(self):
        body = function_body(self.source, "pub fn aml_i2c_binding_for_resource")
        for token in (
            "aml_i2c_decode_serial_bus(resource_index)",
            "!serial.valid || !serial.consumer",
            "aml_discovery_device(serial.device_slot)",
            "resource_index < resource_start",
            "resource_index >= resource_start + resource_count",
            "aml_i2c_resolve_resource_source",
            "controller_namespace_index: controller",
            "resource_source_index: serial.resource_source_index",
            "slave_address: serial.slave_address",
            "connection_speed_hz: serial.connection_speed_hz",
        ):
            self.assertIn(token, body)

    def test_hid_transport_preparation_is_strict_and_not_full_enumeration(self):
        body = function_body(self.source, "pub fn aml_i2c_binding_for_resource")
        for token in (
            "pnp0c50 && !cid_requires_evaluator && dsm_present",
            "gpio_resource_count == 1",
            "gpio_controller != AML_NAMESPACE_INVALID_INDEX",
            "gpio_consumer",
            "gpio_pin_count == 1",
            "!serial.device_initiated",
            "hid_transport_prepared: hid_prepared",
        ):
            self.assertIn(token, body)
        self.assertIn("_HRV e execução/query de _DSM ficam em I2C-HID-0", self.source)

    def test_i2c_0b_is_read_only_and_has_no_hardware_or_method_execution(self):
        lower = self.source.lower()
        for forbidden in (
            "mmio_write", "mmio_read", "pci_write", "pci_read",
            "dma_alloc", "dma_release", "pmm_free", "irq_register",
            "__out", "xhci_", "hid_report", "input_device",
            "execute_method", "aml_evaluate", "aml_method_execute",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotIn("static mut", lower)


if __name__ == "__main__":
    unittest.main()
