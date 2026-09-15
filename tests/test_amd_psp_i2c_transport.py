import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / "kernel/src/drivers/amd_psp_i2c_transport.sotlas"
ARBITRATION = ROOT / "kernel/src/drivers/i2c_bus_arbitration.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class AmdPspI2cTransportContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = TRANSPORT.read_text(encoding="utf-8")

    def test_protocol_and_both_public_transport_kinds_are_explicit(self):
        for token in (
            "AMD_PSP_I2C_TRANSPORT_PLATFORM_ACCESS",
            "AMD_PSP_I2C_TRANSPORT_DOORBELL",
            "AMD_PSP_I2C_REQUEST_ACQUIRE",
            "AMD_PSP_I2C_REQUEST_RELEASE",
            "AMD_PSP_I2C_STATUS_BUS_BUSY",
            "AMD_PSP_I2C_STATUS_INVALID_PARAMETER",
            "payload_size: 12",
        ):
            self.assertIn(token, self.text)

    def test_provider_is_versioned_generation_safe_and_indirect(self):
        for token in (
            "pub submit: fn(u8, *mut AmdPspI2cRequest, u64) -> u32",
            "protocol_version != AMD_PSP_I2C_PROTOCOL_VERSION",
            "AMD_PSP_I2C_PROVIDER.generation != generation",
            "AMD_PSP_I2C_IN_FLIGHT",
            "provider.submit(request_type, &mut request, remaining_us)",
        ):
            self.assertIn(token, self.text)

    def test_retry_has_real_deadline_and_never_fails_open(self):
        for token in (
            "AMD_PSP_I2C_RETRY_COUNT: u32 = 400",
            "AMD_PSP_I2C_RETRY_DELAY_US: u64 = 25000",
            "AMD_PSP_I2C_REQUEST_TIMEOUT_US: u64 = 10000000",
            "if now >= deadline",
            "x86_timer_spin_wait_us",
            "return success",
        ):
            self.assertIn(token, self.text)
        self.assertNotIn("assume", self.text.lower())

    def test_arbitration_and_boot_graph_integrate_transport(self):
        arbitration = ARBITRATION.read_text(encoding="utf-8")
        self.assertIn("i2c_bus_arbitration_bind_psp_transport", arbitration)
        self.assertIn("AMD_PSP_I2C_REQUEST_RELEASE", arbitration)
        self.assertIn("import kernel::drivers::amd_psp_i2c_transport::*;",
                      MAIN.read_text(encoding="utf-8"))
        self.assertIn("amd_psp_i2c_transport_init();",
                      RUNTIME.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
