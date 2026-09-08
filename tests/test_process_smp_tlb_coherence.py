"""Guardrails da coerencia TLB de address spaces de processo em SMP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TLB = ROOT / "kernel/src/memory/tlb_shootdown.sotlas"
REGISTRY = ROOT / "kernel/src/process/registry.sotlas"
SPACE = ROOT / "kernel/src/process/address_space.sotlas"


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

    def test_process_registry_pins_lifetime_but_releases_lock_before_shootdown(self):
        text = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("import kernel::memory::tlb_shootdown::*;", text)
        self.assertIn("!process_address_space_is_ready() || !tlb_shootdown_is_ready()", text)

        for name, mutation in (
            ("map", "process_address_space_map_user_page"),
            ("remap", "process_address_space_remap_user_page"),
            ("unmap", "process_address_space_unmap_user_page"),
        ):
            body = text.split(f"pub fn process_{name}_user_page", 1)[1].split("@system", 1)[0]
            self.assertIn("root = PROCESS_SPACES[slot].root_physical;", body)
            self.assertIn("process_retain_locked(pid)", body)
            self.assertIn(mutation, body)
            self.assertIn("tlb_shootdown_address_space_page(root, address)", body)
            self.assertIn("process_release(pid)", body)
            self.assertLess(body.index("process_retain_locked(pid)"), body.index(mutation))
            self.assertLess(body.index(mutation), body.index("process_registry_unlock_irq(flags)"))
            self.assertLess(body.index("process_registry_unlock_irq(flags)"),
                            body.index("tlb_shootdown_address_space_page(root, address)"))
            self.assertLess(body.index("tlb_shootdown_address_space_page(root, address)"),
                            body.index("process_release(pid)"))

    def test_remap_replaces_one_present_user_leaf_and_returns_old_frame(self):
        text = SPACE.read_text(encoding="utf-8")
        body = text.split("pub fn process_address_space_remap_user_page", 1)[1].split(
            "pub fn process_address_space_unmap_user_page", 1
        )[0]
        self.assertIn("(writable && executable)", body)
        self.assertIn("if !x86_pte_present(old) { return 0; }", body)
        self.assertIn("let mut flags = X86_PTE_PRESENT | X86_PTE_USER", body)
        self.assertIn("page_table_write_entry(pt, index, desired)", body)
        self.assertIn("return x86_pte_address(old);", body)


if __name__ == "__main__":
    unittest.main()
