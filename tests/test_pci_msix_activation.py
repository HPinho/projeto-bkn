#!/usr/bin/env python3
"""DF-7e1 contracts: MSI-X activation/teardown ordering is transactional and fail-closed."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "kernel/src/drivers/pci_msix_activation.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsixActivationContracts(unittest.TestCase):
    def _fn(self, name: str) -> str:
        marker = f"fn {name}"
        start = SOURCE.index(marker)
        end = SOURCE.find("\n@system", start + len(marker))
        return SOURCE[start:] if end == -1 else SOURCE[start:end]

    def _pub(self, name: str) -> str:
        marker = f"pub fn {name}"
        start = SOURCE.index(marker)
        end = SOURCE.find("\n@system", start + len(marker))
        return SOURCE[start:] if end == -1 else SOURCE[start:end]

    def test_module_is_linked_but_not_invoked_from_boot(self):
        self.assertIn("import kernel::drivers::pci_msix_activation::*;", MAIN)
        self.assertNotIn("pci_msix_activate_single(", MAIN)
        self.assertNotIn("pci_msix_disarm_and_release(", MAIN)

    def test_activation_requires_df7d_masked_result_and_operation_pins(self):
        body = self._pub("pci_msix_activate_single")
        self.assertIn("pci_msix_table_program_is_masked(table)", body)
        self.assertIn("pci_msix_activation_begin_pins(", body)
        self.assertIn("pci_msix_layout_probe(", body)
        self.assertIn("pci_msix_activation_owned_active(", body)
        begin = self._fn("pci_msix_activation_begin_pins")
        self.assertIn("device_core_begin_active_operation", begin)
        self.assertIn("irq_registry_begin_operation", begin)

    def test_entry_mapping_uses_typed_uc_without_expanding_footprint(self):
        mapping = self._fn("pci_msix_activation_map_entry")
        self.assertIn("x86_page_align_down(entry_physical)", mapping)
        self.assertIn("x86_page_align_down(last_byte)", mapping)
        self.assertIn("first_page, 4096, MMIO_CACHE_POLICY_UC", mapping)
        self.assertIn("mmio_map_identity(&first_mapping)", mapping)
        self.assertIn("last_page != first_page", mapping)
        self.assertIn("last_page, 4096, MMIO_CACHE_POLICY_UC", mapping)
        self.assertIn("mmio_map_identity(&last_mapping)", mapping)
        self.assertNotIn("active_page_tables_map_mmio_identity_4k", mapping)

    def test_activation_order_is_global_mask_then_entry_unmask_then_function_unmask(self):
        body = self._pub("pci_msix_activate_single")
        enable = body.index("PCI_MSIX_CONTROL_ENABLE |")
        global_mask = body.index("PCI_MSIX_CONTROL_FUNCTION_MASK;", enable)
        write_enable = body.index("masked_enabled_control)", global_mask)
        entry_unmask = body.index("table.programmed.vector_control & ~PCI_MSIX_TABLE_VECTOR_MASK")
        final_unmask = body.index("masked_enabled_control & ~PCI_MSIX_CONTROL_FUNCTION_MASK")
        write_active = body.index("active_control)", final_unmask)
        self.assertLess(enable, global_mask)
        self.assertLess(global_mask, write_enable)
        self.assertLess(write_enable, entry_unmask)
        self.assertLess(entry_unmask, final_unmask)
        self.assertLess(final_unmask, write_active)

    def test_activation_readbacks_every_exposure_boundary(self):
        body = self._pub("pci_msix_activate_single")
        self.assertIn("masked_enabled.control != masked_enabled_control", body)
        self.assertIn("!masked_enabled.enabled || !masked_enabled.function_masked", body)
        self.assertIn("pci_msix_activation_snapshot_equal(", body)
        self.assertIn("active_capability.control != active_control", body)
        self.assertIn("!active_capability.enabled || active_capability.function_masked", body)

    def test_activation_rollback_returns_to_masked_disabled_df7d_state(self):
        body = self._fn("pci_msix_activation_restore_masked_state")
        function_mask = body.index("current.control | PCI_MSIX_CONTROL_FUNCTION_MASK")
        entry_mask = body.index("table.programmed.vector_control | PCI_MSIX_TABLE_VECTOR_MASK")
        restore_control = body.index("original_control)", entry_mask)
        self.assertLess(function_mask, entry_mask)
        self.assertLess(entry_mask, restore_control)
        self.assertIn("!restored.enabled", body)
        self.assertIn("table.programmed", body)

    def test_teardown_requires_unbinding_release_layout(self):
        body = self._fn("pci_msix_teardown_internal")
        self.assertIn("pci_msix_activation_owned_unbinding(", body)
        self.assertIn("pci_msix_release_layout_probe(", body)
        owner = self._fn("pci_msix_activation_owned_unbinding")
        self.assertIn("DEVICE_STATE_UNBINDING", owner)

    def test_teardown_order_is_global_mask_entry_mask_disable_restore_release(self):
        body = self._fn("pci_msix_teardown_internal")
        global_mask = body.index("capability.control | PCI_MSIX_CONTROL_FUNCTION_MASK")
        entry_mask = body.index("arm.table.programmed.vector_control | PCI_MSIX_TABLE_VECTOR_MASK")
        disable = body.index("function_masked_control & ~PCI_MSIX_CONTROL_ENABLE")
        restore_entry = body.index("pci_msix_teardown_restore_original_entry(arm)")
        restore_control = body.index("arm.original_control)", restore_entry)
        release = body.index("pci_msix_release_unarmed_reservation(", restore_control)
        self.assertLess(global_mask, entry_mask)
        self.assertLess(entry_mask, disable)
        self.assertLess(disable, restore_entry)
        self.assertLess(restore_entry, restore_control)
        self.assertLess(restore_control, release)

    def test_no_ownership_release_before_enable_zero_readback(self):
        body = self._fn("pci_msix_teardown_internal")
        source_off = body.index("disabled.enabled")
        release = body.index("pci_msix_release_unarmed_reservation(")
        retry_release = body.index("pci_msix_retry_quarantined_cleanup(")
        self.assertLess(source_off, release)
        self.assertLess(source_off, retry_release)

    def test_quarantine_has_explicit_retry_path(self):
        retry = self._pub("pci_msix_retry_quarantined_teardown")
        self.assertIn("PCI_MSIX_ARM_STATE_QUARANTINED", retry)
        self.assertIn("pci_msix_teardown_internal(", retry)
        teardown = self._fn("pci_msix_teardown_internal")
        self.assertIn("pci_msix_retry_quarantined_cleanup(", teardown)

    def test_df7e_does_not_touch_pba_intx_bus_master_or_bar_config(self):
        for forbidden in (
            "layout.pba_physical +",
            "x86_mmio_write32(layout.pba_physical",
            "ioapic_",
            "pci_enable_bus_master(",
            "pci_enable_memory(",
            "PCI_COMMAND_BUS_MASTER",
        ):
            self.assertNotIn(forbidden, SOURCE)

    def test_public_state_helpers_distinguish_armed_and_released(self):
        armed = self._pub("pci_msix_arm_is_armed")
        released = self._pub("pci_msix_arm_is_released")
        self.assertIn("PCI_MSIX_ARM_STATE_ARMED", armed)
        self.assertIn("PCI_MSIX_CONTROL_ENABLE", armed)
        self.assertIn("PCI_MSIX_TABLE_VECTOR_MASK", armed)
        self.assertIn("PCI_MSIX_ARM_STATE_RELEASED", released)
        self.assertIn("!arm.reservation.valid", released)


if __name__ == "__main__":
    unittest.main()
