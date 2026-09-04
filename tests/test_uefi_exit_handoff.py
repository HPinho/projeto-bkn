#!/usr/bin/env python3
"""Contracts for the staged final UEFI ExitBootServices handoff."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "boot/uefi_exit_boot_services.h"
BOOTLOADER = ROOT / "boot/uefi_bootloader.sotlas"


class UefiExitHandoffTests(unittest.TestCase):
    def test_helper_has_typed_exit_boot_services_and_final_map_state(self):
        text = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("BAKEN_EFI_EXIT_BOOT_SERVICES", text)
        self.assertIn("BAKEN_FINAL_MEMORY_MAP", text)
        self.assertIn("map_key", text)
        self.assertIn("descriptor_size", text)
        self.assertIn("descriptor_version", text)

    def test_retry_contract_handles_map_key_changes(self):
        text = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("BAKEN_UEFI_EXIT_MAX_ATTEMPTS", text)
        self.assertIn("baken_refresh_final_memory_map", text)
        self.assertIn("exit_boot_services(image_handle, state->map_key)", text)
        # Qualquer status diferente de INVALID_PARAMETER encerra; quando é
        # INVALID_PARAMETER o fluxo cai no fim do loop e refaz GetMemoryMap.
        self.assertIn("if (status != EFI_INVALID_PARAMETER)", text)
        self.assertRegex(
            text,
            r"if \(status != EFI_INVALID_PARAMETER\) \{\s*return status;\s*\}.*?Map key mudou",
        )

    def test_no_boot_service_call_is_inserted_between_final_map_and_exit(self):
        text = HANDOFF.read_text(encoding="utf-8")
        marker = "status = baken_refresh_final_memory_map(bs, state);"
        exit_call = "status = exit_boot_services(image_handle, state->map_key);"
        start = text.index(marker)
        end = text.index(exit_call, start)
        between = text[start:end]
        self.assertNotIn("allocate_pool(", between)
        self.assertNotIn("free_pool(", between)
        self.assertNotIn("Stall(", between)
        self.assertNotIn("LocateProtocol(", between)

    def test_cutover_helper_remains_staged_not_active(self):
        bootloader = BOOTLOADER.read_text(encoding="utf-8")
        self.assertNotIn("baken_exit_boot_services_final(", bootloader)
        self.assertIn("baken_kernel_main(&boot_info);", bootloader)

    def test_success_path_has_no_cleanup_after_exit(self):
        text = HANDOFF.read_text(encoding="utf-8")
        success = re.search(
            r"status = exit_boot_services\(image_handle, state->map_key\);\s*"
            r"if \(status == EFI_SUCCESS\) \{(?P<body>.*?)\}",
            text,
            re.S,
        )
        self.assertIsNotNone(success)
        body = success.group("body")
        self.assertIn("return EFI_SUCCESS;", body)
        self.assertNotIn("free_pool", body)
        self.assertNotIn("AllocatePool", body)


if __name__ == "__main__":
    unittest.main()
