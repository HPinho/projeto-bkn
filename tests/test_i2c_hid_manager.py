from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_hid_manager.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cHidManagerTests(unittest.TestCase):
    """Testes de orquestração do ciclo de vida dos dispositivos HID-over-I2C."""

    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_zero_dynamic_heap_allocation(self):
        self.assertNotIn("kernel_heap", self.text)
        self.assertNotIn("alloc(", self.text)
        self.assertNotIn("malloc(", self.text)

    def test_module_registered_in_kernel_main(self):
        self.assertIn("import kernel::drivers::i2c_hid_manager::*;", self.main)

    def test_bounded_managed_devices_table(self):
        self.assertIn("pub const I2C_HID_MANAGER_MAX_MANAGED: usize = I2C_HID_MAX_DEVICES;", self.text)
        self.assertIn("pub const I2C_HID_CERTIFIED_REPORT_MAX: usize = 2048;", self.text)
        self.assertIn("static mut I2C_HID_MANAGED_DEVICES: [I2cHidManagedDevice; I2C_HID_MANAGER_MAX_MANAGED]", self.text)
        self.assertIn("static mut I2C_HID_REPORT_SCRATCH: [u8; I2C_HID_CERTIFIED_REPORT_MAX]", self.text)

    def test_orchestration_links_all_stages(self):
        # Descoberta ACPI idempotente (I2C-HID-0)
        self.assertIn("i2c_hid_acpi_device_count()", self.text)
        self.assertIn("i2c_hid_acpi_get_device(i)", self.text)
        # Device Model I2C (I2C-4)
        self.assertIn("i2c_device_attach(&cfg)", self.text)
        self.assertIn("i2c_device_activate(handle.device_id, handle.generation)", self.text)
        # Descritor HID Físico (I2C-HID-1)
        self.assertIn("i2c_hid_read_descriptor_physical(", self.text)
        # Comandos de Ciclo de Vida (I2C-HID-5)
        self.assertIn("i2c_hid_command_set_power(", self.text)
        self.assertIn("i2c_hid_command_reset(", self.text)
        # Report Descriptor Físico e Parsing (I2C-HID-2)
        self.assertIn("i2c_hid_read_report_descriptor_physical(", self.text)
        self.assertIn("i2c_hid_parse_report_descriptor(", self.text)
        # Pipeline de Entrada (I2C-HID-4)
        self.assertIn("i2c_hid_input_register_device(", self.text)

    def test_canonical_boot_sequence_wires_hid_manager(self):
        self.assertIn("i2c_hid_acpi_scan_devices();", self.runtime)
        self.assertIn("i2c_hid_manager_init();", self.runtime)

        acpi_scan_idx = self.runtime.index("i2c_hid_acpi_scan_devices();")
        mgr_init_idx = self.runtime.index("i2c_hid_manager_init();")
        self.assertLess(acpi_scan_idx, mgr_init_idx)

    def test_fail_closed_and_non_blocking_on_empty_bus(self):
        # Evita double-scan consultando device_count idempotente
        self.assertIn("let mut dev_count = i2c_hid_acpi_device_count();", self.text)
        self.assertIn("if dev_count == 0 { return 0; }", self.text)
        # Sem loops infinitos
        self.assertNotIn("loop {", self.text)
        self.assertNotIn("panic(", self.text)

    def test_gpio_interrupt_connection_registered(self):
        # Transforma GpioInt em conexão real
        self.assertIn("gpio_connection_register_from_acpi(", self.text)
        self.assertIn("i2c_device_set_gpio(", self.text)

    def test_reset_handshake_and_bounded_report_descriptor(self):
        # Protocolo de RESET verifica handshake ACK (wLength == 0)
        self.assertIn("reset_ack = true;", self.text)
        # Bounded report descriptor sem truncamento silencioso
        self.assertIn("desc_rep_len <= I2C_HID_CERTIFIED_REPORT_MAX", self.text)

    def test_shared_hid_input_convergence(self):
        # Integração no subsistema unificado de input
        self.assertIn("input_device_attach(", self.text)
        self.assertIn("hid_input_device_map_build(", self.text)
        self.assertIn("hid_input_events_bind_device(", self.text)

    def test_runtime_services_i2c_hid_loop(self):
        # O manager exporta rotina de serviço consumida no loop principal
        self.assertIn("pub fn i2c_hid_manager_service_once() -> usize", self.text)
        self.assertIn("i2c_hid_manager_service_once();", self.runtime)


if __name__ == "__main__":
    unittest.main()
