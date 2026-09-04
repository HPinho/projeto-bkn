#!/usr/bin/env python3
"""Guardrails do direct-map construído por ranges UEFI seguros."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RANGES = ROOT / "kernel" / "src" / "memory" / "direct_map_ranges.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class DirectMapRangesTests(unittest.TestCase):
    def setUp(self):
        self.ranges = RANGES.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_builder_walks_variable_size_uefi_descriptors(self):
        self.assertIn("descriptor_size < 40", self.ranges)
        self.assertIn("offset += descriptor_size", self.ranges)
        self.assertIn("address as *const EfiMemoryDescriptor", self.ranges)

    def test_builder_uses_memory_policy_before_mapping(self):
        self.assertIn("uefi_memory_descriptor_is_direct_map_wb", self.ranges)
        self.assertIn("skipped_descriptor_count += 1", self.ranges)

    def test_builder_prefers_2m_only_inside_each_safe_range(self):
        self.assertIn("remaining >= X86_PAGE_SIZE_2M", self.ranges)
        self.assertIn("physical_cursor % X86_PAGE_SIZE_2M", self.ranges)
        self.assertIn("page_table_map_2m(", self.ranges)
        self.assertIn("page_table_map_4k(", self.ranges)

    def test_direct_map_is_writable_global_and_nx(self):
        self.assertIn(
            "X86_PTE_PRESENT | X86_PTE_WRITABLE | X86_PTE_GLOBAL | X86_PTE_NX",
            self.ranges,
        )

    def test_builder_rejects_range_overflow_and_span_escape(self):
        self.assertIn("(byte_count / X86_PAGE_SIZE) != page_count", self.ranges)
        self.assertIn("physical_end <= physical_start", self.ranges)
        self.assertIn("physical_end > BAKEN_DIRECT_MAP_SPAN", self.ranges)

    def test_range_builder_does_not_activate_cr3_or_pat(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.ranges.splitlines())
        for token in (
            "__write_cr3", "write_cr3", "__invlpg", "__wrmsr",
            "IA32_PAT", "ExitBootServices", "AllocatePages",
        ):
            self.assertNotIn(token, code)

    def test_hybrid_main_does_not_materialize_direct_map(self):
        self.assertIn("import kernel::memory::direct_map_ranges::*;", self.main)
        self.assertNotIn("direct_map_build_from_uefi_ranges(", self.main)
        self.assertNotIn("page_table_map_2m(", self.main)
        self.assertNotIn("page_table_map_4k(", self.main)


if __name__ == "__main__":
    unittest.main()
