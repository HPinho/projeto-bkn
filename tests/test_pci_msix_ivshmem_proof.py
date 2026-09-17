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
