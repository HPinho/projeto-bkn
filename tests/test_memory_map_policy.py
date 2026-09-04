#!/usr/bin/env python3
"""Guardrails da política do UEFI Memory Map."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "kernel" / "src" / "memory" / "memory_map_policy.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class MemoryMapPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = POLICY.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_direct_map_ram_types_are_explicit(self):
        for token in (
            "EFI_LOADER_CODE", "EFI_LOADER_DATA",
            "EFI_BOOT_SERVICES_CODE", "EFI_BOOT_SERVICES_DATA",
            "EFI_CONVENTIONAL_MEMORY_TYPE",
            "EFI_ACPI_RECLAIM_MEMORY_TYPE", "EFI_ACPI_MEMORY_NVS_TYPE",
        ):
            self.assertIn(token, self.policy)
        self.assertIn("pub fn uefi_memory_type_is_direct_map_ram", self.policy)

    def test_runtime_and_mmio_are_not_automatic_direct_map_ram(self):
        fn = self.policy.split("pub fn uefi_memory_type_is_direct_map_ram", 1)[1]
        fn = fn.split("}", 1)[0]
        for token in (
            "EFI_RUNTIME_SERVICES_CODE", "EFI_RUNTIME_SERVICES_DATA",
            "EFI_MEMORY_MAPPED_IO_TYPE", "EFI_MEMORY_MAPPED_IO_PORT_SPACE_TYPE",
        ):
            self.assertNotIn(token, fn)
        self.assertIn("pub fn uefi_memory_type_is_mmio", self.policy)

    def test_initial_direct_map_requires_wb_and_rejects_runtime_attribute(self):
        self.assertIn("EFI_MEMORY_WB", self.policy)
        self.assertIn("EFI_MEMORY_RUNTIME", self.policy)
        self.assertIn("(attribute & EFI_MEMORY_RUNTIME) != 0", self.policy)
        self.assertIn("(attribute & EFI_MEMORY_WB) != 0", self.policy)

    def test_reclaim_policy_keeps_acpi_nvs_and_runtime_out(self):
        fn = self.policy.split("pub fn uefi_memory_type_is_immediately_reclaimable", 1)[1]
        fn = fn.split("}", 1)[0]
        self.assertIn("EFI_CONVENTIONAL_MEMORY_TYPE", fn)
        self.assertNotIn("EFI_ACPI_MEMORY_NVS_TYPE", fn)
        self.assertNotIn("EFI_RUNTIME_SERVICES_CODE", fn)
        self.assertIn("uefi_memory_type_is_acpi_reclaimable_later", self.policy)

    def test_policy_is_pure_and_does_not_touch_mmu_or_firmware(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.policy.splitlines())
        for token in (
            "GetMemoryMap", "ExitBootServices", "AllocatePages",
            "page_table_write", "page_table_map_", "__write_cr3", "__invlpg",
            "as *mut", "as *const",
        ):
            self.assertNotIn(token, code)

    def test_hybrid_main_only_registers_policy(self):
        self.assertIn("import kernel::memory::memory_map_policy::*;", self.main)
        for token in (
            "uefi_memory_type_is_direct_map_ram(",
            "uefi_memory_descriptor_is_direct_map_wb(",
            "uefi_memory_type_is_immediately_reclaimable(",
        ):
            self.assertNotIn(token, self.main)


if __name__ == "__main__":
    unittest.main()
