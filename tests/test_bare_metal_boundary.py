#!/usr/bin/env python3
"""Guardrails for the Baken OS migration from UEFI runtime to bare metal."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BareMetalBoundaryTests(unittest.TestCase):
    def test_architecture_declares_uefi_bootstrap_only(self):
        text = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        self.assertIn("UEFI é apenas bootstrap", text)
        self.assertIn("ExitBootServices()", text)
        self.assertIn("O compilador não desenha o sistema operacional", text)

    def test_final_bootinfo_contract_forbids_runtime_uefi_pointers(self):
        text = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        forbidden = [
            "EFI_SYSTEM_TABLE*",
            "EFI_SIMPLE_POINTER_PROTOCOL*",
            "EFI_ABSOLUTE_POINTER_PROTOCOL*",
            "EFI_BLOCK_IO_PROTOCOL*",
            "EFI_BOOT_SERVICES*",
        ]
        section = text.split("## BootInfo alvo", 1)[1].split("## Fundação x86-64", 1)[0]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertIn(token, section)

    def test_compiler_remains_host_tool_not_ui_runtime(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        forbidden = {
            "wallpaper": r"\bwallpaper\b",
            "dock": r"\bdock\b",
            "shimmer": r"\bshimmer\b",
            "installer UI": r"\binstaller_(?:screen|ui)\b",
            "OOBE UI": r"\boobe_(?:screen|ui)\b",
        }
        for label, pattern in forbidden.items():
            with self.subTest(label=label):
                self.assertIsNone(re.search(pattern, compiler, re.IGNORECASE))

    @unittest.expectedFailure
    def test_bootloader_has_completed_exit_boot_services_cutover(self):
        """Flip to a normal test once native input/storage replace UEFI bridges."""
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertIn("GetMemoryMap", boot)
        self.assertIn("ExitBootServices", boot)
        self.assertNotIn("pointer_protocol", boot)
        self.assertNotIn("block_io_protocol", boot)
        self.assertNotIn("system_table", boot)


if __name__ == "__main__":
    unittest.main()
