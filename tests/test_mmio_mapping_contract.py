#!/usr/bin/env python3
"""Guardrails DF-9a para o contrato tipado de mapeamento MMIO."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MMIO = ROOT / "kernel/src/memory/mmio_mapping.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class MmioMappingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MMIO.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_in_native_graph(self):
        self.assertIn("import kernel::memory::mmio_mapping::*;", self.main)

    def test_contract_models_all_cache_policies_without_fake_backend_support(self):
        for token in (
            "MMIO_CACHE_POLICY_UC",
            "MMIO_CACHE_POLICY_WC",
            "MMIO_CACHE_POLICY_WT",
            "MMIO_CACHE_POLICY_WB",
            "pub struct MmioMapping",
            "pub physical_base: u64",
            "pub page_count: u64",
            "pub cache_policy: u8",
        ):
            self.assertIn(token, self.text)
        supported = self.text.split("pub fn mmio_mapping_supported", 1)[1].split("@system", 1)[0]
        self.assertIn("(*mapping).cache_policy == MMIO_CACHE_POLICY_UC", supported)
        self.assertNotIn("MMIO_CACHE_POLICY_WC", supported)
        self.assertNotIn("MMIO_CACHE_POLICY_WT", supported)
        self.assertNotIn("MMIO_CACHE_POLICY_WB", supported)

    def test_backend_capabilities_distinguish_generic_uc_from_dedicated_wc(self):
        backend = self.text.split("pub fn mmio_cache_policy_backend", 1)[1].split("@system", 1)[0]
        self.assertIn("MMIO_BACKEND_IDENTITY_UC", backend)
        self.assertIn("MMIO_BACKEND_FRAMEBUFFER_WC", backend)
        self.assertIn("MMIO_BACKEND_NONE", backend)
        generic = self.text.split("pub fn mmio_generic_mapping_supported", 1)[1].split("@system", 1)[0]
        self.assertIn("MMIO_BACKEND_IDENTITY_UC", generic)
        self.assertNotIn("MMIO_BACKEND_FRAMEBUFFER_WC", generic)

    def test_range_description_is_page_rounded_and_overflow_safe(self):
        body = self.text.split("pub fn mmio_describe_identity", 1)[1].split("@system", 1)[0]
        for token in (
            "mmio_range_end(base, size)",
            "x86_page_align_down(base)",
            "x86_page_align_up(end)",
            "limit < end",
            "span / 4096",
        ):
            self.assertIn(token, body)

    def test_mapping_delegates_only_to_existing_uc_backend(self):
        body = self.text.split("pub fn mmio_map_identity", 1)[1]
        self.assertIn("active_page_tables_map_mmio_identity_4k(page)", body)
        self.assertIn("mmio_mapping_supported(mapping)", body)
        self.assertIn("mmio_generic_mapping_supported(mapping)", self.text)
        self.assertNotIn("page_table_map_4k", body)
        self.assertNotIn("X86_PTE_CACHE_DISABLE", body)
        self.assertNotIn("X86_PTE_WRITE_THROUGH", body)

    def test_df9a_does_not_migrate_drivers(self):
        drivers = ROOT / "kernel/src/drivers"
        for path in drivers.glob("*.sotlas"):
            self.assertNotIn("mmio_map_identity(", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
