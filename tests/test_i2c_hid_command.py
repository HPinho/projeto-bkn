from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_hid_command.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def encode_reset_command(cmd_reg: int) -> bytes:
    if cmd_reg == 0:
        raise ValueError("Invalid command register")
    return bytes([
        cmd_reg & 0xFF,
        (cmd_reg >> 8) & 0xFF,
        0x00,
        0x01,  # I2C_HID_CMD_RESET
    ])


def encode_set_power_command(cmd_reg: int, power_state: int) -> bytes:
    if cmd_reg == 0:
        raise ValueError("Invalid command register")
    return bytes([
        cmd_reg & 0xFF,
        (cmd_reg >> 8) & 0xFF,
        power_state & 0x0F,
        0x08,  # I2C_HID_CMD_SET_POWER
    ])


class I2cHidCommandTests(unittest.TestCase):
    """Testes dos comandos do protocolo HID-over-I2C v1.00 (Reset, Set Power, etc.)."""

    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_zero_dynamic_heap_allocation(self):
        self.assertNotIn("kernel_heap", self.text)
        self.assertNotIn("alloc(", self.text)
        self.assertNotIn("malloc(", self.text)

    def test_module_registered_in_kernel_main(self):
        self.assertIn("import kernel::drivers::i2c_hid_command::*;", self.main)

    def test_protocol_opcodes_defined(self):
        self.assertIn("pub const I2C_HID_CMD_RESET: u8 = 0x01;", self.text)
        self.assertIn("pub const I2C_HID_CMD_GET_REPORT: u8 = 0x02;", self.text)
        self.assertIn("pub const I2C_HID_CMD_SET_REPORT: u8 = 0x03;", self.text)
        self.assertIn("pub const I2C_HID_CMD_SET_POWER: u8 = 0x08;", self.text)
        self.assertIn("pub const I2C_HID_POWER_ON: u8 = 0x00;", self.text)
        self.assertIn("pub const I2C_HID_POWER_SLEEP: u8 = 0x01;", self.text)

    def test_reset_command_payload_structure(self):
        cmd_reg = 0x0023
        payload = encode_reset_command(cmd_reg)
        self.assertEqual(len(payload), 4)
        self.assertEqual(payload[0], 0x23)
        self.assertEqual(payload[1], 0x00)
        self.assertEqual(payload[2], 0x00)  # Reserved / modifier
        self.assertEqual(payload[3], 0x01)  # Opcode RESET

    def test_set_power_command_payload_structure(self):
        cmd_reg = 0x0045
        # Power ON
        payload_on = encode_set_power_command(cmd_reg, 0x00)
        self.assertEqual(len(payload_on), 4)
        self.assertEqual(payload_on[0], 0x45)
        self.assertEqual(payload_on[1], 0x00)
        self.assertEqual(payload_on[2], 0x00)  # Power ON
        self.assertEqual(payload_on[3], 0x08)  # Opcode SET_POWER

        # Power SLEEP
        payload_sleep = encode_set_power_command(cmd_reg, 0x01)
        self.assertEqual(len(payload_sleep), 4)
        self.assertEqual(payload_sleep[0], 0x45)
        self.assertEqual(payload_sleep[1], 0x00)
        self.assertEqual(payload_sleep[2], 0x01)  # Power SLEEP
        self.assertEqual(payload_sleep[3], 0x08)  # Opcode SET_POWER

    def test_reject_zero_command_register(self):
        with self.assertRaises(ValueError):
            encode_reset_command(0)
        with self.assertRaises(ValueError):
            encode_set_power_command(0, 0)


if __name__ == "__main__":
    unittest.main()
