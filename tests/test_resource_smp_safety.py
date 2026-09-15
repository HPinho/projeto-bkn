"""DF-3: serialização SMP/IRQ e ausência de efeitos físicos."""
import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] /
          "kernel/src/device/resource_manager.sotlas").read_text(encoding="utf-8")


class ResourceSmpSafetyTests(unittest.TestCase):
    def test_lock_preserves_rflags_even_when_if_was_clear(self):
        self.assertIn("fn resource_lock_irq(saved_flags: *mut u64) -> bool", SOURCE)
        self.assertIn("*saved_flags = flags", SOURCE)
        self.assertNotIn("if flags == 0", SOURCE)

    def test_claim_conflict_scan_and_insert_share_one_lock(self):
        claim = SOURCE.split("pub fn resource_claim", 1)[1].split(
            "pub fn resource_snapshot", 1)[0]
        self.assertLess(claim.index("resource_lock_irq(&mut flags)"),
                        claim.index("resource_requests_conflict"))
        self.assertLess(claim.index("resource_requests_conflict"),
                        claim.index("RESOURCE_CLAIMS[free_slot] = ResourceClaim"))
        self.assertLess(claim.index("RESOURCE_CLAIMS[free_slot] = ResourceClaim"),
                        claim.index("resource_unlock_irq(flags)"))

    def test_policy_layer_has_no_physical_side_effects(self):
        for forbidden in ("active_page_tables_map_mmio", "dma_alloc(",
                          "lapic_send", "__outb", "pci_enable_command_bits"):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
