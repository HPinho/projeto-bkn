#!/usr/bin/env python3
"""Guardrails da composição das page tables pré-cutover."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "kernel/src/memory/transition_page_tables.sotlas"
FRAMEBUFFER = ROOT / "kernel/src/memory/transition_framebuffer_map.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class TransitionPageTableTests(unittest.TestCase):
    def setUp(self):
        self.text = TABLES.read_text(encoding="utf-8")
        self.framebuffer = FRAMEBUFFER.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_composer_allocates_and_zeros_one_root_first(self):
        body = self.text.split("pub fn transition_page_tables_build", 1)[1]
        self.assertIn("(*arena).next_page_index != 0", body)
        self.assertIn("let root = page_table_arena_alloc(arena);", body)
        self.assertIn("if !page_table_zero(root)", body)

    def test_composer_requires_direct_map_wx_image_framebuffer_and_guarded_stack(self):
        body = self.text.split("pub fn transition_page_tables_build", 1)[1]
        direct_pos = body.index("direct_map_build_from_uefi_ranges(")
        image_pos = body.index("transition_image_map_wx(arena, root, image, image_base)")
        framebuffer_pos = body.index("transition_framebuffer_map(arena, root, framebuffer)")
        stack_pos = body.index("transition_stack_map(arena, root, stack)")
        self.assertLess(direct_pos, image_pos)
        self.assertLess(image_pos, framebuffer_pos)
        self.assertLess(framebuffer_pos, stack_pos)
        self.assertIn("if !direct.valid", body)
        self.assertIn("if !image_map.valid", body)
        self.assertIn("if !framebuffer_map.valid", body)
        self.assertIn("if !stack_map.valid", body)
        self.assertNotIn("transition_image_map(arena, root, image)", body)

    def test_framebuffer_is_identity_rw_nx_and_conservative_uc(self):
        text = self.framebuffer
        self.assertIn("virtual_base: physical_base", text)
        for flag in (
            "X86_PTE_PRESENT", "X86_PTE_WRITABLE", "X86_PTE_NX",
            "X86_PTE_WRITE_THROUGH", "X86_PTE_CACHE_DISABLE",
        ):
            self.assertIn(flag, text)
        self.assertNotIn("X86_PTE_USER", text)

    def test_result_exposes_root_physical_without_activating_it(self):
        self.assertIn("root_physical: root.physical_address", self.text)
        self.assertIn("root_virtual: root.virtual_address", self.text)
        self.assertIn("framebuffer_pages: framebuffer_map.mapped_page_count", self.text)
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "__write_cr3", "x86_write_cr3", "__invlpg", "ExitBootServices",
            "GetMemoryMap", "AllocatePages", "BootServices", "pmm_alloc_page(",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_main_registers_composer_without_executing_it(self):
        self.assertIn("import kernel::memory::transition_page_tables::*;", self.main)
        self.assertNotIn("transition_page_tables_build(", self.main)
        self.assertNotIn("x86_mmu_activate_root(", self.main)


if __name__ == "__main__":
    unittest.main()
