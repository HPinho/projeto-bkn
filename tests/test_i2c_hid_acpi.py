from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_hid_acpi.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class I2cHidAcpiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")

    def test_i2c_hid_acpi_is_in_native_graph(self):
        self.assertIn("import kernel::drivers::i2c_hid_acpi::*;", self.main)
        self.assertIn("import kernel::drivers::i2c_hid_acpi::*;", self.runtime)

    def test_microsoft_hidi2c_uuid_bytes(self):
        # UUID 3cdff6f7-4267-4555-ad05-b30a3d8938de em little-endian RFC 4122
        expected_bytes = (
            "0xF7, 0xF6, 0xDF, 0x3C",
            "0x67, 0x42",
            "0x55, 0x45",
            "0xAD, 0x05, 0xB3, 0x0A, 0x3D, 0x89, 0x38, 0xDE",
        )
        for token in expected_bytes:
            self.assertIn(token, self.text)

    def test_constants_and_data_structures(self):
        for token in (
            "pub const I2C_HID_MAX_DEVICES: usize = 4;",
            "pub const I2C_HID_DSM_FUNCTION_QUERY: u64 = 0;",
            "pub const I2C_HID_DSM_FUNCTION_DESCRIPTOR_ADDRESS: u64 = 1;",
            "pub const I2C_HID_DSM_REVISION: u64 = 1;",
            "pub struct I2cHidAcpiDescriptor",
            "pub slave_address: u16;",
            "pub bus_speed_hz: u32;",
            "pub hid_descriptor_register: u16;",
            "pub gpio_pin: u16;",
            "pub gpio_polarity: u8;",
            "pub gpio_trigger: u8;",
            "pub dsm_evaluated: bool;",
        ):
            self.assertIn(token, self.text)

    def test_detection_checks_both_hid_and_cid_pnp0c50(self):
        # Invariante I2C-HID-0: detecção de PNP0C50 e ACPI0C50 tanto em _HID quanto em _CID
        self.assertIn("pub fn i2c_hid_device_is_pnp0c50(device_slot: usize) -> bool", self.text)
        self.assertIn("aml_i2c_device_has_static_pnp0c50(device_slot)", self.text)

    def test_dsm_evaluation_queries_fn0_and_extracts_fn1(self):
        # Invariante I2C-HID-0: avaliação canônica de _DSM (Function 0 valida suporte e Function 1 obtém o registrador)
        self.assertIn("pub fn i2c_hid_evaluate_dsm", self.text)
        self.assertIn("pub fn i2c_hid_evaluate_descriptor_register", self.text)
        self.assertIn("I2C_HID_DSM_FUNCTION_QUERY", self.text)
        self.assertIn("I2C_HID_DSM_FUNCTION_DESCRIPTOR_ADDRESS", self.text)
        # Bit 1 na máscara da Function 0
        self.assertIn("(query_mask & 0x02) == 0", self.text)

    def test_crs_extracts_serial_bus_and_gpio_resources(self):
        # Invariante I2C-HID-0: extração do I2CSerialBusConnection e GpioInt
        self.assertIn("aml_i2c_decode_serial_bus", self.text)
        self.assertIn("aml_i2c_binding_for_resource", self.text)
        self.assertIn("aml_i2c_decode_gpio_int", self.text)

    def test_registry_and_bridge_binding(self):
        # Invariante I2C-HID-0: associação generation-safe do controller via discovery bridge
        self.assertIn("i2c_discovery_bridge_find_by_namespace", self.text)
        self.assertIn("i2c_controller_handle_valid", self.text)


if __name__ == "__main__":
    unittest.main()
