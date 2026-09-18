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
        generic = self.text.split("pub fn mmio_generic_mapping_supported", 1)[1].split("@system", 1)[0]
        self.assertIn("mmio_generic_mapping_supported(mapping)", supported)
        self.assertIn("MMIO_BACKEND_IDENTITY_UC", generic)
        self.assertIn("MMIO_BACKEND_IDENTITY_WC", generic)
        self.assertIn("MMIO_BACKEND_IDENTITY_WT", generic)
        self.assertIn("MMIO_BACKEND_IDENTITY_WB", generic)
        self.assertNotIn("MMIO_BACKEND_FRAMEBUFFER_WC", generic)
        self.assertIn("MMIO_BACKEND_IDENTITY_WT", generic)
        self.assertIn("MMIO_BACKEND_IDENTITY_WB", generic)

    def test_backend_capabilities_distinguish_generic_uc_from_dedicated_wc(self):
        backend = self.text.split("pub fn mmio_cache_policy_backend", 1)[1].split("@system", 1)[0]
        self.assertIn("MMIO_BACKEND_IDENTITY_UC", backend)
        self.assertIn("MMIO_BACKEND_IDENTITY_WC", backend)
        self.assertIn("MMIO_BACKEND_IDENTITY_WT", backend)
        self.assertIn("MMIO_BACKEND_IDENTITY_WB", backend)
        self.assertIn("MMIO_BACKEND_NONE", backend)
        generic = self.text.split("pub fn mmio_generic_mapping_supported", 1)[1].split("@system", 1)[0]
        self.assertIn("MMIO_BACKEND_IDENTITY_UC", generic)
        self.assertIn("MMIO_BACKEND_IDENTITY_WC", generic)
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

    def test_mapping_stages_uc_before_optional_pat_promotion(self):
        body = self.text.split("pub fn mmio_map_identity", 1)[1]
        uc = body.index("active_page_tables_map_mmio_identity_4k(page)")
        wc = body.index("active_mmio_promote_identity_wc(page_base, count)", uc)
        pat_lookup = body.index("mmio_pat_find_runtime_index(memory_type)", wc)
        generic = body.index("active_mmio_promote_identity_pat_index(page_base, count, pat_index)", pat_lookup)
        rollback = body.index("active_mmio_restore_identity_uc(page_base, count)", generic)
        self.assertLess(uc, wc)
        self.assertLess(wc, pat_lookup)
        self.assertLess(pat_lookup, generic)
        self.assertLess(generic, rollback)
        self.assertIn("PAT_MEMORY_TYPE_WT", body)
        self.assertIn("PAT_MEMORY_TYPE_WB", body)
        self.assertIn("MMIO_PAT_INDEX_INVALID", body)
        self.assertNotIn("page_table_map_4k", body)

    def test_df9d_allows_only_certified_typed_driver_callers(self):
        drivers = ROOT / "kernel/src/drivers"
        allowed = {"pci_config.sotlas", "pci_msix_table.sotlas", "pci_msix_activation.sotlas", "xhci_controller.sotlas"}
        for path in drivers.glob("*.sotlas"):
            text = path.read_text(encoding="utf-8")
            if path.name in allowed:
                self.assertIn("mmio_map_identity(", text)
            else:
                self.assertNotIn("mmio_map_identity(", text)


if __name__ == "__main__":
    unittest.main()
