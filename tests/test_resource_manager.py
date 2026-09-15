"""DF-3: catálogo universal e conflitos de recursos."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "kernel/src/device/resource_manager.sotlas").read_text(encoding="utf-8")
TYPES = (ROOT / "kernel/src/device/types.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class ResourceManagerTests(unittest.TestCase):
    def test_resource_taxonomy_covers_df3(self):
        for name in ("MMIO", "IO_PORT", "PCI_BAR", "IRQ", "DMA"):
            self.assertIn(f"RESOURCE_KIND_{name}", TYPES)
        for token in ("pub struct ResourceHandle", "pub struct ResourceRequest",
                      "pub struct ResourceClaim"):
            self.assertIn(token, TYPES)

    def test_conflicts_are_kind_aware(self):
        body = SOURCE.split("fn resource_requests_conflict", 1)[1].split(
            "fn resource_handle_live_locked", 1)[0]
        self.assertIn("left.kind != right.kind", body)
        self.assertIn("left.auxiliary == right.auxiliary", body)
        self.assertIn("resource_ranges_overlap(left, right)", body)

    def test_manager_is_in_graph_but_not_boot_path(self):
        self.assertIn("import kernel::device::resource_manager::*;", MAIN)
        runtime = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("resource_manager_init()", runtime)


if __name__ == "__main__":
    unittest.main()
