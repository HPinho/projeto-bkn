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

    def test_hardware_filter_rejects_non_i2c_intel_devices(self):
        # Invariante crítica P0: Intel NICs, GPUs, SATA, NVMe e xHCI NUNCA podem ser tratados como I2C
        self.assertIn("pub fn i2c_physical_identify_hardware(vendor_id: u16, device_id: u16, class_code: u8, subclass: u8) -> u8", self.text)
        self.assertIn("let is_valid_pci_serial_class = class_code == PCI_CLASS_SERIAL_BUS", self.text)
        self.assertIn("subclass == PCI_SUBCLASS_SERIAL_OTHER || subclass == PCI_SUBCLASS_SMBUS", self.text)
        self.assertIn("return I2C_HARDWARE_TYPE_UNKNOWN;", self.text)

    def test_pci_probing_checks_valid_bar_step(self):
        # Invariante crítica P0: pci_probe_bar retorna 1 (32-bit) ou 2 (64-bit)
        self.assertIn("let bar_step = pci_probe_bar(bus, slot, func, 0, &mut bar0);", self.text)
        self.assertIn("if bar_step >= 1 && bar0.base_address != 0 && !bar0.is_io", self.text)

    def test_hardware_initialization_and_backend_activation(self):
        # Invariante P0: driver inicializa o hardware e ativa o controlador no registry
        self.assertIn("i2c_dw_init(phys_base, 400000)", self.text)
        self.assertIn("i2c_controller_registry_publish_backend(", self.text)
        self.assertIn("i2c_controller_registry_activate(", self.text)
        self.assertIn("i2c_lpss_reset_release(phys_base)", self.text)

    def test_acpi_adr_matching(self):
        # Invariante P0: associação do PCI físico com o namespace ACPI via _ADR
        self.assertIn("pub fn i2c_physical_find_acpi_namespace(slot: u8, func: u8) -> usize", self.text)
        self.assertIn("let target_adr = ((slot as u64) << 16) | (func as u64);", self.text)

    def test_smp_per_controller_locking(self):
        # Invariante SMP: serialização exclusiva da transação por controlador físico
        self.assertIn("pub fn i2c_physical_lock_controller(backend_instance: u32) -> u64", self.text)
        self.assertIn("pub fn i2c_physical_unlock_controller(backend_instance: u32, flags: u64) -> void", self.text)
        self.assertIn("I2C_PHYSICAL_CONTROLLER_LOCKS", self.text)


if __name__ == "__main__":
    unittest.main()
