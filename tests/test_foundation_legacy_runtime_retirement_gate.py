#!/usr/bin/env python3
"""Gate de aposentadoria do runtime UEFI legado do Baken OS."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPAT = ROOT / "kernel/src/baken_runtime.sotlas"
NATIVE = ROOT / "kernel/src/baken_native_runtime.sotlas"
BOOT = ROOT / "boot/uefi_bootloader.sotlas"


class FoundationLegacyRuntimeRetirementGateTests(unittest.TestCase):
    def test_compat_runtime_has_no_firmware_state_or_protocol_types(self):
        text = COMPAT.read_text(encoding="utf-8")
        code = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
        for forbidden in (
            "EfiGuid", "EfiSystemTable", "EfiBootServicesPrefix",
            "EfiSimpleTextInput", "EfiSimplePointer", "EfiAbsolutePointer",
            "BakenBootContext", "G_SYSTEM_TABLE", "G_BOOT_SERVICES", "G_KEYBOARD",
            "G_SIMPLE_POINTERS", "G_ABS_POINTERS", "LocateProtocol", "ReadKeyStroke",
            "pointer_protocol", "block_io_protocol", "install_target_block_io_protocol",
            "baken_efi_init", "baken_efi_poll_key", "baken_efi_poll_mouse_rel",
            "baken_efi_poll_mouse_abs",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_only_native_timer_abi_aliases_remain(self):
        text = COMPAT.read_text(encoding="utf-8")
        aliases = set(re.findall(r"pub fn (baken_efi_[A-Za-z0-9_]+)", text))
        self.assertEqual(aliases, {"baken_efi_read_tsc", "baken_efi_frame_wait"})
        self.assertIn("return x86_timer_read_tsc();", text)
        self.assertIn("x86_timer_elapsed_us(frame_start, frame_end)", text)
        self.assertIn("x86_timer_spin_wait_us(target_us - work_us)", text)
        self.assertNotIn("Stall(", text)

    def test_compat_entry_delegates_input_and_ui_loop_to_native_runtime(self):
        text = COMPAT.read_text(encoding="utf-8")
        native = NATIVE.read_text(encoding="utf-8")
        self.assertIn("import kernel::baken_native_runtime::*;", text)
        self.assertIn("baken_native_runtime_run(width, height);", text)
        self.assertIn("ps2_keyboard_poll", native)
        self.assertIn("ps2_mouse_poll", native)
        self.assertIn("x86_timer_calibrate_from_acpi_pm()", native)
        self.assertNotIn("baken_efi_", native)

    def test_bootstrap_loader_stays_out_of_input_and_storage_discovery(self):
        text = BOOT.read_text(encoding="utf-8")
        for forbidden in (
            "EFI_SIMPLE_POINTER_PROTOCOL_GUID", "EFI_ABSOLUTE_POINTER_PROTOCOL_GUID",
            "EFI_BLOCK_IO_PROTOCOL", "ReadBlocks", "find_boot_media", "find_install_target",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        self.assertIn("EFI_GRAPHICS_OUTPUT_PROTOCOL_GUID", text)
        self.assertIn("baken_exit_boot_services_final(", text)


if __name__ == "__main__":
    unittest.main()
