import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HDA = ROOT / "kernel/src/drivers/hda_controller.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class HdaControllerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = HDA.read_text(encoding="utf-8")

    def test_discovers_standard_hda_class_without_cpu_generation_assumptions(self):
        for token in (
            "PCI_CLASS_MULTIMEDIA: u8 = 0x04",
            "PCI_SUBCLASS_HDA: u8 = 0x03",
            "(*device).revision_id",
            "controller_revision",
            "hda_vendor_family((*device).vendor_id)",
        ):
            self.assertIn(token, self.text)
        self.assertNotIn("cpuid", self.text.lower())

    def test_discovery_is_read_only_and_bar_validation_fails_closed(self):
        body = self.text.split("pub fn hda_discover_pci", 1)[1]
        for forbidden in ("pci_enable_device", "pci_enable_command_bits", "pci_write_config"):
            self.assertNotIn(forbidden, body)
        for token in (
            "!(*device).bars[0].is_io",
            "(*device).bars[0].base_address != 0",
            "HDA_STATE_UNUSABLE_BAR",
            "mmio_base: if usable",
        ):
            self.assertIn(token, self.text)

    def test_registry_is_bounded_and_integrated_nonfatally(self):
        self.assertIn("HDA_CONTROLLER_CAPACITY: usize = 8", self.text)
        self.assertIn("while index < pci_get_device_count()", self.text)
        self.assertIn("import kernel::drivers::hda_controller::*;", MAIN.read_text(encoding="utf-8"))
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("hda_discover_pci();", runtime)
        self.assertNotIn("if !hda_discover_pci", runtime)


if __name__ == "__main__":
    unittest.main()
