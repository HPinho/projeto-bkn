from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "kernel/src/drivers/i2c_hid_command.sotlas"
INPUT = ROOT / "kernel/src/drivers/i2c_hid_input.sotlas"
GPIO = ROOT / "kernel/src/drivers/gpio_core.sotlas"


class I2cHidHardeningContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.command = COMMAND.read_text(encoding="utf-8")
        cls.input = INPUT.read_text(encoding="utf-8")
        cls.gpio = GPIO.read_text(encoding="utf-8")

    def test_get_report_is_single_write_read_transaction(self):
        start = self.command.index("pub fn i2c_hid_command_get_report(")
        end = self.command.index("pub fn i2c_hid_command_set_report(")
        body = self.command[start:end]
        self.assertIn("i2c_device_write_read(", body)
        self.assertNotIn("i2c_device_write(device_id", body)
        self.assertIn("cmd[cmd_len] = (data_register & 0xFF) as u8;", body)
        self.assertIn("cmd_len += 2;", body)

    def test_extended_report_id_follows_opcode(self):
        encode_start = self.command.index("fn i2c_hid_command_encode_report(")
        encode_end = self.command.index("pub fn i2c_hid_command_get_report(")
        body = self.command[encode_start:encode_end]
        opcode_pos = body.index("out_buf[3] = opcode;")
        report_pos = body.index("out_buf[4] = report_id;")
        self.assertLess(opcode_pos, report_pos)

    def test_set_report_is_one_write_with_length_and_optional_id(self):
        start = self.command.index("pub fn i2c_hid_command_set_report(")
        body = self.command[start:]
        self.assertEqual(body.count("i2c_device_write("), 1)
        self.assertIn("let total_wire_len = 2 + report_id_bytes + report_length;", body)
        self.assertIn("if report_id != 0 {", body)
        self.assertIn("send_buf[offset] = report_id;", body)

    def test_input_registration_rejects_truncation(self):
        self.assertIn("max_input_length as usize > I2C_HID_MAX_INPUT_BUFFER_BYTES", self.input)
        self.assertIn("if read_len > buf_capacity || read_len > I2C_HID_MAX_INPUT_BUFFER_BYTES", self.input)
        self.assertNotIn("if read_len > buf_capacity { read_len = buf_capacity; }", self.input)

    def test_input_runtime_index_is_explicit_and_reusable(self):
        self.assertIn("pub const I2C_HID_INPUT_INVALID_INDEX", self.input)
        self.assertIn("pub fn i2c_hid_input_register_device_index", self.input)
        self.assertIn("pub fn i2c_hid_input_unregister_device", self.input)
        self.assertIn("while I2C_HID_INPUT_COUNT > 0", self.input)

    def test_gpio_pin_zero_is_not_global_wildcard(self):
        notify_start = self.input.index("pub fn i2c_hid_input_notify_irq(")
        notify_end = self.input.index("pub fn i2c_hid_input_fetch_report(")
        body = self.input[notify_start:notify_end]
        self.assertIn("I2C_HID_INPUT_DEVICES[i].gpio_pin == gpio_pin", body)
        self.assertNotIn("gpio_pin == 0", body)

    def test_gpio_requires_registered_physical_owner(self):
        self.assertIn("pub struct GpioPhysicalBackend", self.gpio)
        self.assertIn("pub fn gpio_physical_backend_register", self.gpio)
        self.assertIn("pub fn gpio_physical_backend_unregister", self.gpio)
        self.assertIn("pub fn gpio_physical_backend_available", self.gpio)
        self.assertIn("controller == AML_NAMESPACE_INVALID_INDEX || !gpio_physical_backend_available(controller)", self.gpio)

    def test_gpio_backend_cannot_unregister_while_connections_live(self):
        start = self.gpio.index("pub fn gpio_physical_backend_unregister(")
        end = self.gpio.index("pub fn gpio_physical_backend_available(")
        body = self.gpio[start:end]
        self.assertIn("let mut busy = false;", body)
        self.assertIn("if !busy {", body)
        self.assertIn("GPIO_CONNECTIONS[connection].controller_namespace_index == controller_namespace_index", body)


if __name__ == "__main__":
    unittest.main()
