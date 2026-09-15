import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARB = ROOT / "kernel/src/drivers/i2c_bus_arbitration.sotlas"
DEVICE = ROOT / "kernel/src/drivers/i2c_device.sotlas"
DISCOVERY = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"


class I2cBusArbitrationContract(unittest.TestCase):
    def test_psp_protocol_values_and_bounded_state_exist(self):
        text = ARB.read_text(encoding="utf-8")
        for token in ("I2C_PSP_REQUEST_ACQUIRE", "I2C_PSP_REQUEST_RELEASE",
                      "I2C_PSP_STATUS_BUS_BUSY", "I2C_PSP_RESERVATION_TIME_MS",
                      "I2C_PSP_REQUEST_RETRY_COUNT", "I2C_ARBITRATION_CAPACITY"):
            self.assertIn(token, text)

    def test_psp_without_transport_is_fail_closed(self):
        text = ARB.read_text(encoding="utf-8")
        register = text.split("pub fn i2c_bus_arbitration_register", 1)[1].split(
            "pub fn i2c_bus_arbitration_acquire", 1)[0]
        acquire = text.split("pub fn i2c_bus_arbitration_acquire", 1)[1].split(
            "pub fn i2c_bus_arbitration_release", 1)[0]
        self.assertIn("I2C_ARBITRATION_STATE_FAULTED", register)
        self.assertIn("mode == I2C_ARBITRATION_MODE_NONE", acquire)
        self.assertIn("I2C_ARBITRATION_MODE_AMD_PSP", acquire)
        self.assertIn("psp_transport_generation != 0", acquire)
        self.assertIn("amd_psp_i2c_transport_request", acquire)

    def test_psp_mailbox_runs_outside_arbitration_spinlock(self):
        text = ARB.read_text(encoding="utf-8")
        acquire = text.split("pub fn i2c_bus_arbitration_acquire", 1)[1].split(
            "pub fn i2c_bus_arbitration_release", 1)[0]
        self.assertLess(acquire.index("spinlock_unlock"),
                        acquire.index("amd_psp_i2c_transport_request"))
        self.assertIn("I2C_ARBITRATION_STATE_ACQUIRING", acquire)
        self.assertIn("I2C_ARBITRATION_STATE_FAULTED", acquire)

    def test_every_physical_transfer_acquires_and_releases_policy(self):
        text = DEVICE.read_text(encoding="utf-8")
        body = text.split("pub fn i2c_device_execute_transaction", 1)[1]
        acquire = body.index("i2c_bus_arbitration_acquire")
        transfer = body.index("i2c_dw_transfer")
        release = body.index("i2c_bus_arbitration_release", transfer)
        self.assertLess(acquire, transfer)
        self.assertLess(transfer, release)

    def test_backend_policy_precedes_registry_publication(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        pci = text.split("pub fn i2c_physical_probe_pci", 1)[1].split(
            "pub fn i2c_physical_controller_get", 1)[0]
        self.assertLess(pci.index("i2c_bus_arbitration_register"),
                        pci.index("i2c_controller_registry_publish_backend"))


if __name__ == "__main__":
    unittest.main()
