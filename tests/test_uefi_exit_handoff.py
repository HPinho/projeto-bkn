#!/usr/bin/env python3
"""Contracts for the active final UEFI ExitBootServices handoff."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "boot/uefi_exit_boot_services.h"
BOOTLOADER = ROOT / "boot/uefi_bootloader.sotlas"


class UefiExitHandoffTests(unittest.TestCase):
    def test_helper_has_typed_exit_boot_services_final_map_and_callback(self):
        text = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("BAKEN_EFI_EXIT_BOOT_SERVICES", text)
        self.assertIn("BAKEN_FINAL_MEMORY_MAP", text)
        self.assertIn("BAKEN_PRE_EXIT_CALLBACK", text)
        self.assertIn("map_key", text)
        self.assertIn("descriptor_size", text)
        self.assertIn("descriptor_version", text)
        self.assertIn("baken_final_map_physical_address", text)

    def test_retry_contract_rebuilds_cutover_for_each_map_key(self):
        text = HANDOFF.read_text(encoding="utf-8")
        refresh = "status = baken_refresh_final_memory_map(bs, state);"
        prepare = "status = prepare_cutover(state, prepare_context);"
        exit_call = "status = exit_boot_services(image_handle, state->map_key);"
        reject_other_errors = "if (status != EFI_INVALID_PARAMETER) {"

        self.assertIn("BAKEN_UEFI_EXIT_MAX_ATTEMPTS", text)
        self.assertIn(refresh, text)
        self.assertIn(prepare, text)
        self.assertIn(exit_call, text)
        self.assertIn(reject_other_errors, text)

        refresh_pos = text.index(refresh)
        prepare_pos = text.index(prepare, refresh_pos)
        exit_pos = text.index(exit_call, prepare_pos)
        reject_pos = text.index(reject_other_errors, exit_pos)
        self.assertLess(refresh_pos, prepare_pos)
        self.assertLess(prepare_pos, exit_pos)
        self.assertLess(exit_pos, reject_pos)

    def test_pre_exit_window_contains_no_firmware_allocation_or_cleanup(self):
        text = HANDOFF.read_text(encoding="utf-8")
        marker = "status = baken_refresh_final_memory_map(bs, state);"
        exit_call = "status = exit_boot_services(image_handle, state->map_key);"
        start = text.index(marker)
        end = text.index(exit_call, start)
        between = text[start:end]
        self.assertIn("prepare_cutover(state, prepare_context)", between)
        for forbidden in (
            "allocate_pool(", "free_pool(", "Stall(", "LocateProtocol(",
            "AllocatePages(", "FreePages(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, between)

    def test_bootloader_activates_cutover_and_no_longer_calls_hybrid_kernel_entry(self):
        bootloader = BOOTLOADER.read_text(encoding="utf-8")
        self.assertIn("baken_exit_boot_services_final(", bootloader)
        self.assertIn("baken_prepare_cutover_from_final_map", bootloader)
        self.assertIn("cutover_prepare(&input)", bootloader)
        self.assertIn("x86_stack_switch_to_post_cutover_raw(", bootloader)
        self.assertNotIn("baken_kernel_main(&boot_info);", bootloader)

    def test_success_path_has_no_cleanup_after_exit(self):
        helper = HANDOFF.read_text(encoding="utf-8")
        success = re.search(
            r"status = exit_boot_services\(image_handle, state->map_key\);\s*"
            r"if \(status == EFI_SUCCESS\) \{(?P<body>.*?)\}",
            helper,
            re.S,
        )
        self.assertIsNotNone(success)
        body = success.group("body")
        self.assertIn("return EFI_SUCCESS;", body)
        self.assertNotIn("free_pool", body)
        self.assertNotIn("AllocatePool", body)

        bootloader = BOOTLOADER.read_text(encoding="utf-8")
        post_success = bootloader.split("if (status != EFI_SUCCESS) return status;", 1)[1]
        self.assertIn("x86_stack_switch_to_post_cutover_raw(", post_success)
        for forbidden in (
            "bs->", "SystemTable->", "pointer_protocol", "block_io_protocol",
            "FreePool", "AllocatePool", "LocateProtocol", "Stall(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, post_success)

    def test_context_uses_physical_final_map_and_acpi_addresses(self):
        bootloader = BOOTLOADER.read_text(encoding="utf-8")
        self.assertIn("map_physical = baken_final_map_physical_address", bootloader)
        self.assertIn("image_physical = baken_final_map_physical_address", bootloader)
        self.assertIn("acpi_physical = baken_final_map_physical_address", bootloader)
        self.assertIn("post->memory_map_base = map_physical", bootloader)
        self.assertIn("post->acpi_rsdp = acpi_physical", bootloader)
        self.assertIn("post->root_physical = prepared.root_physical", bootloader)
        self.assertIn("post->valid = true", bootloader)


if __name__ == "__main__":
    unittest.main()
