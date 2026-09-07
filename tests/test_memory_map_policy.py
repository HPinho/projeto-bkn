#!/usr/bin/env python3
"""Guardrails da política Baken para o snapshot de memória do bootstrap."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "kernel/src/memory/memory_map_policy.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class MemoryMapPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = POLICY.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_direct_map_ram_types_are_baken_owned_and_explicit(self):
        for token in (
            "BAKEN_BOOT_MEMORY_LOADER_CODE", "BAKEN_BOOT_MEMORY_LOADER_DATA",
            "BAKEN_BOOT_MEMORY_BOOT_SERVICES_CODE", "BAKEN_BOOT_MEMORY_BOOT_SERVICES_DATA",
            "BAKEN_BOOT_MEMORY_CONVENTIONAL", "BAKEN_BOOT_MEMORY_ACPI_RECLAIM",
            "BAKEN_BOOT_MEMORY_ACPI_NVS",
        ):
            self.assertIn(token, self.policy)
        self.assertIn("pub fn boot_memory_type_is_direct_map_ram", self.policy)

    def test_runtime_and_mmio_are_not_automatic_direct_map_ram(self):
        fn = self.policy.split("pub fn boot_memory_type_is_direct_map_ram", 1)[1].split("}", 1)[0]
        for token in (
            "BAKEN_BOOT_MEMORY_RUNTIME_SERVICES_CODE",
            "BAKEN_BOOT_MEMORY_RUNTIME_SERVICES_DATA",
            "BAKEN_BOOT_MEMORY_MMIO", "BAKEN_BOOT_MEMORY_MMIO_PORT_SPACE",
        ):
            self.assertNotIn(token, fn)
        self.assertIn("pub fn boot_memory_type_is_mmio", self.policy)

    def test_initial_direct_map_requires_wb_and_rejects_runtime_attribute(self):
        self.assertIn("BAKEN_BOOT_MEMORY_ATTR_WB", self.policy)
        self.assertIn("BAKEN_BOOT_MEMORY_ATTR_RUNTIME", self.policy)
        self.assertIn("(attribute & BAKEN_BOOT_MEMORY_ATTR_RUNTIME) != 0", self.policy)
        self.assertIn("(attribute & BAKEN_BOOT_MEMORY_ATTR_WB) != 0", self.policy)

    def test_reclaim_policy_keeps_acpi_nvs_and_runtime_out(self):
        fn = self.policy.split("pub fn boot_memory_type_is_immediately_reclaimable", 1)[1].split("}", 1)[0]
        self.assertIn("BAKEN_BOOT_MEMORY_CONVENTIONAL", fn)
        self.assertNotIn("BAKEN_BOOT_MEMORY_ACPI_NVS", fn)
        self.assertNotIn("BAKEN_BOOT_MEMORY_RUNTIME_SERVICES_CODE", fn)
        self.assertIn("boot_memory_type_is_acpi_reclaimable_later", self.policy)

    def test_kernel_memory_api_has_no_efi_named_identifiers(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.policy.splitlines())
        for token in ("EFI_", "uefi_", "Efi", "BootServices", "RuntimeServices"):
            self.assertNotIn(token, code)

    def test_policy_is_pure_and_does_not_touch_mmu_or_firmware(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.policy.splitlines())
        for token in ("GetMemoryMap", "ExitBootServices", "AllocatePages", "page_table_write", "page_table_map_", "__write_cr3", "__invlpg", "as *mut", "as *const"):
            self.assertNotIn(token, code)

    def test_graph_root_only_registers_policy(self):
        self.assertIn("import kernel::memory::memory_map_policy::*;", self.main)
        for token in ("boot_memory_type_is_direct_map_ram(", "boot_memory_descriptor_is_direct_map_wb(", "boot_memory_type_is_immediately_reclaimable("):
            self.assertNotIn(token, self.main)


if __name__ == "__main__": unittest.main()
