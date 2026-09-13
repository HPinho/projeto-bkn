from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/gpio_core.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class GpioCoreContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_gpio_core_has_capacity_and_states(self):
        for token in (
            "pub const GPIO_MAX_CONNECTIONS: usize = 32",
            "pub const GPIO_CONNECTION_ID_NONE: u32 = 0",
            "pub const GPIO_GENERATION_INVALID: u32 = 0",
            "GPIO_PIN_STATE_FREE",
            "GPIO_PIN_STATE_CONFIGURED",
            "GPIO_PIN_STATE_ACTIVE",
            "GPIO_PIN_STATE_MASKED",
            "GPIO_PIN_STATE_DETACHED",
            "pub struct GpioInterruptConnection",
            "static mut GPIO_CONNECTIONS",
        ):
            self.assertIn(token, self.text)

    def test_gpio_core_supports_polarity_and_trigger(self):
        for token in (
            "pub const GPIO_POLARITY_ACTIVE_HIGH: u8 = 0",
            "pub const GPIO_POLARITY_ACTIVE_LOW: u8 = 1",
            "pub const GPIO_POLARITY_ACTIVE_BOTH: u8 = 2",
            "pub const GPIO_TRIGGER_LEVEL: u8 = 0",
            "pub const GPIO_TRIGGER_EDGE: u8 = 1",
        ):
            self.assertIn(token, self.text)

    def test_gpio_core_registers_from_acpi(self):
        self.assertIn("pub fn gpio_connection_register_from_acpi", self.text)
        self.assertIn("aml_i2c_decode_gpio_int", self.text)
        self.assertIn("aml_i2c_resolve_resource_source", self.text)
        self.assertIn("target_device_id", self.text)
        self.assertIn("target_generation", self.text)

    def test_gpio_core_manages_lifecycle_and_masking(self):
        self.assertIn("pub fn gpio_connection_unregister", self.text)
        self.assertIn("pub fn gpio_connection_mask", self.text)
        self.assertIn("pub fn gpio_connection_unmask", self.text)
        self.assertIn("gpio_generation_next(generation)", self.text)

    def test_gpio_core_signals_and_consumes_pending_interrupts(self):
        self.assertIn("pub fn gpio_connection_signal", self.text)
        self.assertIn("pub fn gpio_connection_consume_pending", self.text)
        self.assertIn("pub fn gpio_connection_is_pending", self.text)
        self.assertIn("interrupt_count += 1", self.text)

    def test_gpio_core_is_thread_safe_with_irq_spinlock(self):
        self.assertIn("x86_irq_save_disable()", self.text)
        self.assertIn("x86_irq_restore(flags)", self.text)
        self.assertIn("spinlock_lock(&mut GPIO_CORE_LOCK)", self.text)
        self.assertIn("spinlock_unlock(&mut GPIO_CORE_LOCK)", self.text)


if __name__ == "__main__":
    unittest.main()
