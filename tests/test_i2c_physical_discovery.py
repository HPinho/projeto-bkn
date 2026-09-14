from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cPhysicalDiscoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_physical_discovery_is_in_native_graph(self):
        self.assertIn("import kernel::drivers::i2c_physical_discovery::*;", self.main)

    def test_hardware_types_and_constants(self):
        for token in (
            "pub const I2C_HARDWARE_TYPE_UNKNOWN: u8 = 0",
            "pub const I2C_HARDWARE_TYPE_DESIGNWARE: u8 = 1",
            "pub const I2C_HARDWARE_TYPE_INTEL_LPSS: u8 = 2",
            "pub const I2C_MAX_PHYSICAL_CONTROLLERS: usize = 8",
            "pub const PCI_CLASS_SERIAL_BUS: u8 = 0x0C",
            "pub const PCI_SUBCLASS_SMBUS: u8 = 0x05",
            "pub const PCI_SUBCLASS_SERIAL_OTHER: u8 = 0x80",
            "pub struct I2cPhysicalController",
        ):
            self.assertIn(token, self.text)

    def test_hardware_identification_intel_lpss(self):
        self.assertIn("pub fn i2c_physical_identify_hardware", self.text)
        self.assertIn("0x9D60", self.text)
        self.assertIn("0xA0C5", self.text)
        self.assertIn("I2C_HARDWARE_TYPE_INTEL_LPSS", self.text)
        self.assertIn("I2C_HARDWARE_TYPE_DESIGNWARE", self.text)

    def test_pci_probing_and_vmm_mapping(self):
        self.assertIn("pub fn i2c_physical_probe_pci", self.text)
        self.assertIn("pci_get_device_count()", self.text)
        self.assertIn("pci_probe_bar", self.text)
        self.assertIn("pci_enable_device", self.text)
        self.assertIn("active_page_tables_map_mmio_identity_4k", self.text)

    def test_thread_safety_and_mmio_getter(self):
        self.assertIn("pub fn i2c_physical_get_mmio_base", self.text)
        self.assertIn("x86_irq_save_disable()", self.text)
        self.assertIn("x86_irq_restore(flags)", self.text)
        self.assertIn("spinlock_lock(&mut I2C_PHYSICAL_LOCK)", self.text)
        self.assertIn("spinlock_unlock(&mut I2C_PHYSICAL_LOCK)", self.text)


if __name__ == "__main__":
    unittest.main()
