from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_device.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cDeviceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_device_model_has_capacity_and_states(self):
        for token in (
            "pub const I2C_DEVICE_CAPACITY: usize = 32",
            "pub const I2C_DEVICE_ID_NONE: u32 = 0",
            "pub const I2C_DEVICE_GENERATION_INVALID: u32 = 0",
            "I2C_DEVICE_STATE_EMPTY",
            "I2C_DEVICE_STATE_ATTACHED",
            "I2C_DEVICE_STATE_ACTIVE",
            "I2C_DEVICE_STATE_SUSPENDED",
            "I2C_DEVICE_STATE_FAILED",
            "I2C_DEVICE_STATE_DETACHED",
            "pub struct I2cDeviceRecord",
            "static mut I2C_DEVICES",
        ):
            self.assertIn(token, self.text)

    def test_device_model_has_lifecycle_operations(self):
        for token in (
            "pub fn i2c_device_attach",
            "pub fn i2c_device_activate",
            "pub fn i2c_device_suspend",
            "pub fn i2c_device_detach",
            "i2c_device_generation_next",
        ):
            self.assertIn(token, self.text)

    def test_device_model_validates_address_and_controller(self):
        self.assertIn("i2c_address_valid", self.text)
        self.assertIn("controller_id == I2C_CONTROLLER_ID_NONE", self.text)
        self.assertIn("controller_generation == I2C_CONTROLLER_GENERATION_INVALID", self.text)

    def test_device_model_executes_transactions_via_protocol(self):
        self.assertIn("pub fn i2c_device_execute_transaction", self.text)
        self.assertIn("i2c_plan_transaction", self.text)
        self.assertIn("i2c_executor_prepare", self.text)
        self.assertIn("i2c_protocol_begin", self.text)
        self.assertIn("i2c_protocol_issue", self.text)
        self.assertIn("i2c_protocol_accept_event", self.text)
        self.assertIn("i2c_protocol_completion", self.text)

    def test_device_model_provides_write_read_and_combined_apis(self):
        self.assertIn("pub fn i2c_device_write", self.text)
        self.assertIn("pub fn i2c_device_read", self.text)
        self.assertIn("pub fn i2c_device_write_read", self.text)
        self.assertIn("I2C_DIRECTION_WRITE", self.text)
        self.assertIn("I2C_DIRECTION_READ", self.text)

    def test_device_model_is_thread_safe_with_irq_spinlock(self):
        self.assertIn("x86_irq_save_disable()", self.text)
        self.assertIn("x86_irq_restore(flags)", self.text)
        self.assertIn("spinlock_lock(&mut I2C_DEVICE_LOCK)", self.text)
        self.assertIn("spinlock_unlock(&mut I2C_DEVICE_LOCK)", self.text)


if __name__ == "__main__":
    unittest.main()
