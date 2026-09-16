#!/usr/bin/env python3
"""DF-6d1: teardown MSI deve ser source-off-first, generation-safe e fail-closed."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEARDOWN = (ROOT / "kernel/src/drivers/pci_msi_teardown.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsiTeardownTests(unittest.TestCase):
    def _body(self, name: str) -> str:
        return TEARDOWN.split(f"fn {name}", 1)[1].split("\n@system", 1)[0]

    def test_module_is_linked_but_not_invoked_by_boot(self):
        self.assertIn("import kernel::drivers::pci_msi_teardown::*;", MAIN)
        self.assertNotIn("pci_msi_disarm_and_release(", MAIN)
        self.assertEqual(TEARDOWN.count("pub fn pci_msi_disarm_and_release"), 1)

    def test_teardown_requires_armed_ready_and_unbinding_owner(self):
        body = self._body("pci_msi_disarm_and_release")
        self.assertIn("arm.state != PCI_MSI_ARM_STATE_ARMED", body)
        self.assertIn("pci_msi_reservation_is_ready(arm.reservation)", body)
        self.assertIn("pci_msi_teardown_owner_matches", body)
        owner = self._body("pci_msi_teardown_owner_matches")
        self.assertIn("owner.state != DEVICE_STATE_UNBINDING", owner)
        self.assertIn("RESOURCE_KIND_PCI_MSI", owner)
        self.assertIn("irq_registry_vector(reservation.irq) != reservation.vector", owner)

    def test_preflight_proves_exact_df6c_programming_before_write(self):
        body = self._body("pci_msi_disarm_and_release")
        expected = body.index("let expected_enabled")
        payload = body.index("pci_msi_teardown_programmed_payload_matches", expected)
        first_write = body.index("pci_config_write16", payload)
        self.assertLess(expected, payload)
        self.assertLess(payload, first_write)
        self.assertIn("!capability.enabled", body)
        self.assertIn("capability.multiple_message_enable != 0", body)
        self.assertIn("capability.control != expected_enabled", body)

    def test_source_is_disabled_before_restore_or_release(self):
        body = self._body("pci_msi_disarm_and_release")
        disable = body.index("let disabled = capability.control & ~PCI_MSI_CONTROL_ENABLE")
        write = body.index("pci_config_write16", disable)
        proof = body.index("let quiescent = pci_msi_capability_probe", write)
        restore = body.index("pci_msi_teardown_restore_original", proof)
        release = body.index("pci_msi_release_unarmed_reservation", restore)
        self.assertLess(disable, write)
        self.assertLess(write, proof)
        self.assertLess(proof, restore)
        self.assertLess(restore, release)
        self.assertIn("quiescent.enabled", body[proof:restore])

    def test_original_snapshot_is_restored_only_after_source_off(self):
        body = self._body("pci_msi_teardown_restore_original")
        self.assertIn("if !pci_msi_teardown_layout_matches(before, arm) || before.enabled", body)
        data = body.index("arm.original_data")
        high = body.index("arm.original_address_high")
        low = body.index("arm.original_address_low", high)
        control = body.index("arm.original_control", low)
        verify = body.index("let after = pci_msi_capability_probe", control)
        self.assertLess(data, high)
        self.assertLess(high, low)
        self.assertLess(low, control)
        self.assertLess(control, verify)
        self.assertIn("after.enabled", body[verify:])
        self.assertIn("after.control != arm.original_control", body[verify:])

    def test_any_uncertainty_preserves_ownership_in_quarantine(self):
        body = self._body("pci_msi_disarm_and_release")
        self.assertGreaterEqual(body.count("pci_msi_teardown_quarantined"), 5)
        quarantine = self._body("pci_msi_teardown_quarantined")
        self.assertIn("PCI_MSI_RESERVATION_QUARANTINED", quarantine)
        self.assertIn("source: reservation.source", quarantine)
        self.assertIn("irq: reservation.irq", quarantine)

    def test_release_is_delegated_to_df6b_after_positive_quiescence(self):
        body = self._body("pci_msi_disarm_and_release")
        self.assertIn("return pci_msi_release_unarmed_reservation", body)
        self.assertNotIn("irq_registry_unregister", TEARDOWN)
        self.assertNotIn("resource_release(", TEARDOWN)
        self.assertNotIn("resource_claim(", TEARDOWN)
        self.assertNotIn("irq_registry_register", TEARDOWN)

    def test_df6d1_does_not_expand_interrupt_or_command_policy(self):
        for forbidden in (
            "PCI_COMMAND_INTX_DISABLE",
            "PCI_COMMAND_BUS_MASTER",
            "PCI_COMMAND_MEMORY_SPACE",
            "ioapic_",
            "idt_",
            "lapic_eoi",
            "lapic_id(",
        ):
            self.assertNotIn(forbidden, TEARDOWN)

    def test_private_helpers_are_namespaced_for_current_c_backend(self):
        self.assertNotIn("fn pci_msi_source_owned", TEARDOWN)
        for name in (
            "pci_msi_teardown_quarantined",
            "pci_msi_teardown_owner_matches",
            "pci_msi_teardown_layout_matches",
            "pci_msi_teardown_programmed_payload_matches",
            "pci_msi_teardown_restore_original",
        ):
            self.assertEqual(TEARDOWN.count(f"fn {name}"), 1)


if __name__ == "__main__":
    unittest.main()
