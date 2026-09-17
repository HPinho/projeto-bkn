#!/usr/bin/env python3
"""DF-7c: reserva e ownership de fonte/vetor MSI-X sem programacao de hardware."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = (ROOT / "kernel/src/device/types.sotlas").read_text(encoding="utf-8")
MANAGER = (ROOT / "kernel/src/device/resource_manager.sotlas").read_text(encoding="utf-8")
MSIX = (ROOT / "kernel/src/drivers/pci_msix.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsixReservationContracts(unittest.TestCase):
    def _body(self, name: str) -> str:
        return MSIX.split(f"pub fn {name}", 1)[1].split("\n@system", 1)[0]

    def _fn(self, name: str) -> str:
        return MSIX.split(f"fn {name}", 1)[1].split("\n@system", 1)[0]

    # 1. Taxonomia de recursos e exclusao mutua cruzada MSI <-> MSI-X
    def test_msix_resource_kind_and_cross_exclusion_with_msi(self):
        self.assertIn("RESOURCE_KIND_PCI_MSIX: u8 = 7", TYPES)
        self.assertIn("request.kind > RESOURCE_KIND_PCI_MSIX", MANAGER)
        valid = MANAGER.split("if request.kind == RESOURCE_KIND_PCI_MSI || request.kind == RESOURCE_KIND_PCI_MSIX", 1)[1].split("}", 1)[0]
        self.assertIn("request.length == 1", valid)
        self.assertIn("request.auxiliary == 0", valid)

        conflict = MANAGER.split("fn resource_requests_conflict", 1)[1].split("\n@system", 1)[0]
        self.assertIn("left.kind == RESOURCE_KIND_PCI_MSI && right.kind == RESOURCE_KIND_PCI_MSIX", conflict)
        self.assertIn("left.kind == RESOURCE_KIND_PCI_MSIX && right.kind == RESOURCE_KIND_PCI_MSI", conflict)
        self.assertIn("left.kind == RESOURCE_KIND_IRQ || left.kind == RESOURCE_KIND_PCI_MSI ||", conflict)
        self.assertIn("left.kind == RESOURCE_KIND_PCI_MSIX", conflict)

    # 2. Estrutura de dados da reserva MSI-X
    def test_msix_reservation_data_structures(self):
        self.assertIn("pub struct PciMsixReservation", MSIX)
        for field in (
            "pub source: ResourceHandle",
            "pub irq: IrqHandle",
            "pub vector: u16",
            "pub bdf: u32",
            "pub capability_offset: u16",
            "pub table_size: u16",
            "pub state: u8",
            "pub valid: bool",
        ):
            self.assertIn(field, MSIX)
        for state in (
            "PCI_MSIX_RESERVATION_INVALID",
            "PCI_MSIX_RESERVATION_READY",
            "PCI_MSIX_RESERVATION_QUARANTINED",
        ):
            self.assertIn(state, MSIX)

    # 3. Ordem de alocacao: source claim antes de IRQ register
    def test_reservation_claims_source_before_irq_and_irq_registry_owns_vector(self):
        body = self._body("pci_msix_reserve_single")
        self.assertIn("kind: RESOURCE_KIND_PCI_MSIX", body)
        self.assertIn("resource_claim(device, driver", body)
        self.assertIn("irq_registry_register(device, driver, descriptor)", body)
        self.assertLess(body.index("kind: RESOURCE_KIND_PCI_MSIX"), body.index("irq_registry_register"))
        self.assertIn("irq_registry_vector(irq)", body)
        self.assertIn("IRQ_DYNAMIC_VECTOR_FIRST", body)
        self.assertIn("IRQ_DYNAMIC_VECTOR_LAST", body)
        self.assertNotIn("kind: RESOURCE_KIND_IRQ", body)

    # 4. Exigencia de layout DF-7b valido
    def test_reservation_requires_valid_df7b_layout_matching_bdf_and_disabled(self):
        body = self._body("pci_msix_reserve_single")
        self.assertIn("!layout.valid", body)
        self.assertIn("layout.bdf != bdf", body)
        self.assertIn("layout.enabled", body)
        self.assertIn("capability.capability_offset != layout.capability_offset", body)
        self.assertIn("capability.table_size != layout.table_size", body)

    # 5. Tratamento de quiescencia e walker (MSI disabled se presente, MSI-X disabled)
    def test_reservation_handles_capability_walker_and_quiescence(self):
        body = self._body("pci_msix_reserve_single")
        self.assertIn("msi_cap = pci_msi_capability_probe", body)
        self.assertIn("msi_cap.valid && msi_cap.enabled", body)
        self.assertIn("!capability.valid || capability.enabled", body)
        self.assertIn("capability.table_size == 0", body)

    # 6. Proibicao estrita de programar hardware ou mapear Table/PBA
    def test_reservation_never_programs_hardware_or_maps_table_or_pba(self):
        body = self._body("pci_msix_reserve_single")
        for forbidden in (
            "pci_config_write",
            "pci_config_set16_bits",
            "x86_mmio_write",
            "active_page_tables_map",
            "lapic_",
            "ioapic_",
            "idt_set",
            "PCI_MSIX_CONTROL_ENABLE",
        ):
            self.assertNotIn(forbidden, body)

    # 7. Revalidacao TOCTOU antes de publicar estado READY
    def test_reservation_revalidates_device_source_and_capability_toctou(self):
        body = self._body("pci_msix_reserve_single")
        self.assertGreaterEqual(body.count("pci_msix_owned_device"), 2)
        self.assertGreaterEqual(body.count("pci_msix_capability_probe"), 2)
        self.assertIn("pci_msix_source_owned(source, bdf, device, driver)", body)
        self.assertIn("verify.capability_offset != capability.capability_offset", body)
        self.assertIn("verify.control != capability.control", body)
        self.assertIn("verify.table_size != capability.table_size", body)
        self.assertIn("verify.enabled", body)
        self.assertIn("state: PCI_MSIX_RESERVATION_READY", body)
        self.assertLess(body.index("verify.enabled"),
                        body.index("state: PCI_MSIX_RESERVATION_READY"))

    # 8. Cleanup seguro na ordem inversa: IRQ -> source sob comprovacao de quiescencia
    def test_cleanup_is_quiescence_gated_irq_then_source(self):
        body = self._fn("pci_msix_cleanup_unarmed_claims")
        proof = "pci_msix_quiescence_proven"
        irq = "irq_registry_unregister(remaining_irq, device, driver)"
        source = "resource_release(remaining_source, device, driver)"
        self.assertIn(proof, body)
        self.assertIn(irq, body)
        self.assertIn(source, body)
        self.assertLess(body.index(proof), body.index(irq))
        self.assertLess(body.index(irq), body.index(source))
        self.assertIn("pci_msix_quarantined_reservation", body)
        self.assertIn("remaining_irq = irq_invalid_handle()", body)

    # 9. Release de reserva nao armada
    def test_unarmed_release_returns_new_ownership_state_and_safe_cleanup(self):
        sig = MSIX.split("pub fn pci_msix_release_unarmed_reservation", 1)[1].split("{", 1)[0]
        body = self._body("pci_msix_release_unarmed_reservation")
        self.assertIn("-> PciMsixReservation", sig)
        self.assertIn("pci_msix_reservation_is_ready", body)
        self.assertIn("pci_msix_owned_device_for_release", body)
        self.assertIn("irq_registry_vector(reservation.irq) != reservation.vector", body)
        self.assertIn("pci_msix_quarantined_reservation", body)
        self.assertIn("pci_msix_cleanup_unarmed_claims", body)
        self.assertNotIn("irq_registry_unregister", body)
        self.assertNotIn("resource_release(", body)

    # 10. API de retry para quarentena
    def test_quarantined_cleanup_has_explicit_retry_contract(self):
        body = self._body("pci_msix_retry_quarantined_cleanup")
        self.assertIn("pci_msix_reservation_is_quarantined", body)
        self.assertIn("pci_msix_owned_device_for_release", body)
        self.assertIn("return reservation", body)
        self.assertIn("pci_msix_cleanup_unarmed_claims", body)

    # 11. Isolamento de bootstrap: boot do kernel intocado
    def test_bootstrap_isolation_and_no_boot_path_invocation(self):
        self.assertIn("import kernel::drivers::pci_msix::*;", MAIN)
        self.assertNotIn("pci_msix_reserve_single(", MAIN)
        self.assertEqual(MSIX.count("pub fn pci_msix_reserve_single"), 1)


if __name__ == "__main__":
    unittest.main()
