from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_controller_registry.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cControllerRegistryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_registry_is_in_native_graph(self):
        self.assertIn("import kernel::drivers::i2c_controller_registry::*;", self.main)

    def test_registry_is_bounded_and_has_lifecycle_states(self):
        for token in (
            "pub const I2C_CONTROLLER_CAPACITY: usize = 16",
            "I2C_CONTROLLER_STATE_EMPTY",
            "I2C_CONTROLLER_STATE_ATTACHED",
            "I2C_CONTROLLER_STATE_ACTIVE",
            "I2C_CONTROLLER_STATE_FAILED",
            "I2C_CONTROLLER_STATE_DETACHED",
            "static mut I2C_CONTROLLER_RECORDS",
            "pub struct I2cControllerRecord",
        ):
            self.assertIn(token, self.text)

    def test_registry_owns_generation_safe_identity(self):
        for token in (
            "pub controller_id: u32",
            "pub generation: u32",
            "i2c_controller_registry_generation_next",
            "i2c_controller_registry_generation_for_id",
            "i2c_controller_registry_handle_is_current",
            "I2C_CONTROLLER_GENERATION_INVALID",
        ):
            self.assertIn(token, self.text)
        self.assertIn("I2C_CONTROLLER_RECORDS[slot].generation == generation", self.text)
        self.assertIn("i2c_controller_registry_generation_next(generation)", self.text)

    def test_attach_rejects_duplicate_live_acpi_owner(self):
        self.assertIn("i2c_controller_registry_attach", self.text)
        self.assertIn("acpi_namespace_index == AML_NAMESPACE_INVALID_INDEX", self.text)
        self.assertIn("i2c_controller_capabilities_valid(capabilities)", self.text)
        self.assertIn("I2C_CONTROLLER_RECORDS[duplicate].valid", self.text)
        self.assertIn("I2C_CONTROLLER_RECORDS[duplicate].acpi_namespace_index == acpi_namespace_index", self.text)

    def test_backend_publication_is_once_per_generation(self):
        self.assertIn("i2c_controller_registry_publish_backend", self.text)
        self.assertIn("state == I2C_CONTROLLER_STATE_ATTACHED", self.text)
        self.assertIn("!I2C_CONTROLLER_RECORDS[slot].backend_ready", self.text)
        self.assertIn(
            "I2C_CONTROLLER_RECORDS[slot].backend_instance == I2C_CONTROLLER_BACKEND_INSTANCE_NONE",
            self.text,
        )
        self.assertIn("I2C_CONTROLLER_RECORDS[slot].backend_instance = backend_instance", self.text)

    def test_activation_requires_ready_nonzero_backend(self):
        self.assertIn("i2c_controller_registry_activate", self.text)
        self.assertIn("I2C_CONTROLLER_RECORDS[slot].backend_ready &&", self.text)
        self.assertIn(
            "I2C_CONTROLLER_RECORDS[slot].backend_instance != I2C_CONTROLLER_BACKEND_INSTANCE_NONE",
            self.text,
        )
        self.assertIn("I2C_CONTROLLER_ACTIVE_COUNT += 1", self.text)

    def test_failed_state_revokes_backend_authorization(self):
        self.assertIn("i2c_controller_registry_mark_failed", self.text)
        self.assertIn("I2C_CONTROLLER_RECORDS[slot].state = I2C_CONTROLLER_STATE_FAILED", self.text)
        self.assertIn(
            "I2C_CONTROLLER_RECORDS[slot].backend_instance = I2C_CONTROLLER_BACKEND_INSTANCE_NONE",
            self.text,
        )
        self.assertIn("I2C_CONTROLLER_RECORDS[slot].backend_ready = false", self.text)

    def test_detach_clears_record_and_advances_generation(self):
        self.assertIn("i2c_controller_registry_detach", self.text)
        self.assertIn("I2C_CONTROLLER_RECORDS[slot].state = I2C_CONTROLLER_STATE_DETACHED", self.text)
        self.assertIn("I2C_CONTROLLER_RECORDS[slot].valid = false", self.text)
        self.assertIn("i2c_controller_registry_generation_next(generation)", self.text)
        self.assertIn("acpi_namespace_index = AML_NAMESPACE_INVALID_INDEX", self.text)

    def test_descriptor_snapshot_reuses_i2c_1d_contract(self):
        for token in (
            "i2c_controller_registry_descriptor",
            "I2cControllerDescriptor",
            "capabilities: I2C_CONTROLLER_RECORDS[slot].capabilities",
            "backend_instance: I2C_CONTROLLER_RECORDS[slot].backend_instance",
            "backend_ready: I2C_CONTROLLER_RECORDS[slot].backend_ready",
        ):
            self.assertIn(token, self.text)

    def test_locking_is_irq_safe_even_when_saved_flags_are_zero(self):
        self.assertIn("static mut I2C_CONTROLLER_REGISTRY_LOCK: SpinLock", self.text)
        self.assertGreaterEqual(self.text.count("let flags = x86_irq_save_disable();"), 9)
        self.assertGreaterEqual(self.text.count("x86_irq_restore(flags);"), 9)
        self.assertNotIn("if flags == 0", self.text)
        self.assertNotIn("flags != 0", self.text)

    def test_cut_has_no_physical_controller_or_hid_side_effects(self):
        forbidden = (
            "import kernel::drivers::pci_bus::*;",
            "pci_read_",
            "pci_write_",
            "baken_mmio",
            "volatile_load",
            "volatile_store",
            "dma_",
            "gpio_",
            "xhci_",
            "hid_",
            "sleep(",
            "aml_evaluate",
        )
        for token in forbidden:
            self.assertNotIn(token, self.text, token)


if __name__ == "__main__":
    unittest.main()
