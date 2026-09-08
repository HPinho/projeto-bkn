"""Guardrails da coerencia TLB de address spaces de processo em SMP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TLB = ROOT / "kernel/src/memory/tlb_shootdown.sotlas"
REGISTRY = ROOT / "kernel/src/process/registry.sotlas"


class ProcessSmpTlbCoherenceTests(unittest.TestCase):
    def test_shootdown_carries_target_cr3_without_scheduler_dependency(self):
        text = TLB.read_text(encoding="utf-8")
        for token in (
            "static mut TLB_SHOOTDOWN_ROOT_LO: u32 = 0",
            "static mut TLB_SHOOTDOWN_ROOT_HI: u32 = 0",
            "fn tlb_shootdown_publish(address: u64, root: u64, generation: u32)",
            "pub fn tlb_shootdown_address_space_page(root: u64, address: u64) -> bool",
            "return tlb_shootdown_page(address, root);",
        ):
            self.assertIn(token, text)
        self.assertNotIn("scheduler::", text)
        self.assertNotIn("process::", text)

    def test_remote_handler_invalidates_only_matching_root_but_always_acks(self):
        text = TLB.read_text(encoding="utf-8")
        body = text.split("pub fn tlb_shootdown_handle_ipi() -> bool", 1)[1]
        self.assertIn("let target_root = target_root_lo | (target_root_hi << 32);", body)
        self.assertIn("let current_root = x86_read_cr3_raw() & X86_PAGE_ADDRESS_MASK;", body)
        conditional = "if target_root == 0 || current_root == target_root { x86_invlpg(address); }"
        self.assertIn(conditional, body)
        self.assertIn("x86_mmio_write32(tlb_u32_address(ack), generation);", body)
        self.assertLess(body.index(conditional), body.index("x86_mmio_write32(tlb_u32_address(ack), generation);"))

    def test_local_requester_uses_same_root_filter(self):
        text = TLB.read_text(encoding="utf-8")
        body = text.split("fn tlb_shootdown_page(address: u64, root: u64) -> bool", 1)[1]
        body = body.split("pub fn tlb_shootdown_kernel_page", 1)[0]
        self.assertIn("let current_root = x86_read_cr3_raw() & X86_PAGE_ADDRESS_MASK;", body)
        self.assertIn("if root == 0 || current_root == root { x86_invlpg(address); }", body)
        self.assertIn("xapic_ipi_send_fixed_all_excluding_self", body)
        self.assertIn("tlb_shootdown_wait_ack", body)

    def test_process_registry_publishes_user_pte_before_unlock(self):
        text = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("import kernel::memory::tlb_shootdown::*;", text)
        self.assertIn("!process_address_space_is_ready() || !tlb_shootdown_is_ready()", text)

        mapped = text.split("pub fn process_map_user_page", 1)[1].split("@system", 1)[0]
        self.assertIn("root = PROCESS_SPACES[slot].root_physical;", mapped)
        self.assertIn("tlb_shootdown_address_space_page(root, address)", mapped)
        self.assertIn("loop { x86_cpu_pause(); }", mapped)
        self.assertLess(mapped.index("process_address_space_map_user_page"), mapped.index("tlb_shootdown_address_space_page"))
        self.assertLess(mapped.index("tlb_shootdown_address_space_page"), mapped.index("process_registry_unlock_irq(flags)"))

        unmapped = text.split("pub fn process_unmap_user_page", 1)[1].split("@system", 1)[0]
        self.assertIn("root = PROCESS_SPACES[slot].root_physical;", unmapped)
        self.assertIn("if physical != 0 && !tlb_shootdown_address_space_page(root, address)", unmapped)
        self.assertLess(unmapped.index("process_address_space_unmap_user_page"), unmapped.index("tlb_shootdown_address_space_page"))
        self.assertLess(unmapped.index("tlb_shootdown_address_space_page"), unmapped.index("process_registry_unlock_irq(flags)"))


if __name__ == "__main__":
    unittest.main()
