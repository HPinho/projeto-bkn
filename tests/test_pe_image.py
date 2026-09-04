#!/usr/bin/env python3
"""Guardrails do parser PE32+ usado para hardening W^X."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PE = ROOT / "kernel/src/memory/pe_image.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class PeImageTests(unittest.TestCase):
    def setUp(self):
        self.text = PE.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_parser_requires_amd64_pe32_plus(self):
        for token in (
            "PE_DOS_MAGIC: u16 = 0x5A4D",
            "PE_SIGNATURE: u32 = 0x00004550",
            "PE_MACHINE_AMD64: u16 = 0x8664",
            "PE32_PLUS_MAGIC: u16 = 0x020B",
        ):
            self.assertIn(token, self.text)
        self.assertIn("pe_read_u16(base, loaded_size, 0) != PE_DOS_MAGIC", self.text)
        self.assertIn("pe_read_u32(base, loaded_size, pe_offset) != PE_SIGNATURE", self.text)
        self.assertIn("!= PE_MACHINE_AMD64", self.text)
        self.assertIn("!= PE32_PLUS_MAGIC", self.text)

    def test_parser_bounds_every_header_and_section_table(self):
        self.assertIn("fn pe_range_valid", self.text)
        self.assertIn("loaded_end <= image_base", self.text)
        self.assertIn("section_count > PE_MAX_SECTION_COUNT", self.text)
        self.assertIn("!pe_range_valid(loaded_size, optional_offset, optional_size)", self.text)
        self.assertIn("!pe_range_valid(loaded_size, section_table_offset, section_bytes)", self.text)
        self.assertIn("section_table_end > (size_of_headers as u64)", self.text)
        self.assertIn("section_end > (image.size_of_image as u64)", self.text)

    def test_section_permissions_come_from_pe_characteristics(self):
        for token in (
            "PE_SCN_MEM_EXECUTE: u32 = 0x20000000",
            "PE_SCN_MEM_READ: u32 = 0x40000000",
            "PE_SCN_MEM_WRITE: u32 = 0x80000000",
            "readable: (characteristics & PE_SCN_MEM_READ) != 0",
            "writable: (characteristics & PE_SCN_MEM_WRITE) != 0",
            "executable: (characteristics & PE_SCN_MEM_EXECUTE) != 0",
        ):
            self.assertIn(token, self.text)

    def test_parser_is_read_only_and_has_no_mmu_or_firmware_side_effects(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "*mut u8", "*mut u16", "*mut u32", "*mut u64",
            "ExitBootServices", "GetMemoryMap", "AllocatePages", "__write_cr3",
            "x86_write_cr3", "page_table_map_4k", "page_table_map_2m",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_main_registers_parser_without_parsing_during_hybrid_boot(self):
        self.assertIn("import kernel::memory::pe_image::*;", self.main)
        self.assertNotIn("pe_image_parse(", self.main)
        self.assertNotIn("pe_image_section(", self.main)


if __name__ == "__main__":
    unittest.main()
