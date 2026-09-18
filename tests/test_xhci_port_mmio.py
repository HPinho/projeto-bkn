#!/usr/bin/env python3
"""DF-9d5 guardrails: xHCI PORTSC mapping uses the typed UC contract."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PORT = (ROOT / "kernel/src/drivers/xhci_port.sotlas").read_text(encoding="utf-8")


class XhciPortMmioMigrationTests(unittest.TestCase):
    def test_port_helper_preserves_single_page_uc_mapping(self):
        body = PORT.split("fn xhci_port_map", 1)[1].split("@system", 1)[0]
        self.assertIn("xhci_port_page_base(address)", body)
        self.assertIn("mmio_describe_identity(page, 4096, MMIO_CACHE_POLICY_UC)", body)
        self.assertIn("mmio_map_identity(&mapping)", body)
        self.assertNotIn("active_page_tables_map_mmio_identity_4k", body)

    def test_port_scan_remains_read_only(self):
        body = PORT.split("pub fn xhci_port_scan()", 1)[1].split("@system", 1)[0]
        self.assertIn("x86_mmio_read32(address)", body)
        self.assertNotIn("x86_mmio_write32", body)
        self.assertIn("xhci_port_map(address)", body)


if __name__ == "__main__":
    unittest.main()
