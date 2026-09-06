#!/usr/bin/env python3
"""Guardrail for keeping UEFI limited to bootstrap-only platform discovery."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "boot/uefi_bootloader.sotlas"


class FoundationBootstrapProtocolCleanupGateTests(unittest.TestCase):
    def test_loader_keeps_only_bootstrap_platform_protocols(self):
        text = BOOT.read_text(encoding="utf-8")

        # GOP, ACPI, Loaded Image, Memory Map and ExitBootServices remain valid
        # bootstrap responsibilities.
        for required in (
            "EFI_GRAPHICS_OUTPUT_PROTOCOL_GUID",
            "EFI_LOADED_IMAGE_PROTOCOL_GUID",
            "find_acpi_rsdp",
            "capture_memory_map",
            "baken_exit_boot_services_final(",
            "x86_stack_switch_to_post_cutover_raw(",
        ):
            self.assertIn(required, text)

        # Input and storage discovery belong to native Baken drivers now.
        for forbidden in (
            "EFI_SIMPLE_POINTER_PROTOCOL_GUID",
            "EFI_ABSOLUTE_POINTER_PROTOCOL_GUID",
            "EFI_BLOCK_IO_PROTOCOL_GUID",
            "EFI_BLOCK_IO_PROTOCOL",
            "EFI_BLOCK_IO_MEDIA",
            "find_pointer_protocol",
            "find_install_target",
            "find_boot_media",
            "is_baken_boot_media",
            "ReadBlocks",
            "WriteBlocks",
            "block_io",
            "install_target",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_loader_does_not_transport_firmware_objects(self):
        text = BOOT.read_text(encoding="utf-8")
        for forbidden in (
            "boot_info.system_table =",
            "boot_info.pointer_protocol =",
            "boot_info.block_io_protocol =",
            "boot_info.install_target_block_io_protocol =",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("boot_info.flags = 0;", text)


if __name__ == "__main__":
    unittest.main()
