"""Contratos I2C-0a para recursos ACPI I2CSerialBus/GpioInt."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/acpi/aml_i2c_resources.sotlas"
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


class AcpiI2cResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_in_native_sotlas_graph(self):
        self.assertIn(
            "import kernel::acpi::aml_i2c_resources::*;",
            self.main,
        )
        self.assertIn(
            "import kernel::acpi::aml_discovery::*;",
            self.source,
        )

    def test_i2c_serial_descriptor_uses_acpi_66_layout(self):
        expected = (
            "AML_I2C_RESOURCE_ITEM_SERIAL_BUS: u8 = 0x0E",
            "AML_I2C_SERIAL_BUS_TYPE: u8 = 1",
            "AML_I2C_SERIAL_REVISION: u8 = 2",
            "AML_I2C_TYPE_REVISION: u8 = 1",
            "AML_I2C_TYPE_DATA_MIN_LENGTH: usize = 6",
            "aml_i2c_read_u16(payload, 7)",
            "aml_i2c_read_u32(payload, 9)",
            "aml_i2c_read_u16(payload, 13)",
        )
        for token in expected:
            self.assertIn(token, self.source)

    def test_i2c_serial_decoder_is_bounded_and_fail_closed(self):
        body = function_body(self.source, "pub fn aml_i2c_decode_serial_bus")
        for token in (
            "(*descriptor).kind != AML_RESOURCE_KIND_LARGE",
            "(*descriptor).payload_length <",
            "(general_flags & 0xF8) != 0",
            "(type_flags_low & 0xFE) != 0",
            "type_data_length < AML_I2C_TYPE_DATA_MIN_LENGTH",
            "type_data_length > payload_length - AML_I2C_SERIAL_FIXED_PAYLOAD",
            "source_offset >= payload_length",
            "aml_i2c_source_exact_length",
            "(address & 0xFC00) != 0",
            "(address & 0xFF80) != 0",
        ):
            self.assertIn(token, body)
        self.assertIn("legacy_virtual_register: type_flags_high", body)

    def test_gpio_interrupt_descriptor_uses_relative_offsets_safely(self):
        body = function_body(self.source, "pub fn aml_i2c_decode_gpio_int")
        for token in (
            "AML_I2C_RESOURCE_ITEM_GPIO_CONNECTION",
            "AML_GPIO_CONNECTION_REVISION",
            "AML_GPIO_CONNECTION_INTERRUPT",
            "(general_flags & 0xFFFE) != 0",
            "(interrupt_flags & 0xFFE0) != 0",
            "polarity == 3",
            "polarity == 2 && !edge_triggered",
            "payload[13] != 0",
            "pin_table_full",
            "source_full",
            "vendor_full",
            "vendor_full + vendor_length != descriptor_length",
            "pin_table_full - AML_RESOURCE_LARGE_HEADER_LENGTH",
            "source_full - AML_RESOURCE_LARGE_HEADER_LENGTH",
            "vendor_full - AML_RESOURCE_LARGE_HEADER_LENGTH",
            "pin_count > AML_I2C_MAX_GPIO_PINS",
        ):
            self.assertIn(token, body)

    def test_resource_source_requires_exact_nul_terminated_region(self):
        body = function_body(self.source, "fn aml_i2c_source_exact_length")
        self.assertIn("region_length < 2", body)
        self.assertIn("index + 1 != region_length", body)
        self.assertIn("value < 0x20 || value > 0x7E", body)

    def test_gpio_pin_accessor_is_bounded(self):
        body = function_body(self.source, "pub fn aml_gpio_int_pin_at")
        self.assertIn("index >= (*resource).pin_count", body)
        self.assertIn("return 0xFFFF", body)
        self.assertIn("aml_i2c_read_u16((*resource).pin_table, index * 2)", body)

    def test_i2c_0a_has_no_hardware_or_hid_side_effects(self):
        lower = self.source.lower()
        for forbidden in (
            "mmio_write", "mmio_read", "pci_write", "pci_read",
            "dma_alloc", "dma_release", "pmm_free", "xhci_",
            "hid_report", "input_device", "irq_register", "__out",
            "execute_method", "aml_evaluate",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotIn("static mut", lower)


if __name__ == "__main__":
    unittest.main()
