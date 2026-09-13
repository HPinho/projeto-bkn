from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_controller.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cControllerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_in_native_graph(self):
        self.assertIn("import kernel::drivers::i2c_controller::*;", self.main)

    def test_generation_safe_identity_contract(self):
        for token in (
            "pub struct I2cControllerHandle",
            "pub controller_id: u32",
            "pub generation: u32",
            "I2C_CONTROLLER_ID_NONE",
            "I2C_CONTROLLER_GENERATION_INVALID",
            "i2c_controller_handle_matches_descriptor",
            "i2c_controller_binding_is_stale",
        ):
            self.assertIn(token, self.text)

    def test_descriptor_keeps_acpi_and_backend_identity_separate(self):
        for token in (
            "pub struct I2cControllerDescriptor",
            "pub acpi_namespace_index: usize",
            "pub capabilities: I2cControllerCapabilities",
            "pub backend_instance: u32",
            "pub backend_ready: bool",
            "i2c_controller_descriptor_valid",
        ):
            self.assertIn(token, self.text)
        self.assertIn("backend_instance != I2C_CONTROLLER_BACKEND_INSTANCE_NONE", self.text)
        self.assertIn("backend_instance == I2C_CONTROLLER_BACKEND_INSTANCE_NONE", self.text)

    def test_acpi_binding_requires_same_controller_and_capabilities(self):
        for token in (
            "i2c_controller_can_host_acpi",
            "controller_namespace_index != (*descriptor).acpi_namespace_index",
            "connection_speed_hz > (*descriptor).capabilities.max_speed_hz",
            "capabilities.supports_10bit",
            "capabilities.supports_7bit",
            "(*binding).device_initiated",
        ):
            self.assertIn(token, self.text)

    def test_binding_carries_generation_and_connection_identity(self):
        for token in (
            "pub struct I2cControllerBinding",
            "pub resource_index: usize",
            "pub device_slot: usize",
            "pub resource_source_index: u8",
            "pub slave_address: u16",
            "pub connection_speed_hz: u32",
            "pub ten_bit_addressing: bool",
            "i2c_controller_bind_acpi",
        ):
            self.assertIn(token, self.text)

    def test_execution_requires_same_descriptor_generation_and_ready_backend(self):
        self.assertIn("i2c_controller_binding_matches_descriptor", self.text)
        self.assertIn("i2c_controller_binding_is_executable", self.text)
        self.assertIn("(*binding).generation != (*descriptor).generation", self.text)
        self.assertIn("(*binding).backend_ready &&", self.text)

    def test_cut_has_no_registry_or_physical_backend_side_effects(self):
        forbidden = (
            "static mut",
            "SpinLock",
            "spinlock_",
            "pci_read_",
            "pci_write_",
            "baken_mmio",
            "volatile_load",
            "volatile_store",
            "dma_",
            "x86_irq_",
            "sleep(",
            "polling",
            "import kernel::drivers::pci_bus::*;",
        )
        for token in forbidden:
            self.assertNotIn(token, self.text, token)


if __name__ == "__main__":
    unittest.main()
