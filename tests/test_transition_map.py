#!/usr/bin/env python3
"""Guardrails dos mappings mínimos de transição para a futura troca de CR3."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRANSITION = ROOT / "kernel" / "src" / "memory" / "transition_map.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class TransitionMapTests(unittest.TestCase):
    def setUp(self):
        self.transition = TRANSITION.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_transition_range_keeps_physical_and_virtual_addresses_separate(self):
        self.assertIn("pub fn transition_map_range", self.transition)
        self.assertIn("virtual_address: u64", self.transition)
        self.assertIn("physical_address: u64", self.transition)
        self.assertIn("page_table_map_4k(arena, root, virtual_cursor, physical_cursor, clean_flags)", self.transition)

    def test_identity_mapping_is_only_explicit_wrapper(self):
        self.assertIn("pub fn transition_map_identity_range", self.transition)
        self.assertIn("return transition_map_range(arena, root, address, address, size, flags);", self.transition)

    def test_transition_range_aligns_arbitrary_image_or_stack_bounds(self):
        self.assertIn("x86_page_align_down(virtual_address)", self.transition)
        self.assertIn("x86_page_align_down(physical_address)", self.transition)
        self.assertIn("x86_page_align_up(last_byte + 1)", self.transition)
        self.assertIn("if last_byte < virtual_address", self.transition)
        self.assertIn("(virtual_address % X86_PAGE_SIZE) != (physical_address % X86_PAGE_SIZE)", self.transition)

    def test_transition_range_never_requests_huge_pages(self):
        self.assertIn("& ~X86_PTE_HUGE", self.transition)
        code = "\n".join(line.split("//", 1)[0] for line in self.transition.splitlines())
        self.assertNotIn("page_table_map_2m(", code)

    def test_transition_mapper_has_no_firmware_or_mmu_activation(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.transition.splitlines())
        for token in (
            "ExitBootServices", "AllocatePages", "GetMemoryMap",
            "__write_cr3", "x86_write_cr3", "__invlpg", "IA32_PAT",
            "pmm_alloc_page(", "pmm_alloc_pages(",
        ):
            self.assertNotIn(token, code)

    def test_hybrid_main_only_registers_transition_mapper(self):
        self.assertIn("import kernel::memory::transition_map::*;", self.main)
        self.assertNotIn("transition_map_identity_range(", self.main)
        self.assertNotIn("transition_map_range(", self.main)
        self.assertNotIn("x86_write_cr3(", self.main)


if __name__ == "__main__":
    unittest.main()
