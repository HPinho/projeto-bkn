#!/usr/bin/env python3
"""DF-6c: MSI single-vector deve ser programado transacionalmente e fail-closed."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MSI = (ROOT / "kernel/src/drivers/pci_msi.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsiProgrammingTests(unittest.TestCase):
    def _body(self, name: str) -> str:
        return MSI.split(f"fn {name}", 1)[1].split("\n@system", 1)[0]

    def test_module_is_reachable_but_not_invoked_by_boot(self):
        self.assertIn("import kernel::drivers::pci_msi::*;", MAIN)
        self.assertNotIn("pci_msi_arm_single(", MAIN)
        self.assertEqual(MSI.count("pub fn pci_msi_arm_single"), 1)

    def test_x86_msi_message_format_is_single_vector_fixed_edge(self):
        for token in (
            "PCI_MSI_MESSAGE_ADDRESS_BASE: u32 = 0xFEE00000",
            "PCI_MSI_MESSAGE_DEST_SHIFT: u32 = 12",
            "PCI_MSI_MESSAGE_DEST_MASK: u32 = 0x000FF000",
            "PCI_MSI_MESSAGE_DATA_VECTOR_MASK: u16 = 0x00FF",
            "PCI_MSI_MESSAGE_DATA_DELIVERY_MASK: u16 = 0x0700",
            "PCI_MSI_MESSAGE_DATA_RESERVED_MASK: u16 = 0x3800",
            "PCI_MSI_MESSAGE_DATA_LEVEL_ASSERT: u16 = 0x4000",
            "PCI_MSI_MESSAGE_DATA_TRIGGER_LEVEL: u16 = 0x8000",
        ):
            self.assertIn(token, MSI)
        arm = self._body("pci_msi_arm_single")
        self.assertIn("let destination = lapic_id();", arm)
        self.assertIn("(destination as u32) << PCI_MSI_MESSAGE_DEST_SHIFT", arm)
        self.assertIn("snapshot.data & PCI_MSI_MESSAGE_DATA_RESERVED_MASK", arm)
        self.assertIn("reservation.vector & PCI_MSI_MESSAGE_DATA_VECTOR_MASK", arm)
        self.assertNotIn("PCI_MSI_MESSAGE_DATA_DELIVERY_MASK |", arm)
        self.assertNotIn("PCI_MSI_MESSAGE_DATA_TRIGGER_LEVEL |", arm)
        self.assertNotIn("PCI_MSI_MESSAGE_DATA_LEVEL_ASSERT |", arm)

    def test_arm_requires_ready_active_lapic_and_live_ownership(self):
        body = self._body("pci_msi_arm_single")
        self.assertIn("pci_msi_reservation_is_ready(reservation)", body)
        self.assertIn("pci_msi_device_active(device, driver, reservation.bdf)", body)
        self.assertIn("lapic_is_ready()", body)
        self.assertGreaterEqual(body.count("pci_msi_reservation_owned"), 2)
        owned = self._body("pci_msi_reservation_owned")
        self.assertIn("reservation.state == PCI_MSI_RESERVATION_READY", owned)
        self.assertIn("pci_msi_source_owned", owned)
        self.assertIn("pci_msi_irq_owned", owned)
        source = self._body("pci_msi_source_owned")
        self.assertIn("resource_snapshot(reservation.source)", source)
        self.assertIn("RESOURCE_KIND_PCI_MSI", source)
        irq = self._body("pci_msi_irq_owned")
        self.assertIn("irq_registry_vector(reservation.irq) == reservation.vector", irq)

    def test_programming_is_serialized_and_mme_zero_before_payload(self):
        self.assertIn("static mut PCI_MSI_PROGRAM_LOCK", MSI)
        body = self._body("pci_msi_arm_single")
        self.assertIn("pci_msi_program_lock_irq", body)
        disabled = "let disabled_single = snapshot.control"
        low = "snapshot.message_address_low_offset"
        data = "snapshot.message_data_offset, data"
        enabled = "let enabled_single = disabled_single | PCI_MSI_CONTROL_ENABLE"
        self.assertIn("~PCI_MSI_CONTROL_ENABLE", body)
        self.assertIn("~PCI_MSI_CONTROL_MME_MASK", body)
        self.assertLess(body.index(disabled), body.index(low))
        self.assertLess(body.index(low), body.index(data))
        self.assertLess(body.index(data), body.index(enabled))
        self.assertIn("programmed.multiple_message_enable != 0", body)
        self.assertIn("armed.multiple_message_enable != 0", body)

    def test_32_and_64_bit_layouts_use_df6a_offsets(self):
        body = self._body("pci_msi_arm_single")
        self.assertIn("snapshot.message_address_low_offset", body)
        self.assertIn("if snapshot.address_64", body)
        self.assertIn("snapshot.message_address_high_offset", body)
        self.assertIn("snapshot.message_data_offset", body)
        snap = self._body("pci_msi_snapshot_config")
        self.assertIn("pci_msi_capability_probe", snap)
        self.assertIn("first.message_address_low_offset", snap)
        self.assertIn("first.message_address_high_offset", snap)
        self.assertIn("first.message_data_offset", snap)
        self.assertGreaterEqual(snap.count("pci_msi_capability_probe"), 2)

    def test_enable_is_last_programming_write_after_full_revalidation(self):
        body = self._body("pci_msi_arm_single")
        enable_decl = body.index("let enabled_single = disabled_single | PCI_MSI_CONTROL_ENABLE")
        enable_write = body.index("control_offset, enabled_single", enable_decl)
        self.assertLess(body.index("let programmed = pci_msi_capability_probe"), enable_decl)
        self.assertLess(body.index("pci_msi_raw_config_matches", body.index("let programmed")), enable_decl)
        self.assertLess(body.index("pci_msi_source_owned", body.index("let programmed")), enable_decl)
        self.assertLess(body.index("pci_msi_irq_owned", body.index("let programmed")), enable_decl)
        self.assertGreater(enable_write, body.index("snapshot.message_data_offset, data"))
        armed = body.index("let armed = pci_msi_capability_probe", enable_write)
        self.assertGreater(armed, enable_write)
        self.assertIn("!armed.enabled", body[armed:])

    def test_rollback_disables_first_restores_snapshot_and_verifies(self):
        body = self._body("pci_msi_restore_snapshot")
        disable = "let disabled = current.control & ~PCI_MSI_CONTROL_ENABLE"
        data = "snapshot.message_data_offset, snapshot.data"
        low = "snapshot.message_address_low_offset,"
        original_control = "snapshot.capability_offset + PCI_MSI_CONTROL_REL,\n                           snapshot.control"
        verify = "return pci_msi_raw_config_matches"
        for token in (disable, data, low, original_control, verify):
            self.assertIn(token, body)
        self.assertLess(body.index(disable), body.index(data))
        self.assertLess(body.index(data), body.index(low))
        self.assertLess(body.index(low), body.index(original_control))
        self.assertLess(body.index(original_control), body.index(verify))
        self.assertIn("snapshot.control & PCI_MSI_CONTROL_ENABLE", body)

    def test_uncertain_rollback_quarantines_without_releasing_ownership(self):
        failure = self._body("pci_msi_failure_after_write")
        self.assertIn("pci_msi_restore_snapshot", failure)
        self.assertIn("PCI_MSI_ARM_STATE_READY", failure)
        self.assertIn("pci_msi_quarantined_copy", failure)
        self.assertIn("PCI_MSI_ARM_STATE_QUARANTINED", failure)
        self.assertNotIn("irq_registry_unregister", MSI)
        self.assertNotIn("resource_release(", MSI)

    def test_df6c_does_not_change_legacy_irq_or_device_command_policy(self):
        for forbidden in (
            "PCI_COMMAND_INTX_DISABLE",
            "PCI_COMMAND_BUS_MASTER",
            "PCI_COMMAND_MEMORY_SPACE",
            "ioapic_",
            "idt_",
            "lapic_eoi",
            "irq_registry_register",
            "irq_registry_unregister",
            "resource_claim(",
            "resource_release(",
        ):
            self.assertNotIn(forbidden, MSI)


if __name__ == "__main__":
    unittest.main()
