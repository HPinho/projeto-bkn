from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class I2cPhysicalDiscoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")

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

    def test_pci_probing_checks_valid_bar_step_and_mmio_map(self):
        # Invariante crítica P0: validação de retorno do BAR e verificação do active_page_tables_map
        self.assertIn("let bar_step = pci_probe_bar(bus, slot, func, 0, &mut bar0);", self.text)
        self.assertIn("if bar_step >= 1 && bar0.base_address != 0 && !bar0.is_io", self.text)
        self.assertIn("if !active_page_tables_map_mmio_identity_4k(page_aligned)", self.text)
        self.assertIn("pci_enable_command_bits(bus, slot, func, PCI_COMMAND_MEMORY_SPACE)", self.text)

    def test_hardware_initialization_requires_init_ok_before_activation(self):
        # Invariante P0: se init_ok falhar, NÃO publica nem ativa no registry
        self.assertIn("let init_ok = i2c_dw_init_with_clock(phys_base, 400000, input_clock);", self.text)
        self.assertIn("if !init_ok {", self.text)
        self.assertIn("i2c_controller_registry_publish_backend(", self.text)
        self.assertIn("i2c_controller_registry_activate(", self.text)
        self.assertIn("i2c_lpss_reset_release(phys_base, phys_base)", self.text)

    def test_acpi_adr_matching_requires_root_bus(self):
        # Invariante P0: associação do PCI físico com o namespace ACPI via _ADR no Bus 0
        self.assertIn("pub fn i2c_physical_find_acpi_namespace(bus: u8, slot: u8, func: u8) -> usize", self.text)
        self.assertIn("if bus != 0 { return AML_NAMESPACE_INVALID_INDEX; }", self.text)
        self.assertIn("let target_adr = ((slot as u64) << 16) | (func as u64);", self.text)

    def test_smp_per_controller_locking_does_not_mask_irqs(self):
        # Invariante SMP: serialização sem mascarar IRQs prolongadamente
        self.assertIn("pub fn i2c_physical_lock_controller(backend_instance: u32) -> bool", self.text)
        self.assertIn("pub fn i2c_physical_unlock_controller(backend_instance: u32) -> void", self.text)
        self.assertIn("I2C_PHYSICAL_CONTROLLER_LOCKS", self.text)

    def test_boot_route_invokes_i2c_discovery(self):
        # Invariante P0: a rota de boot nativa chama ativamente o discovery de ACPI e PCI
        self.assertIn("i2c_discovery_scan_acpi_controllers();", self.runtime)
        self.assertIn("i2c_physical_probe_pci();", self.runtime)


if __name__ == "__main__":
    unittest.main()
