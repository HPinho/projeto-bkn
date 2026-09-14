from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_hid_manager.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cHidManagerTests(unittest.TestCase):
    """Contratos do lifecycle físico HID-over-I2C."""

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
        self.assertIn("pub const I2C_HID_RESET_ACK_SPINS: usize = 200000;", self.text)
        self.assertIn("static mut I2C_HID_MANAGED_DEVICES: [I2cHidManagedDevice; I2C_HID_MANAGER_MAX_MANAGED]", self.text)
        self.assertIn("static mut I2C_HID_SERVICE_BUFFER: [u8; I2C_HID_MAX_INPUT_BUFFER_BYTES]", self.text)

    def test_orchestration_links_all_stages(self):
        self.assertIn("i2c_hid_acpi_device_count()", self.text)
        self.assertIn("i2c_hid_acpi_get_device(i)", self.text)
        self.assertIn("i2c_device_attach(&cfg)", self.text)
        self.assertIn("i2c_device_activate(handle.device_id, handle.generation)", self.text)
        self.assertIn("i2c_hid_read_descriptor_physical(", self.text)
        self.assertIn("i2c_hid_command_set_power(", self.text)
        self.assertIn("i2c_hid_command_reset(", self.text)
        self.assertIn("i2c_hid_read_report_descriptor_physical(", self.text)
        self.assertIn("i2c_hid_parse_report_descriptor(", self.text)
        self.assertIn("i2c_hid_input_register_device_index(", self.text)

    def test_canonical_boot_sequence_wires_hid_manager(self):
        self.assertIn("i2c_hid_acpi_scan_devices();", self.runtime)
        self.assertIn("i2c_hid_manager_init();", self.runtime)
        self.assertLess(
            self.runtime.index("i2c_hid_acpi_scan_devices();"),
            self.runtime.index("i2c_hid_manager_init();"),
        )

    def test_fail_closed_and_non_blocking_on_empty_bus(self):
        self.assertIn("let mut dev_count = i2c_hid_acpi_device_count();", self.text)
        self.assertIn("if dev_count == 0 { return 0; }", self.text)
        self.assertNotIn("loop {", self.text)
        self.assertNotIn("panic(", self.text)

    def test_gpio_is_mandatory_and_physically_backed(self):
        self.assertIn("gpio_connection_register_from_acpi(", self.text)
        self.assertIn("if gpio_handle.valid {", self.text)
        self.assertIn("i2c_device_set_gpio(", self.text)
        self.assertNotIn("gpio_pin == 0", self.text)

    def test_reset_handshake_requires_gpio_irq_before_read(self):
        consume = self.text.index("gpio_connection_consume_pending(gpio_connection_id, gpio_generation)")
        read = self.text.index("i2c_device_read(device_id, generation, &mut ack[0], 2)")
        self.assertLess(consume, read)
        self.assertIn("return wire_length == 0;", self.text)
        self.assertIn("while spin < I2C_HID_RESET_ACK_SPINS", self.text)

    def test_report_descriptor_and_input_length_are_bounded(self):
        self.assertIn("desc_rep_len <= I2C_HID_CERTIFIED_REPORT_MAX", self.text)
        self.assertIn("desc.w_max_input_length as usize <= I2C_HID_MAX_INPUT_BUFFER_BYTES", self.text)

    def test_runtime_index_is_not_acpi_device_slot(self):
        self.assertIn("pub input_device_index: usize;", self.text)
        self.assertIn("input_index = i2c_hid_input_register_device_index(", self.text)
        self.assertIn("i2c_hid_input_has_pending_irq(dev.input_device_index)", self.text)
        self.assertIn("i2c_hid_input_fetch_report(dev.input_device_index", self.text)
        self.assertNotIn("i2c_hid_input_has_pending_irq(dev.device_slot)", self.text)
        self.assertNotIn("i2c_hid_input_fetch_report(\n                        dev.device_slot", self.text)

    def test_full_rollback_is_generation_safe(self):
        for token in (
            "i2c_hid_input_unregister_device(input_device_index)",
            "hid_input_events_unbind_device(input_device_id, input_device_generation)",
            "hid_input_device_map_unbind(input_device_id, input_device_generation)",
            "input_device_detach(input_device_id, input_device_generation)",
            "gpio_connection_unregister(gpio_connection_id, gpio_generation)",
            "i2c_device_detach(device_id, generation)",
        ):
            self.assertIn(token, self.text)

    def test_shared_hid_input_convergence_checks_every_stage(self):
        self.assertIn("let map_ok = unsafe", self.text)
        self.assertIn("if map_ok && hid_input_events_bind_device", self.text)
        self.assertIn("operational = input_index != I2C_HID_INPUT_INVALID_INDEX;", self.text)

    def test_runtime_services_i2c_hid_loop(self):
        self.assertIn("pub fn i2c_hid_manager_service_once() -> usize", self.text)
        self.assertIn("i2c_hid_manager_service_once();", self.runtime)


if __name__ == "__main__":
    unittest.main()
