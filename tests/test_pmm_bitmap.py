"""Contratos do bitmap de páginas físicos, sem heap ou UEFI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BITMAP = ROOT / "kernel/src/memory/pmm_bitmap.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class PmmBitmapTests(unittest.TestCase):
    def test_bitmap_requires_caller_owned_storage(self):
        text = BITMAP.read_text(encoding="utf-8")
        self.assertIn("storage: *mut u8", text)
        self.assertIn("pmm_bitmap_required_bytes", text)
        self.assertIn("storage == (null as *mut u8)", text)
        self.assertNotIn("malloc", text.lower())
        self.assertNotIn("BootServices", text)

    def test_bitmap_has_checked_mark_test_and_contiguous_search(self):
        text = BITMAP.read_text(encoding="utf-8")
        self.assertIn("pub fn pmm_bitmap_test", text)
        self.assertIn("pub fn pmm_bitmap_mark", text)
        self.assertIn("pub fn pmm_bitmap_find_free_run", text)
        self.assertIn("while page < (*bitmap).page_count", text)
        self.assertIn("if run == count { return start; }", text)

    def test_bitmap_is_registered_in_kernel_graph(self):
        self.assertIn("import kernel::memory::pmm_bitmap::*;", MAIN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
