import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE = ROOT / "kernel/src/process/address_space.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
GDT = ROOT / "kernel/src/arch/x86_64/gdt.sotlas"
PAGING = ROOT / "kernel/src/arch/x86_64/paging.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_nvme_only.yml"


class ProcessAddressSpaceTests(unittest.TestCase):
    def setUp(self):
        self.text = SPACE.read_text(encoding="utf-8")

    def test_user_window_is_disjoint_from_runtime_window(self):
        self.assertIn("PROCESS_USER_BASE: u64 = 0x0000200000000000", self.text)
        self.assertIn("PROCESS_USER_WINDOW_SIZE: u64 = 0x00200000", self.text)
        self.assertIn("PROCESS_USER_PML4_INDEX: u16 = 64", self.text)
        active = (ROOT / "kernel/src/memory/active_page_tables.sotlas").read_text(encoding="utf-8")
        self.assertIn("VMM_RUNTIME_BASE: u64 = 0x0000400000000000", active)

    def test_existing_cpu_foundation_already_has_ring3_selectors_and_user_pte(self):
        gdt = GDT.read_text(encoding="utf-8")
        paging = PAGING.read_text(encoding="utf-8")
        self.assertIn("GDT_USER_CODE_SELECTOR: u16 = 0x1B", gdt)
        self.assertIn("GDT_USER_DATA_SELECTOR: u16 = 0x23", gdt)
        self.assertIn("gdt_make_code_descriptor(3)", gdt)
        self.assertIn("gdt_make_data_descriptor(3)", gdt)
        self.assertIn("X86_PTE_USER: u64 = 1 << 2", paging)

    def test_space_owns_exactly_four_private_page_table_pages(self):
        for token in (
            "PROCESS_ADDRESS_SPACE_TABLE_PAGES: u64 = 4",
            "pmm_alloc_pages(PROCESS_ADDRESS_SPACE_TABLE_PAGES)",
            "let pdpt = process_address_space_page(table_base + X86_PAGE_SIZE)",
            "let pd = process_address_space_page(table_base + (2 * X86_PAGE_SIZE))",
            "let pt = process_address_space_page(table_base + (3 * X86_PAGE_SIZE))",
        ):
            self.assertIn(token, self.text)

    def test_kernel_root_copy_fails_closed_on_user_accessible_inheritance(self):
        body = self.text.split("fn process_address_space_copy_kernel_root", 1)[1]
        body = body.split("fn process_address_space_link_user_tree", 1)[0]
        self.assertIn("if x86_pte_present(entry) { return false; }", body)
        self.assertIn("if x86_pte_present(entry) && (entry & X86_PTE_USER) != 0 { return false; }", body)
        self.assertIn("page_table_write_entry(destination, index, entry)", body)

    def test_user_bit_is_present_on_every_private_walk_level(self):
        body = self.text.split("fn process_address_space_link_user_tree", 1)[1]
        body = body.split("pub fn process_address_space_create", 1)[0]
        self.assertIn("X86_PTE_PRESENT | X86_PTE_WRITABLE | X86_PTE_USER", body)
        self.assertIn("page_table_write_entry(root, PROCESS_USER_PML4_INDEX, root_entry)", body)
        self.assertIn("page_table_write_entry(pdpt, 0, pdpt_entry)", body)
        self.assertIn("page_table_write_entry(pd, 0, pd_entry)", body)

    def test_user_leaf_policy_rejects_wx_and_never_maps_without_user_bit(self):
        body = self.text.split("pub fn process_address_space_map_user_page", 1)[1]
        body = body.split("pub fn process_address_space_unmap_user_page", 1)[0]
        self.assertIn("(writable && executable)", body)
        self.assertIn("let mut flags = X86_PTE_PRESENT | X86_PTE_USER", body)
        self.assertIn("if writable { flags |= X86_PTE_WRITABLE; }", body)
        self.assertIn("if !executable { flags |= X86_PTE_NX; }", body)
        self.assertIn("x86_pte_present(process_address_space_user_pte", body)

    def test_self_test_proves_same_virtual_address_has_distinct_backing(self):
        body = self.text.split("fn process_address_space_self_test()", 1)[1]
        body = body.split("pub fn process_address_space_activate_foundation", 1)[0]
        self.assertGreaterEqual(body.count("PROCESS_USER_BASE"), 6)
        self.assertIn("first_frame == second_frame", body)
        self.assertIn("x86_pte_address(first_pte) != first_frame", body)
        self.assertIn("x86_pte_address(second_pte) != second_frame", body)
        self.assertIn("0x1111222233334444", body)
        self.assertIn("0xAAAABBBBCCCCDDDD", body)
        self.assertIn("first_kernel != second_kernel", body)
        self.assertIn("(first_kernel & X86_PTE_USER) != 0", body)

    def test_destroy_requires_empty_user_pt_and_releases_only_owned_tables(self):
        body = self.text.split("pub fn process_address_space_destroy", 1)[1]
        body = body.split("fn process_address_space_self_test", 1)[0]
        self.assertIn("process_address_space_user_empty", body)
        self.assertIn("x86_read_cr3_raw() & X86_PAGE_ADDRESS_MASK", body)
        self.assertIn("pmm_free_pages(base, PROCESS_ADDRESS_SPACE_TABLE_PAGES)", body)
        self.assertNotIn("pmm_free_pages_lifo", body)

    def test_stage10_does_not_switch_cr3_or_claim_ring3(self):
        self.assertIn("x86_read_cr3_raw()", self.text)
        self.assertNotIn("x86_write_cr3_raw", self.text)
        self.assertNotIn("__write_cr3", self.text)
        self.assertNotIn("iretq", self.text.lower())
        self.assertNotIn("sysret", self.text.lower())

    def test_foundation_runs_after_bare_metal_gate_and_before_scheduler(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        process = body.index("process_address_space_activate_foundation()")
        marker = body.index("process_address_space_emit_ready_marker()")
        scheduler = body.index("scheduler_initialize()")
        self.assertLess(process, marker)
        self.assertLess(marker, scheduler)
        self.assertIn("import kernel::process::address_space::*;", runtime)

    def test_nvme_gate_requires_process_isolation_proof(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("'BAKEN:HEAP_READY'", workflow)
        self.assertIn("'BAKEN:PROCESS_ISOLATION_READY'", workflow)
        self.assertIn("'BAKEN:BARE_METAL_READY'", workflow)


if __name__ == "__main__":
    unittest.main()
