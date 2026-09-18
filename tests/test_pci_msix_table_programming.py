#!/usr/bin/env python3
"""DF-7d contracts: masked MSI-X Table entry programming stays fail-closed."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TABLE = (ROOT / "kernel/src/drivers/pci_msix_table.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsixTableProgrammingContracts(unittest.TestCase):
    def _fn(self, name: str) -> str:
        marker = f"fn {name}"
        start = TABLE.index(marker)
        end = TABLE.find("\n@system", start + len(marker))
        if end == -1:
            return TABLE[start:]
        return TABLE[start:end]

    def _pub(self, name: str) -> str:
        marker = f"pub fn {name}"
        start = TABLE.index(marker)
        end = TABLE.find("\n@system", start + len(marker))
        if end == -1:
            return TABLE[start:]
        return TABLE[start:end]

    def test_module_is_linked_but_not_invoked_from_boot(self):
        self.assertIn("import kernel::drivers::pci_msix_table::*;", MAIN)
        self.assertNotIn("pci_msix_table_program_masked_single(", MAIN)
        self.assertEqual(TABLE.count("pub fn pci_msix_table_program_masked_single"), 1)

    def test_entry_model_is_exactly_four_dwords_and_mask_bit(self):
        for token in (
            "PCI_MSIX_TABLE_ENTRY_SIZE: u64 = 16",
            "PCI_MSIX_TABLE_ADDRESS_LOW_REL: u64 = 0",
            "PCI_MSIX_TABLE_ADDRESS_HIGH_REL: u64 = 4",
            "PCI_MSIX_TABLE_MESSAGE_DATA_REL: u64 = 8",
            "PCI_MSIX_TABLE_VECTOR_CONTROL_REL: u64 = 12",
            "PCI_MSIX_TABLE_VECTOR_MASK: u32 = 1",
        ):
            self.assertIn(token, TABLE)

    def test_programming_requires_active_owned_reservation_and_operation_pins(self):
        body = self._pub("pci_msix_table_program_masked_single")
        self.assertIn("pci_msix_reservation_is_ready(reservation)", body)
        self.assertIn("DEVICE_STATE_ACTIVE", self._fn("pci_msix_table_device_active"))
        self.assertIn("pci_msix_table_begin_operation_pins", body)
        begin = self._fn("pci_msix_table_begin_operation_pins")
        self.assertIn("device_core_begin_active_operation", begin)
        self.assertIn("irq_registry_begin_operation", begin)
        end = self._fn("pci_msix_table_end_operation_pins")
        self.assertLess(end.index("irq_registry_end_operation"), end.index("device_core_end_active_operation"))

    def test_live_layout_and_source_vector_ownership_are_revalidated(self):
        body = self._pub("pci_msix_table_program_masked_single")
        self.assertGreaterEqual(body.count("pci_msix_layout_probe("), 3)
        self.assertGreaterEqual(body.count("pci_msix_table_reservation_owned"), 3)
        owned = self._fn("pci_msix_table_reservation_owned")
        self.assertIn("pci_msix_table_source_owned", owned)
        self.assertIn("pci_msix_table_irq_owned", owned)
        source = self._fn("pci_msix_table_source_owned")
        self.assertIn("RESOURCE_KIND_PCI_MSIX", source)
        irq = self._fn("pci_msix_table_irq_owned")
        self.assertIn("irq_registry_vector(reservation.irq) == reservation.vector", irq)

    def test_quiescence_requires_both_interrupt_models_off_and_memory_decode_on(self):
        quiet = self._fn("pci_msix_table_quiescent")
        self.assertIn("pci_msi_capability_probe", quiet)
        self.assertIn("msi.valid && msi.enabled", quiet)
        self.assertIn("pci_msix_capability_probe", quiet)
        self.assertIn("msix.enabled", quiet)
        self.assertIn("PCI_COMMAND_MEMORY_SPACE", quiet)
        self.assertNotIn("pci_enable_memory", TABLE)
        self.assertNotIn("pci_enable_bus_master", TABLE)

    def test_entry_bounds_and_page_straddle_mapping_are_fail_closed(self):
        address = self._fn("pci_msix_table_entry_address")
        self.assertIn("entry_index >= layout.table_size", address)
        self.assertIn("PCI_MSIX_TABLE_ENTRY_SIZE > layout.table_bytes - offset", address)
        self.assertIn("address < layout.table_physical", address)
        mapping = self._fn("pci_msix_table_map_entry")
        self.assertIn("x86_page_align_down(entry_physical)", mapping)
        self.assertIn("x86_page_align_down(last_byte)", mapping)
        self.assertIn("mmio_describe_identity(", mapping)
        self.assertIn("first_page, 4096, MMIO_CACHE_POLICY_UC", mapping)
        self.assertIn("mmio_map_identity(&first_mapping)", mapping)
        self.assertIn("last_page != first_page", mapping)
        self.assertIn("last_page, 4096, MMIO_CACHE_POLICY_UC", mapping)
        self.assertIn("mmio_map_identity(&last_mapping)", mapping)
        self.assertNotIn("active_page_tables_map_mmio_identity_4k", mapping)

    def test_mapping_happens_before_irq_disabled_program_lock(self):
        body = self._pub("pci_msix_table_program_masked_single")
        self.assertLess(body.index("pci_msix_table_map_entry(entry_physical)"),
                        body.index("pci_msix_table_program_lock_irq"))
        lock = self._fn("pci_msix_table_program_lock_irq")
        self.assertIn("x86_irq_save_disable", lock)
        self.assertIn("spinlock_lock(&mut PCI_MSIX_TABLE_PROGRAM_LOCK)", lock)

    def test_mask_is_written_and_read_back_before_payload(self):
        body = self._pub("pci_msix_table_program_masked_single")
        mask_write = body.index("PCI_MSIX_TABLE_VECTOR_CONTROL_REL, masked_control")
        mask_read = body.index("PCI_MSIX_TABLE_VECTOR_CONTROL_REL) != masked_control")
        address_write = body.index("PCI_MSIX_TABLE_ADDRESS_LOW_REL, address_low")
        data_write = body.index("PCI_MSIX_TABLE_MESSAGE_DATA_REL, message_data")
        self.assertLess(mask_write, mask_read)
        self.assertLess(mask_read, address_write)
        self.assertLess(address_write, data_write)
        self.assertIn("PCI_MSIX_TABLE_PROGRAMMED_MASKED", body)

    def test_xapic_payload_is_fixed_edge_single_vector(self):
        body = self._pub("pci_msix_table_program_masked_single")
        for token in (
            "PCI_MSIX_MESSAGE_ADDRESS_BASE: u32 = 0xFEE00000",
            "PCI_MSIX_MESSAGE_DEST_SHIFT: u32 = 12",
            "PCI_MSIX_MESSAGE_DEST_MASK: u32 = 0x000FF000",
            "PCI_MSIX_MESSAGE_DATA_VECTOR_MASK: u32 = 0x000000FF",
            "let destination = lapic_id()",
            "let address_high: u32 = 0",
            "reservation.vector as u32",
        ):
            self.assertIn(token, TABLE if token.startswith("PCI_") else body)

    def test_readback_covers_full_entry_and_keeps_vector_mask_set(self):
        snapshot = self._fn("pci_msix_table_snapshot")
        for token in (
            "PCI_MSIX_TABLE_ADDRESS_LOW_REL",
            "PCI_MSIX_TABLE_ADDRESS_HIGH_REL",
            "PCI_MSIX_TABLE_MESSAGE_DATA_REL",
            "PCI_MSIX_TABLE_VECTOR_CONTROL_REL",
        ):
            self.assertIn(token, snapshot)
        body = self._pub("pci_msix_table_program_masked_single")
        self.assertIn("pci_msix_table_snapshot_equal(readback, programmed)", body)
        self.assertIn("(readback.vector_control & PCI_MSIX_TABLE_VECTOR_MASK) == 0", body)

    def test_failure_after_first_write_rolls_back_or_quarantines(self):
        rollback = self._fn("pci_msix_table_restore_entry")
        first = rollback.index("PCI_MSIX_TABLE_VECTOR_CONTROL_REL, masked_control")
        low = rollback.index("PCI_MSIX_TABLE_ADDRESS_LOW_REL, original.address_low")
        high = rollback.index("PCI_MSIX_TABLE_ADDRESS_HIGH_REL, original.address_high")
        data = rollback.index("PCI_MSIX_TABLE_MESSAGE_DATA_REL, original.message_data")
        last = rollback.rindex("original.vector_control")
        self.assertLess(first, low)
        self.assertLess(low, high)
        self.assertLess(high, data)
        self.assertLess(data, last)
        failure = self._fn("pci_msix_table_failure_after_write")
        self.assertIn("PCI_MSIX_TABLE_PROGRAM_READY", failure)
        self.assertIn("pci_msix_table_quarantined_copy", failure)
        self.assertIn("PCI_MSIX_TABLE_PROGRAM_QUARANTINED", failure)

    def test_df7d_does_not_activate_msix_or_touch_pba_intx_or_config_writes(self):
        for forbidden in (
            "pci_config_write",
            "pci_config_set16_bits",
            "PCI_MSIX_CONTROL_ENABLE",
            "PCI_MSIX_CONTROL_FUNCTION_MASK",
            "pci_enable_memory(",
            "pci_enable_bus_master(",
            "lapic_eoi(",
            "ioapic_",
            "idt_set",
            "resource_release(",
            "irq_registry_unregister(",
        ):
            self.assertNotIn(forbidden, TABLE)
        self.assertNotIn("layout.pba_physical +", TABLE)
        self.assertNotIn("active_page_tables_map_mmio_identity_4k(layout.pba_physical", TABLE)
        self.assertNotIn("mmio_describe_identity(layout.pba_physical", TABLE)


if __name__ == "__main__":
    unittest.main()
