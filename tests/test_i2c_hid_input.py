from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_hid_input.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def unpack_input_report(raw_wire: bytes, buf_capacity: int) -> tuple[int, bytes]:
    """Decodifica relatório de entrada conforme especificação Microsoft HID-over-I2C.
    Primeiros 2 bytes contêm o comprimento total wLength (incluindo os 2 bytes).
    """
    if len(raw_wire) < 2:
        return 0, b""
    wire_len = struct.unpack_from("<H", raw_wire, 0)[0]
    if wire_len < 2:
        return 0, b""
    actual_len = min(wire_len, len(raw_wire), buf_capacity)
    payload_len = actual_len - 2
    return payload_len, raw_wire[2 : 2 + payload_len]


class I2cHidInputTests(unittest.TestCase):
    """Testes do pipeline de recepção e despacho de entrada HID-over-I2C."""

    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_zero_dynamic_heap_allocation(self):
        self.assertNotIn("kernel_heap", self.text)
        self.assertNotIn("alloc(", self.text)
        self.assertNotIn("malloc(", self.text)

    def test_module_registered_in_kernel_main(self):
        self.assertIn("import kernel::drivers::i2c_hid_input::*;", self.main)

    def test_bounded_capacities_and_device_table(self):
        self.assertIn("pub const I2C_HID_MAX_INPUT_DEVICES: usize = 4;", self.text)
        self.assertIn("pub const I2C_HID_MAX_INPUT_BUFFER_BYTES: usize = 256;", self.text)
        self.assertIn("pub struct I2cHidInputDevice", self.text)
        self.assertIn("static mut I2C_HID_INPUT_DEVICES: [I2cHidInputDevice; I2C_HID_MAX_INPUT_DEVICES]", self.text)

    def test_pure_read_transaction_used(self):
        # O serviço de input deve usar READ puro do escravo, sem escrever wInputRegister antes
        self.assertIn("i2c_device_read(", self.text)
        self.assertNotIn("i2c_device_write_read(", self.text)

    def test_wlength_validation_and_reset_ack(self):
        # Trata wLength == 0 como confirmação de reset ou frame nulo
        self.assertIn("wire_length == 0", self.text)
        # Rejeita wLength malformado (1 ou maior que recebido)
        self.assertIn("wire_length == 1 || wire_length > read_len", self.text)

    def test_shared_hid_pipeline_dispatch(self):
        # Despacha relatório desembrulhado para o decodificador HID genérico
        self.assertIn("hid_input_events_process_report_for_device(", self.text)

    def test_spinlock_thread_safety(self):
        self.assertIn("static mut I2C_HID_INPUT_LOCK: SpinLock", self.text)
        self.assertIn("x86_irq_save_disable()", self.text)
        self.assertIn("x86_irq_restore(flags)", self.text)
        self.assertIn("spinlock_lock(&mut I2C_HID_INPUT_LOCK)", self.text)
        self.assertIn("spinlock_unlock(&mut I2C_HID_INPUT_LOCK)", self.text)

    def test_unpack_valid_mouse_report(self):
        # 2 bytes comprimento (ex: 6 = 2 cabeçalho + 4 bytes mouse: buttons, dx, dy, wheel)
        wire_data = struct.pack("<H Bbb b", 6, 0x01, 10, -5, 0)
        payload_len, payload = unpack_input_report(wire_data, 256)
        self.assertEqual(payload_len, 4)
        self.assertEqual(payload, bytes([0x01, 10, 0xFB, 0]))

    def test_unpack_empty_or_null_report(self):
        # Dispositivo sinaliza sem dados pendentes com wLength = 0
        wire_data = struct.pack("<H", 0)
        payload_len, payload = unpack_input_report(wire_data, 256)
        self.assertEqual(payload_len, 0)
        self.assertEqual(payload, b"")

        # wLength = 1 (inválido por especificação)
        wire_data_one = struct.pack("<H", 1)
        payload_len, payload = unpack_input_report(wire_data_one, 256)
        self.assertEqual(payload_len, 0)
        self.assertEqual(payload, b"")

    def test_unpack_keyboard_boot_report(self):
        # 2 bytes cabeçalho + 8 bytes HID keyboard boot report (modifiers, reserved, keycodes[6])
        wire_data = struct.pack("<H BB 6B", 10, 0x02, 0x00, 0x04, 0, 0, 0, 0, 0)
        payload_len, payload = unpack_input_report(wire_data, 256)
        self.assertEqual(payload_len, 8)
        self.assertEqual(payload[0], 0x02)  # Modificador (ex: Shift)
        self.assertEqual(payload[2], 0x04)  # Key 'A'


if __name__ == "__main__":
    unittest.main()
