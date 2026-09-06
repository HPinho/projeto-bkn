from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "kernel/src/memory/active_page_tables.sotlas"
INTRINSICS = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
FIXTURE = ROOT / "tools/scripts/extend_foundation_fixture.py"


class FoundationPatWriteCombiningGateTests(unittest.TestCase):
    def test_pat_intrinsic_programs_wc_slot_with_architectural_flush_sequence(self):
        text = INTRINSICS.read_text(encoding="utf-8")
        body = text.split("static inline bool __pat_install_wc(void)", 1)[1]
        body = body.split("static inline uint64_t __rdtsc", 1)[0]

        for token in (
            'uint32_t a = 1, b, c, d;',
            '"cpuid"',
            'if (!(d & (1u << 16))) return false;',
            'pushfq; popq %0; cli; mov %%cr0,%1; mov %%cr3,%2',
            '(cr0 | (1ull << 30)) & ~(1ull << 29)',
            'mov %0,%%cr0; wbinvd',
            '"c"(0x277)',
            'hi = (hi & 0x00ffffffu) | 0x01000000u;',
            'wrmsr; wbinvd',
            'mov %0,%%cr3; mov %1,%%cr0; pushq %2; popfq',
            'return (hi >> 24) == 1;',
        ):
            self.assertIn(token, body)

        # Slot 7 is the only PAT byte rewritten; bootstrap WB/UC slots remain intact.
        self.assertNotIn('lo =', body)
        self.assertIn('hi & 0x00ffffffu', body)

    def test_framebuffer_preflights_entire_identity_range_before_pat_change(self):
        text = ACTIVE.read_text(encoding="utf-8")
        body = text.split("pub fn active_framebuffer_write_combining", 1)[1]
        body = body.split("pub fn active_page_tables_resume", 1)[0]

        for token in (
            'base == 0 || size == 0 || size > 268435456',
            'let end = base + size;',
            'let first = x86_page_align_down(base);',
            'let limit = x86_page_align_up(end);',
            'if limit < end { return false; }',
            'x86_pte_address(pte) != page',
            '(pte & (X86_PTE_WRITABLE | X86_PTE_NX)) != (X86_PTE_WRITABLE | X86_PTE_NX)',
            'if !__pat_install_wc() { return false; }',
        ):
            self.assertIn(token, body)

        preflight = body.index('while page < limit')
        install = body.index('__pat_install_wc()')
        mutate = body.index('old | 0x98')
        self.assertLess(preflight, install)
        self.assertLess(install, mutate)

    def test_each_4k_framebuffer_pte_selects_pat_slot7_and_is_invalidated(self):
        text = ACTIVE.read_text(encoding="utf-8")
        body = text.split("pub fn active_framebuffer_write_combining", 1)[1]
        body = body.split("pub fn active_page_tables_resume", 1)[0]

        for token in (
            'old | 0x98',
            'x86_invlpg(page);',
            '(page_table_read_entry(leaf, x86_pt_index(page)) & 0x98) != 0x98',
            '__dma_fence();',
        ):
            self.assertIn(token, body)

        # 4K PAT=1, PCD=1, PWT=1 -> index 7. No huge-page rewrite is allowed here.
        self.assertNotIn('X86_PTE_HUGE', body)

    def test_post_cutover_orders_wc_after_nvme_and_proves_marker_before_final_j(self):
        text = POST.read_text(encoding="utf-8")
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        nvme = entry.index("foundation_nvme_probe()")
        wc = entry.index("active_framebuffer_write_combining(", nvme)
        marker = entry.index("x86_serial_write_stage_marker('%' as u8)", wc)
        final_j = entry.index("x86_serial_write_stage_marker('J' as u8)", marker)
        self.assertLess(nvme, wc)
        self.assertLess(wc, marker)
        self.assertLess(marker, final_j)

    def test_qemu_fixture_verifier_requires_pat_wc_runtime_proof(self):
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("'BAKEN:STEP=%'", text)
        self.assertIn("'BAKEN:STEP=J'", text)


if __name__ == "__main__":
    unittest.main()
