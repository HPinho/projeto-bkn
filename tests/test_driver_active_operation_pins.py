#!/usr/bin/env python3
"""DF-6c guardrail: lifecycle e IRQ ownership devem ser pinados durante hardware ops."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVICES = (ROOT / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")
IRQS = (ROOT / "kernel/src/interrupts/registry.sotlas").read_text(encoding="utf-8")
MSI = (ROOT / "kernel/src/drivers/pci_msi.sotlas").read_text(encoding="utf-8")


class DriverActiveOperationPinTests(unittest.TestCase):
    def _body(self, text: str, name: str) -> str:
        return text.split(f"fn {name}", 1)[1].split("\n@system", 1)[0]

    def test_device_core_has_generation_safe_active_operation_pin(self):
        self.assertIn("static mut DEVICE_ACTIVE_OPERATIONS", DEVICES)
        begin = self._body(DEVICES, "device_core_begin_active_operation")
        end = self._body(DEVICES, "device_core_end_active_operation")
        self.assertIn("device_handle_live_locked(handle)", begin)
        self.assertIn("driver_handle_equal", begin)
        self.assertIn("DEVICE_STATE_ACTIVE", begin)
        self.assertIn("DEVICE_ACTIVE_OPERATIONS[slot] += 1", begin)
        self.assertIn("DEVICE_ACTIVE_OPERATIONS[slot] -= 1", end)

    def test_active_pin_blocks_lifecycle_exit(self):
        prepare = self._body(DEVICES, "device_core_prepare_unbind")
        failed = self._body(DEVICES, "device_core_mark_failed")
        detach = self._body(DEVICES, "device_core_detach")
        self.assertIn("DEVICE_ACTIVE_OPERATIONS[slot] == 0", prepare)
        self.assertIn("DEVICE_ACTIVE_OPERATIONS[slot] == 0", failed)
        self.assertIn("DEVICE_ACTIVE_OPERATIONS[slot] == 0", detach)

    def test_irq_external_pin_reuses_operations_in_flight(self):
        begin = self._body(IRQS, "irq_registry_begin_operation")
        end = self._body(IRQS, "irq_registry_end_operation")
        unregister = self._body(IRQS, "irq_registry_unregister")
        release_all = self._body(IRQS, "irq_registry_release_all")
        self.assertIn("IRQ_REGISTRY_STATE_ACTIVE", begin)
        self.assertIn("operations_in_flight += 1", begin)
        self.assertIn("operations_in_flight -= 1", end)
        self.assertIn("operations_in_flight == 0", unregister)
        self.assertIn("operations_in_flight == 0", release_all)

    def test_msi_pins_device_then_irq_and_unpins_irq_then_device(self):
        begin = self._body(MSI, "pci_msi_begin_operation_pins")
        end = self._body(MSI, "pci_msi_end_operation_pins")
        self.assertLess(begin.index("device_core_begin_active_operation"),
                        begin.index("irq_registry_begin_operation"))
        self.assertIn("device_core_end_active_operation", begin)
        self.assertLess(end.index("irq_registry_end_operation"),
                        end.index("device_core_end_active_operation"))

    def test_arm_acquires_pins_before_any_config_write(self):
        arm = self._body(MSI, "pci_msi_arm_single")
        self.assertIn("pci_msi_begin_operation_pins", arm)
        self.assertIn("pci_msi_end_operation_pins", arm)
        first_write = min(
            pos for pos in (
                arm.find("pci_config_write16"),
                arm.find("pci_config_write32"),
            ) if pos >= 0
        )
        self.assertLess(arm.index("pci_msi_begin_operation_pins"), first_write)
        self.assertGreater(arm.rindex("pci_msi_end_operation_pins"), first_write)


if __name__ == "__main__":
    unittest.main()
