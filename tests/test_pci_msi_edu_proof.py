#!/usr/bin/env python3
"""DF-6d2: QEMU EDU proof must exercise real MSI without entering production boot."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/df6d2/pci_msi_edu_proof.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_msi_edu.yml"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"

FIXTURE_TEXT = FIXTURE.read_text(encoding="utf-8")
WORKFLOW_TEXT = WORKFLOW.read_text(encoding="utf-8")
RUNTIME_TEXT = RUNTIME.read_text(encoding="utf-8")
MAIN_TEXT = MAIN.read_text(encoding="utf-8")


class PciMsiEduProofTests(unittest.TestCase):
    def _body(self, name: str) -> str:
        return FIXTURE_TEXT.split(f"fn {name}", 1)[1].split("\n@system", 1)[0]

    def test_production_graph_is_unchanged(self):
        self.assertNotIn("pci_msi_edu_proof", MAIN_TEXT)
        self.assertNotIn("pci_msi_edu_runtime_proof", RUNTIME_TEXT)
        self.assertIn(
            "tests/fixtures/df6d2/pci_msi_edu_proof.sotlas",
            WORKFLOW_TEXT,
        )
        self.assertIn(
            "kernel/src/drivers/pci_msi_edu_proof.sotlas",
            WORKFLOW_TEXT,
        )

    def test_fixture_targets_qemu_edu_contract(self):
        for token in (
            "PCI_MSI_EDU_VENDOR_ID: u16 = 0x1234",
            "PCI_MSI_EDU_DEVICE_ID: u16 = 0x11E8",
            "PCI_MSI_EDU_BAR_CLAIM_LENGTH: u64 = 4096",
            "PCI_MSI_EDU_IRQ_STATUS: u64 = 0x24",
            "PCI_MSI_EDU_IRQ_RAISE: u64 = 0x60",
            "PCI_MSI_EDU_IRQ_ACK: u64 = 0x64",
            "PCI_MSI_EDU_LIVENESS: u64 = 0x04",
        ):
            self.assertIn(token, FIXTURE_TEXT)

    def test_probe_is_passive_binding_only(self):
        body = self._body("pci_msi_edu_probe")
        self.assertIn("pci_claim_bar(", body)
        self.assertIn("pci_msi_reserve_single(", body)
        for forbidden in (
            "pci_msi_arm_single(",
            "pci_enable_memory(",
            "x86_mmio_write32(",
            "pci_config_write",
            "lapic_",
            "ioapic_",
        ):
            self.assertNotIn(forbidden, body)

    def test_arm_happens_only_after_active_bind(self):
        body = self._body("pci_msi_edu_runtime_proof")
        bind = body.index("let bound = driver_bind(device)")
        active = body.index("active.state != DEVICE_STATE_ACTIVE", bind)
        mapping = body.index("active_page_tables_map_mmio_identity_4k(base)", active)
        memory = body.index("pci_enable_memory(device, driver)", mapping)
        arm = body.index("pci_msi_arm_single(reservation, device, driver)", memory)
        trigger = body.index("PCI_MSI_EDU_IRQ_RAISE", arm)
        unbind = body.index("driver_unbind(device, driver)", trigger)
        self.assertLess(bind, active)
        self.assertLess(active, mapping)
        self.assertLess(mapping, memory)
        self.assertLess(memory, arm)
        self.assertLess(arm, trigger)
        self.assertLess(trigger, unbind)

    def test_isr_acknowledges_device_before_return(self):
        body = self._body("pci_msi_edu_irq_handler")
        read = body.index("PCI_MSI_EDU_IRQ_STATUS")
        ack = body.index("PCI_MSI_EDU_IRQ_ACK", read)
        count = body.index("PCI_MSI_EDU_IRQ_COUNT += 1", ack)
        self.assertLess(read, ack)
        self.assertLess(ack, count)

    def test_remove_uses_certified_teardown_before_bar_release(self):
        body = self._body("pci_msi_edu_remove")
        disarm = body.index("pci_msi_disarm_and_release")
        restore = body.index("pci_msi_edu_restore_memory_space", disarm)
        bar = body.index("pci_release_bar", restore)
        self.assertLess(disarm, restore)
        self.assertLess(restore, bar)
        self.assertIn("pci_msi_release_unarmed_reservation", body)
        self.assertIn("pci_msi_retry_quarantined_cleanup", body)

    def test_proof_has_no_parallel_interrupt_core_or_unsafe_policy(self):
        for forbidden in (
            "pci_enable_bus_master",
            "PCI_COMMAND_BUS_MASTER",
            "INTX",
            "intx",
            "ioapic_",
            "lapic_eoi",
            "idt_",
            "x86_sti_raw",
            "x86_cli_raw",
        ):
            self.assertNotIn(forbidden, FIXTURE_TEXT)

    def test_workflow_instruments_only_the_runner_and_requires_real_marker(self):
        for token in (
            "cp tests/fixtures/df6d2/pci_msi_edu_proof.sotlas",
            "import kernel::drivers::pci_msi_edu_proof::*;",
            "pci_msi_edu_runtime_proof()",
            "-device edu",
            "BAKEN:PCI_MSI_EDU_READY",
            "BAKEN:DRIVER_FOUNDATION_READY",
        ):
            self.assertIn(token, WORKFLOW_TEXT)


if __name__ == "__main__":
    unittest.main()
