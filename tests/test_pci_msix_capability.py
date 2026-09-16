from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/pci_msix_capability.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class PciMsixCapabilityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_linked_but_not_invoked_from_boot(self):
        self.assertIn("import kernel::drivers::pci_msix_capability::*;", self.main)
        self.assertNotIn("pci_msix_capability_probe(", self.main)

    def test_capability_layout_matches_msix_standard_fields(self):
        for token in (
            "PCI_CAP_ID_MSIX",
            "PCI_MSIX_CONTROL_REL: u16 = 0x0002",
            "PCI_MSIX_TABLE_REL: u16 = 0x0004",
            "PCI_MSIX_PBA_REL: u16 = 0x0008",
            "PCI_MSIX_CONTROL_TABLE_SIZE_MASK: u16 = 0x07FF",
            "PCI_MSIX_CONTROL_FUNCTION_MASK: u16 = 0x4000",
            "PCI_MSIX_CONTROL_ENABLE: u16 = 0x8000",
            "PCI_MSIX_BIR_MASK: u32 = 0x00000007",
            "PCI_MSIX_OFFSET_MASK: u32 = 0xFFFFFFF8",
        ):
            self.assertIn(token, self.text)

    def test_table_size_and_spans_are_bounded(self):
        self.assertIn("PCI_MSIX_MAX_TABLE_ENTRIES: u16 = 2048", self.text)
        self.assertIn("PCI_MSIX_TABLE_ENTRY_BYTES: u64 = 16", self.text)
        self.assertIn("PCI_MSIX_PBA_WORD_BITS: u64 = 64", self.text)
        self.assertIn("PCI_MSIX_PBA_WORD_BYTES: u64 = 8", self.text)
        self.assertIn("table_offset + table_bytes <= table_offset", self.text)
        self.assertIn("pba_offset + pba_bytes <= pba_offset", self.text)

    def test_only_bar_zero_through_five_are_accepted(self):
        self.assertIn("PCI_MSIX_MAX_BIR: u8 = 5", self.text)
        self.assertIn("table_bir > PCI_MSIX_MAX_BIR", self.text)
        self.assertIn("pba_bir > PCI_MSIX_MAX_BIR", self.text)

    def test_snapshot_is_revalidated_before_publication(self):
        for token in (
            "let verify_header = pci_config_read16",
            "let verify_control = pci_config_read16",
            "let verify_table = pci_config_read32",
            "let verify_pba = pci_config_read32",
            "verify_header != header",
            "verify_control != control",
            "verify_table != table_raw",
            "verify_pba != pba_raw",
        ):
            self.assertIn(token, self.text)

    def test_df7a_is_strictly_read_only_and_passive(self):
        forbidden = (
            "pci_config_write",
            "pci_config_set16_bits",
            "resource_claim(",
            "irq_registry_register(",
            "active_runtime_map(",
            "active_page_tables_map_mmio",
            "lapic_eoi(",
            "pci_enable_memory(",
            "pci_enable_bus_master(",
        )
        for token in forbidden:
            self.assertNotIn(token, self.text)

    def test_conventional_config_space_bound_is_explicit(self):
        self.assertIn("PCI_MSIX_LAST_REL: u16 = 0x000B", self.text)
        self.assertIn("PCI_CONFIG_LEGACY_MAX_OFFSET - PCI_MSIX_LAST_REL", self.text)


if __name__ == "__main__":
    unittest.main()
