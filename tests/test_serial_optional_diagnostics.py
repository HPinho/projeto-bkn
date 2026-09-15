"""Guardrails para diagnóstico de boot independente de UART legado."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERIAL = ROOT / "kernel/src/arch/x86_64/serial.sotlas"
ADDRESS_SPACE = ROOT / "kernel/src/process/address_space.sotlas"
REGISTRY = ROOT / "kernel/src/process/registry.sotlas"
FPU = ROOT / "kernel/src/arch/x86_64/fpu.sotlas"
USERSPACE = ROOT / "kernel/src/process/userspace_loader.sotlas"


class SerialOptionalDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.serial = SERIAL.read_text(encoding="utf-8")

    def test_ram_boot_log_is_authoritative_and_uart_is_optional(self):
        for token in (
            "boot log em RAM é o sink autoritativo de diagnóstico",
            "COM1/UART é apenas",
            "x86_serial_is_ready() explicitamente",
        ):
            self.assertIn(token, self.serial)

    def test_single_byte_capture_does_not_fail_without_uart(self):
        body = self.serial.split("pub fn x86_serial_write_byte(value: u8) -> bool", 1)[1]
        body = body.split("pub fn x86_serial_write_buffer", 1)[0]
        self.assertIn("x86_boot_log_append(value);", body)
        self.assertIn("if x86_serial_is_ready()", body)
        self.assertIn("x86_serial_write_byte_unlocked(value);", body)
        self.assertIn("return true;", body)
        self.assertNotIn("let success = x86_serial_is_ready() &&", body)

    def test_buffer_capture_does_not_fail_without_uart(self):
        body = self.serial.split("pub fn x86_serial_write_buffer(bytes: *const u8, length: usize) -> bool", 1)[1]
        body = body.split("fn x86_serial_hex_digit", 1)[0]
        self.assertIn("x86_boot_log_append(bytes[index]);", body)
        self.assertIn("if x86_serial_is_ready()", body)
        self.assertIn("if !x86_serial_write_byte_unlocked(bytes[index]) { break; }", body)
        self.assertIn("return true;", body)
        self.assertNotIn("if !x86_serial_is_ready()", body)
        self.assertNotIn("return success;", body)

    def test_uart_health_remains_observable_separately(self):
        self.assertIn("pub fn x86_serial_is_ready() -> bool", self.serial)
        transport = self.serial.split("fn x86_serial_write_byte_unlocked", 1)[1]
        transport = transport.split("pub fn x86_serial_write_byte", 1)[0]
        self.assertIn("X86_SERIAL_READY = false", transport)
        self.assertIn("return false;", transport)

    def test_existing_subsystems_inherit_common_diagnostic_policy(self):
        # Estes marcadores já usam a camada serial comum. A política central
        # evita hacks ASUS/Dell/Lenovo e cobre também os próximos gates do boot.
        sources = {
            "address_space": ADDRESS_SPACE.read_text(encoding="utf-8"),
            "registry": REGISTRY.read_text(encoding="utf-8"),
            "fpu": FPU.read_text(encoding="utf-8"),
            "userspace": USERSPACE.read_text(encoding="utf-8"),
        }
        self.assertIn("process_address_space_emit_ready_marker", sources["address_space"])
        self.assertIn("x86_serial_write_byte", sources["address_space"])
        self.assertIn("process_registry_emit_ready_marker", sources["registry"])
        self.assertIn("x86_serial_write_byte", sources["registry"])
        self.assertIn("fpu_emit_ready_marker", sources["fpu"])
        self.assertIn("x86_serial_write_byte", sources["fpu"])
        self.assertIn("userspace_emit", sources["userspace"])
        self.assertIn("x86_serial_write_byte", sources["userspace"])


if __name__ == "__main__":
    unittest.main()
