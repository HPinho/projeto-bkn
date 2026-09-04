#!/usr/bin/env python3
"""Guardrails do mapping temporário da imagem durante a troca futura de CR3."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMAGE_MAP = ROOT / "kernel/src/memory/transition_image_map.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class TransitionImageMapTests(unittest.TestCase):
    def setUp(self):
        self.text = IMAGE_MAP.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_layout_keeps_physical_and_virtual_addresses_separate(self):
        self.assertIn("physical_base: u64", self.text)
        self.assertIn("virtual_base: u64", self.text)
        self.assertIn("(physical_base % X86_PAGE_SIZE) != (virtual_base % X86_PAGE_SIZE)", self.text)
        self.assertIn("layout.virtual_base", self.text)
        self.assertIn("layout.physical_base", self.text)

    def test_mapping_is_explicitly_transitional_rwx(self):
        self.assertIn("TRANSITÓRIO", self.text)
        self.assertIn("W^X", self.text)
        self.assertIn("X86_PTE_PRESENT | X86_PTE_WRITABLE", self.text)
        # NX ausente significa executável durante a janela de transição.
        body = self.text.split("pub fn transition_image_map", 1)[1]
        self.assertNotIn("X86_PTE_NX", body)
        self.assertIn("transition_map_range(", body)

    def test_module_cannot_activate_mmu_or_depend_on_firmware(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "ExitBootServices", "GetMemoryMap", "AllocatePages", "__write_cr3",
            "x86_write_cr3", "__invlpg", "pmm_alloc_page(", "pmm_alloc_pages(",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_main_registers_but_does_not_execute_image_mapping(self):
        self.assertIn("import kernel::memory::transition_image_map::*;", self.main)
        self.assertNotIn("transition_image_layout(", self.main)
        self.assertNotIn("transition_image_map(", self.main)
        self.assertNotIn("x86_write_cr3(", self.main)


if __name__ == "__main__":
    unittest.main()
