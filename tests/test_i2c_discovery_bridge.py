from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_discovery_bridge.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cDiscoveryBridgeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_bridge_has_capacity_and_constants(self):
        for token in (
            "pub const I2C_BRIDGE_CAPACITY: usize = 16",
            "pub const I2C_BRIDGE_DEFAULT_SPEED_HZ: u32 = 400000",
            "pub const I2C_BRIDGE_STANDARD_SPEED_HZ: u32 = 100000",
            "pub struct I2cBridgeController",
            "static mut I2C_BRIDGE_CONTROLLERS",
        ):
            self.assertIn(token, self.text)

    def test_bridge_provides_default_capabilities(self):
        self.assertIn("pub fn i2c_discovery_default_capabilities", self.text)
        self.assertIn("supports_7bit: true", self.text)
        self.assertIn("supports_repeated_start: true", self.text)
        self.assertIn("max_messages: I2C_MAX_MESSAGES", self.text)

    def test_bridge_registers_controller_with_generation_safe_registry(self):
        self.assertIn("pub fn i2c_discovery_register_controller", self.text)
        self.assertIn("i2c_controller_registry_attach", self.text)
        self.assertIn("i2c_controller_handle_valid(&handle)", self.text)
        self.assertIn("i2c_discovery_bridge_find_by_namespace", self.text)

    def test_bridge_scans_and_resolves_acpi_resources(self):
        self.assertIn("pub fn i2c_discovery_scan_acpi_controllers", self.text)
        self.assertIn("aml_i2c_binding_for_resource", self.text)
        self.assertIn("pub fn i2c_discovery_find_controller_for_resource", self.text)
        self.assertIn("i2c_discovery_bridge_record_device", self.text)

    def test_bridge_is_thread_safe_with_irq_spinlock(self):
        self.assertIn("x86_irq_save_disable()", self.text)
        self.assertIn("x86_irq_restore(flags)", self.text)
        self.assertIn("spinlock_lock(&mut I2C_BRIDGE_LOCK)", self.text)
        self.assertIn("spinlock_unlock(&mut I2C_BRIDGE_LOCK)", self.text)


if __name__ == "__main__":
    unittest.main()
