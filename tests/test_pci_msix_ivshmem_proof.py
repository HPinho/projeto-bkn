from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (ROOT / "tests/fixtures/df7e2/pci_msix_ivshmem_proof.sotlas").read_text(encoding="utf-8")
SERVER = (ROOT / "tools/scripts/ivshmem_test_server.py").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
RUNTIME = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")


class PciMsixIvshmemRuntimeProofContracts(unittest.TestCase):
    def _body(self, name: str) -> str:
        marker = f"fn {name}"
        start = FIXTURE.index(marker)
        end = FIXTURE.find("\n@system", start + len(marker))
        return FIXTURE[start:] if end == -1 else FIXTURE[start:end]

    def test_fixture_is_ci_only(self):
        self.assertNotIn("pci_msix_ivshmem_proof", MAIN)
        self.assertNotIn("pci_msix_ivshmem_runtime_proof", RUNTIME)
        self.assertIn("module kernel::drivers::pci_msix_ivshmem_proof;", FIXTURE)

    def test_uses_real_qemu_ivshmem_identity_and_bars(self):
        self.assertIn("PCI_MSIX_IVSHMEM_VENDOR_ID: u16 = 0x1AF4", FIXTURE)
        self.assertIn("PCI_MSIX_IVSHMEM_DEVICE_ID: u16 = 0x1110", FIXTURE)
        self.assertIn("PCI_MSIX_IVSHMEM_REG_BAR: u8 = 0", FIXTURE)
        self.assertIn("PCI_MSIX_IVSHMEM_MSIX_BAR: u8 = 1", FIXTURE)
        self.assertIn("PCI_MSIX_IVSHMEM_POSITION: u64 = 0x08", FIXTURE)
        self.assertIn("PCI_MSIX_IVSHMEM_DOORBELL: u64 = 0x0C", FIXTURE)

    def test_probe_reserves_before_any_runtime_programming(self):
        probe = self._body("pci_msix_ivshmem_probe")
        self.assertIn("pci_claim_bar(", probe)
        self.assertIn("pci_msix_reserve_single(", probe)
        self.assertNotIn("pci_msix_table_program_masked_single(", probe)
        self.assertNotIn("pci_msix_activate_single(", probe)
        self.assertNotIn("x86_mmio_write32", probe)

    def test_runtime_order_is_masked_program_activate_irq_then_unbind(self):
        body = self._body("pci_msix_ivshmem_runtime_proof")
        program = body.index("pci_msix_table_program_masked_single(")
        activate = body.index("pci_msix_activate_single(")
        doorbell = body.index("PCI_MSIX_IVSHMEM_DOORBELL")
        unbind = body.index("driver_unbind(device, driver)")
        self.assertLess(program, activate)
        self.assertLess(activate, doorbell)
        self.assertLess(doorbell, unbind)
        self.assertIn("PCI_MSIX_IVSHMEM_IRQ_COUNT", body)
        self.assertIn("pci_msix_arm_is_released(released)", body)

    def test_success_path_proves_no_leaks_or_stale_dispatch(self):
        body = self._body("pci_msix_ivshmem_runtime_proof")
        self.assertIn("resource_active_count() != before_resources", body)
        self.assertIn("irq_registry_active_count() != before_irqs", body)
        self.assertIn("irq_registry_dispatch(vector)", body)
        self.assertIn('"BAKEN:PCI_MSIX_IVSHMEM_READY\\n"', body)

    def test_proof_does_not_enable_intx_bus_master_or_rewrite_bars(self):
        runtime = self._body("pci_msix_ivshmem_runtime_proof")
        probe = self._body("pci_msix_ivshmem_probe")
        remove = self._body("pci_msix_ivshmem_remove")
        mutation_path = runtime + probe + remove
        forbidden = (
            "pci_enable_bus_master(",
            "pci_enable_memory(",
            "pci_write_command(",
            "pci_config_write32(",
            "pci_config_write16(",
            "pci_write_config32(",
        )
        for token in forbidden:
            self.assertNotIn(token, mutation_path)
        self.assertNotIn("pba_physical", mutation_path)

    def test_sizing_helper_only_quiesces_decode_master_and_restores_exact_command(self):
        body = self._body("pci_msix_ivshmem_measure_msix_bar")

        self.assertIn("let command_before = pci_config_read16(0, bus, slot_id, func, 0x04);", body)
        self.assertIn("PCI_COMMAND_IO_SPACE | PCI_COMMAND_MEMORY_SPACE | PCI_COMMAND_BUS_MASTER", body)
        self.assertIn("let active_bits = command_before & decode_master_mask;", body)
        self.assertIn("let quiescent = command_before & !decode_master_mask;", body)

        quiesce = body.index("pci_config_write16(0, bus, slot_id, func, 0x04, quiescent)")
        measure = body.index("pci_measure_owned_bar(device, driver, sizing_claim)")
        restore = body.rindex("pci_config_write16(0, bus, slot_id, func, 0x04, command_before)")
        restore_verify = body.rindex("pci_config_read16(0, bus, slot_id, func, 0x04) != command_before")
        self.assertLess(quiesce, measure)
        self.assertLess(measure, restore)
        self.assertLess(restore, restore_verify)

        # The helper may touch only the 16-bit PCI Command register around the real
        # BAR measurement. It must not rewrite BARs, MSI-X Table/PBA state, INTx,
        # or use any wider/raw config mutation primitive.
        forbidden = (
            "pci_config_write32(",
            "pci_write_config32(",
            "pci_enable_bus_master(",
            "pci_enable_memory(",
            "pci_write_command(",
            "x86_mmio_write32(",
            "pci_msix_table_program_masked_single(",
            "pci_msix_activate_single(",
            "pba_physical",
        )
        for token in forbidden:
            self.assertNotIn(token, body)

        self.assertEqual(body.count("pci_measure_owned_bar(device, driver, sizing_claim)"), 1)
        self.assertGreaterEqual(
            body.count("pci_config_write16(0, bus, slot_id, func, 0x04, command_before)"),
            2,
        )

    def test_remove_delegates_to_df7e1_teardown_before_bar_release(self):
        body = self._body("pci_msix_ivshmem_remove")
        disarm = body.index("pci_msix_disarm_and_release(")
        release_bar = body.index("pci_release_bar(msix_claim")
        self.assertLess(disarm, release_bar)
        self.assertIn("pci_msix_retry_quarantined_teardown(", body)
        self.assertIn("pci_msix_retry_quarantined_cleanup(", body)

    def test_test_server_implements_documented_protocol_order(self):
        version = SERVER.index("send_message(conn, 0)                 # protocol version")
        peer = SERVER.index("send_message(conn, 0)                 # this client's peer ID")
        shm = SERVER.index("send_message(conn, -1, shm_fd)")
        event = SERVER.index("send_message(conn, 0, event_fd)")
        self.assertLess(version, peer)
        self.assertLess(peer, shm)
        self.assertLess(shm, event)
        self.assertIn("SCM_RIGHTS", SERVER)
        self.assertIn("os.eventfd", SERVER)


if __name__ == "__main__":
    unittest.main()
