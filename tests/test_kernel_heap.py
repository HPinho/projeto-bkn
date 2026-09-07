"""Contratos do heap geral do kernel Baken OS."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEAP = ROOT / "kernel/src/memory/kernel_heap.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
SERIAL = ROOT / "kernel/src/arch/x86_64/serial.sotlas"
NVME_WORKFLOW = ROOT / ".github/workflows/baken_nvme_only.yml"


class KernelHeapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.heap = HEAP.read_text(encoding="utf-8")

    def test_heap_is_freestanding_and_pmm_backed(self):
        for token in (
            "module kernel::memory::kernel_heap;",
            "pmm_alloc_pages(pages)",
            "pmm_free_pages(physical, pages)",
            "direct_map_virtual_address(physical)",
            "vmm_direct_map_base() != BAKEN_DIRECT_MAP_BASE",
        ):
            self.assertIn(token, self.heap)
        lower = self.heap.lower()
        self.assertNotIn("malloc(", lower)
        self.assertNotIn("calloc(", lower)
        self.assertNotIn("realloc(", lower)
        self.assertNotIn("bootservices", lower)

    def test_heap_is_16_byte_aligned_and_splits_blocks(self):
        self.assertIn("KERNEL_HEAP_ALIGNMENT: u64 = 16", self.heap)
        self.assertIn("return rounded & ~(KERNEL_HEAP_ALIGNMENT - 1)", self.heap)
        alloc = self.heap.split("fn kernel_heap_alloc_locked", 1)[1].split("fn kernel_heap_coalesce_locked", 1)[0]
        self.assertIn("let remainder = original_size - aligned", alloc)
        self.assertIn("KERNEL_HEAP_BLOCK_BASES[split] = split_base", alloc)
        self.assertIn("KERNEL_HEAP_BLOCK_SIZES[slot] = aligned", alloc)

    def test_free_rejects_unknown_or_double_free_and_coalesces(self):
        free = self.heap.split("fn kernel_heap_free_locked", 1)[1].split("pub fn kernel_heap_alloc", 1)[0]
        self.assertIn("if !KERNEL_HEAP_BLOCK_USED[slot] { return false; }", free)
        self.assertIn("kernel_heap_coalesce_locked();", free)
        coalesce = self.heap.split("fn kernel_heap_coalesce_locked", 1)[1].split("fn kernel_heap_free_locked", 1)[0]
        self.assertIn("left_end == KERNEL_HEAP_BLOCK_BASES[right]", coalesce)
        self.assertIn("right_end == KERNEL_HEAP_BLOCK_BASES[left]", coalesce)
        self.assertIn("KERNEL_HEAP_BLOCK_ACTIVE[right] = false", coalesce)

    def test_public_operations_preserve_interrupt_state(self):
        alloc = self.heap.split("pub fn kernel_heap_alloc(size: u64)", 1)[1].split("pub fn kernel_heap_free", 1)[0]
        free = self.heap.split("pub fn kernel_heap_free(pointer: *mut u8)", 1)[1].split("fn kernel_heap_self_test", 1)[0]
        for body in (alloc, free):
            save = body.index("x86_irq_save_disable()")
            restore = body.index("x86_irq_restore(flags)")
            self.assertLess(save, restore)

    def test_self_test_proves_reuse_and_neighbor_survival(self):
        body = self.heap.split("fn kernel_heap_self_test() -> bool", 1)[1].split("pub fn kernel_heap_activate", 1)[0]
        self.assertIn("let first = kernel_heap_alloc(64)", body)
        self.assertIn("let second = kernel_heap_alloc(128)", body)
        self.assertIn("if !kernel_heap_free(first)", body)
        self.assertIn("let recycled = kernel_heap_alloc(32)", body)
        self.assertIn("(recycled as u64) != (first as u64)", body)
        self.assertIn("if *second_word != 0x8877665544332211", body)
        self.assertIn("kernel_heap_allocated_bytes() != before", body)

    def test_heap_activation_requires_pmm_vmm_and_direct_map(self):
        body = self.heap.split("pub fn kernel_heap_activate() -> bool", 1)[1]
        self.assertIn("pmm_allocator_is_active()", body)
        self.assertIn("vmm_is_active()", body)
        self.assertIn("vmm_direct_map_base() != BAKEN_DIRECT_MAP_BASE", body)
        self.assertIn("kernel_heap_self_test()", body)
        self.assertIn("KERNEL_HEAP_SELF_TEST_PASSED = true", body)

    def test_heap_is_in_kernel_graph(self):
        self.assertIn("import kernel::memory::kernel_heap::*;", MAIN.read_text(encoding="utf-8"))

    def test_post_cutover_orders_vmm_heap_acpi_fail_closed(self):
        text = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::memory::kernel_heap::*;", text)
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        vmm = entry.index("post_cutover_activate_vmm(context)")
        heap = entry.index("post_cutover_activate_heap()")
        acpi = entry.index("post_cutover_activate_acpi(context)")
        self.assertLess(vmm, heap)
        self.assertLess(heap, acpi)
        self.assertIn("if !post_cutover_activate_heap() { loop {} }", entry)
        activation = text.split("pub fn post_cutover_activate_heap() -> bool", 1)[1].split("pub fn post_cutover_heap_active", 1)[0]
        self.assertIn("kernel_heap_activate()", activation)
        self.assertIn("kernel_heap_self_test_passed()", activation)

    def test_qemu_gate_requires_named_heap_proof(self):
        serial = SERIAL.read_text(encoding="utf-8")
        workflow = NVME_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pub fn x86_serial_write_heap_ready_marker() -> bool", serial)
        self.assertIn("'BAKEN:HEAP_READY'", workflow)
        entry = POST.read_text(encoding="utf-8").split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        heap = entry.index("post_cutover_activate_heap()")
        marker = entry.index("x86_serial_write_heap_ready_marker()")
        self.assertLess(heap, marker)


if __name__ == "__main__":
    unittest.main()
