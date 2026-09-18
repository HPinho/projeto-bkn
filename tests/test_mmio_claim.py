#!/usr/bin/env python3
"""Guardrails DF-9b: MMIO ownership reutiliza o Resource Manager."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = ROOT / "kernel/src/device/mmio_claim.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
RESOURCE = ROOT / "kernel/src/device/resource_manager.sotlas"


class MmioClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CLAIM.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.resource = RESOURCE.read_text(encoding="utf-8")

    def test_claim_layer_is_in_native_graph_and_reuses_resource_manager(self):
        self.assertIn("import kernel::device::mmio_claim::*;", self.main)
        self.assertIn("import kernel::device::resource_manager::*;", self.text)
        self.assertNotIn("static mut MMIO_CLAIMS", self.text)
        self.assertNotIn("SpinLock", self.text)

    def test_claim_uses_page_rounded_range_and_mmio_kind(self):
        body = self.text.split("pub fn mmio_claim_and_map_identity", 1)[1]
        for token in (
            "mmio_claim_length(&mapping)",
            "start: mapping.page_base",
            "kind: RESOURCE_KIND_MMIO",
            "auxiliary: 0",
            "resource_claim(device, driver",
        ):
            self.assertIn(token, body)

    def test_claim_precedes_mapping_and_mapping_failure_rolls_back_claim(self):
        body = self.text.split("pub fn mmio_claim_and_map_identity", 1)[1].split(
            "pub fn mmio_release_claim", 1
        )[0]
        claim = body.index("resource_claim(device, driver")
        mapping = body.index("mmio_map_identity(&mapping)", claim)
        rollback = body.index("resource_release(resource, device, driver)", mapping)
        publish = body.index("return MmioClaim", rollback)
        self.assertLess(claim, mapping)
        self.assertLess(mapping, rollback)
        self.assertLess(rollback, publish)

    def test_release_is_exact_owner_resource_release_without_fake_unmap(self):
        body = self.text.split("pub fn mmio_release_claim", 1)[1]
        self.assertIn("resource_release(claim.resource, device, driver)", body)
        self.assertNotIn("active_runtime_unmap", body)
        self.assertNotIn("page_table_", body)

    def test_overlap_semantics_remain_centralized_in_resource_manager(self):
        self.assertIn("resource_ranges_overlap(left, right)", self.resource)
        self.assertIn("left.kind != right.kind", self.resource)


if __name__ == "__main__":
    unittest.main()
