#!/usr/bin/env python3
"""Guardrails do gate runtime PMM/VMM/DMA pós-cutover (STEP=!)."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "kernel/src/storage/foundation_probe.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
FIXTURE = ROOT / "tools/scripts/extend_foundation_fixture.py"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class FoundationMemoryRuntimeGateTests(unittest.TestCase):
    def test_memory_probe_exercises_constrained_dma_and_dynamic_vmm(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("pub fn foundation_memory_probe()", 1)[1]
        body = body.split("pub fn foundation_protective_mbr()", 1)[0]

        for token in (
            "let before = pmm_allocator_allocated_pages();",
            "dma_alloc_for_device(4096, 4096, 0xFFFFFFFF, 65536)",
            "pmm_allocator_allocated_pages() != before + 1",
            "active_runtime_map(VMM_RUNTIME_BASE, page.physical_address, true, false)",
            "*(VMM_RUNTIME_BASE as *mut u32) = 0xBA4E2026",
            "*(page.virtual_address as *const u32) != 0xBA4E2026",
            "active_runtime_protect(VMM_RUNTIME_BASE, false, false)",
            "X86_PTE_WRITABLE",
            "X86_PTE_NX",
            "active_runtime_protect(VMM_RUNTIME_BASE, true, true)",
            "active_runtime_unmap(VMM_RUNTIME_BASE)",
            "active_runtime_pte(VMM_RUNTIME_BASE) != 0",
            "active_runtime_map(VMM_RUNTIME_BASE, page.physical_address, false, false)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, body)

    def test_memory_probe_enforces_dma_ownership_fence_and_release(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("pub fn foundation_memory_probe()", 1)[1]
        body = body.split("pub fn foundation_protective_mbr()", 1)[0]

        submit = body.index("dma_submit_to_device(&mut page, 1)")
        wrong_fence = body.index("dma_complete_from_device(&mut page, 2)", submit)
        blocked_release = body.index("dma_release(&mut page)", wrong_fence)
        right_fence = body.index("dma_complete_from_device(&mut page, 1)", blocked_release)
        final_release = body.index("dma_release(&mut page)", right_fence)
        accounting = body.index("pmm_allocator_allocated_pages() != before", final_release)
        marker = body.index("x86_serial_write_stage_marker('!' as u8)", accounting)

        self.assertLess(submit, wrong_fence)
        self.assertLess(wrong_fence, blocked_release)
        self.assertLess(blocked_release, right_fence)
        self.assertLess(right_fence, final_release)
        self.assertLess(final_release, accounting)
        self.assertLess(accounting, marker)

    def test_post_cutover_chains_memory_gate_before_external_irq_gate(self):
        text = POST.read_text(encoding="utf-8")
        backup = text.index("post_cutover_probe_backup_gpt_entries()")
        memory = text.index("foundation_memory_probe()", backup)
        irq = text.index("foundation_external_irq_probe()", memory)
        self.assertLess(backup, memory)
        self.assertLess(memory, irq)

    def test_ci_verifier_requires_runtime_memory_marker(self):
        fixture = FIXTURE.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("'BAKEN:STEP=!'", fixture)
        self.assertIn(
            "python3 tools/scripts/extend_foundation_fixture.py build/storage-test.img --verify build/qemu-serial.log",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
