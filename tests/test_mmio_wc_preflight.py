#!/usr/bin/env python3
"""Guardrails DF-9c2: preflight e restauração UC para futuro backend WC."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "kernel/src/memory/active_page_tables.sotlas"
MMIO = ROOT / "kernel/src/memory/mmio_mapping.sotlas"


class MmioWcPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.active = ACTIVE.read_text(encoding="utf-8")
        cls.mmio = MMIO.read_text(encoding="utf-8")

    def test_preflight_requires_exact_identity_rw_nx_uc_and_no_user(self):
        body = self.active.split("fn active_mmio_identity_uc_pte_locked", 1)[1].split(
            "@system", 1
        )[0]
        for token in (
            "x86_pte_address(pte) != page",
            "X86_PTE_WRITABLE",
            "X86_PTE_NX",
            "X86_PTE_WRITE_THROUGH",
            "X86_PTE_CACHE_DISABLE",
            "X86_PTE_USER",
            "(pte & 0x98)",
        ):
            self.assertIn(token, body)

    def test_range_preflight_is_bounded_and_lock_serialized(self):
        body = self.active.split("pub fn active_mmio_identity_uc_range_ready", 1)[1].split(
            "@system", 1
        )[0]
        self.assertIn("page_count > (0xFFFFFFFFFFFFFFFF / 4096)", body)
        self.assertIn("page_base + span <= page_base", body)
        self.assertIn("active_page_tables_lock_irq()", body)
        self.assertIn("active_mmio_identity_uc_pte_locked(page)", body)
        self.assertIn("active_page_tables_unlock_irq(flags_irq)", body)

    def test_restore_reconstructs_uc_pat_selection_and_flushes(self):
        body = self.active.split("fn active_mmio_restore_uc_locked", 1)[1].split(
            "@system", 1
        )[0]
        self.assertIn("(old & ~0x98)", body)
        self.assertIn("X86_PTE_WRITE_THROUGH | X86_PTE_CACHE_DISABLE", body)
        self.assertIn("page_table_write_entry", body)
        self.assertIn("active_page_tables_publish_locked(page)", body)
        self.assertIn("__dma_fence()", body)

    def test_df9c3_wc_promotion_is_preflighted_and_rollback_capable(self):
        body = self.active.split("pub fn active_mmio_promote_identity_wc", 1)[1].split(
            "@system", 1
        )[0]
        preflight = body.index("active_mmio_identity_uc_pte_locked(page)")
        install = body.index("__pat_install_wc()", preflight)
        write = body.index("page_table_write_entry", install)
        rollback = body.index("active_mmio_restore_uc_locked(page_base, page_count)", write)
        self.assertLess(preflight, install)
        self.assertLess(install, write)
        self.assertLess(write, rollback)
        self.assertIn("(old & ~0x98) | 0x98", body)
        self.assertIn("active_page_tables_publish_locked(page)", body)
        self.assertIn("__dma_fence()", body)

        mapper = self.mmio.split("pub fn mmio_generic_mapping_supported", 1)[1].split(
            "@system", 1
        )[0]
        self.assertIn("MMIO_BACKEND_IDENTITY_UC", mapper)
        self.assertIn("MMIO_BACKEND_IDENTITY_WC", mapper)
        self.assertNotIn("MMIO_BACKEND_FRAMEBUFFER_WC", mapper)


if __name__ == "__main__":
    unittest.main()
