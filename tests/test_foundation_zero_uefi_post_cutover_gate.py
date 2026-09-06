from pathlib import Path
import re
import unittest

from tools.scripts.audit_post_cutover import audit

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
BOOT = ROOT / "boot/uefi_bootloader.sotlas"
FIXTURE = ROOT / "tools/scripts/extend_foundation_fixture.py"

FIRMWARE_NAME = re.compile(
    r"(?:^|_)(?:uefi|efi)(?:_|$)|BootServices|RuntimeServices|SystemTable|"
    r"LocateProtocol|ReadBlocks|WriteBlocks|Stall|baken_runtime_run|baken_efi_",
    re.IGNORECASE,
)


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


class FoundationZeroUefiPostCutoverGateTests(unittest.TestCase):
    def test_reachable_post_cutover_call_graph_has_no_firmware_reentry(self):
        report = audit()
        self.assertFalse(report["firmware_violations"], report)
        self.assertGreater(report["reachable_functions"], 100, report)
        suspicious_opaque = [
            name for name in report["opaque_calls"] if FIRMWARE_NAME.search(name)
        ]
        self.assertEqual(suspicious_opaque, [], report)

    def test_post_cutover_context_contains_only_stable_handoff_data(self):
        text = POST.read_text(encoding="utf-8")
        struct = text.split("pub struct PostCutoverContext {", 1)[1].split("}", 1)[0]
        for forbidden in (
            "system_table",
            "pointer_protocol",
            "block_io_protocol",
            "install_target_block_io_protocol",
            "BootServices",
            "RuntimeServices",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, struct)
        for required in (
            "root_physical",
            "stack_top",
            "framebuffer_base",
            "framebuffer_size",
            "memory_map_base",
            "memory_map_size",
            "memory_descriptor_size",
            "acpi_rsdp",
            "page_table_arena_physical_base",
            "page_table_pages_used",
        ):
            with self.subTest(required=required):
                self.assertIn(required, struct)

    def test_post_cutover_source_cannot_call_legacy_runtime_or_firmware_bridge(self):
        code = strip_comments(POST.read_text(encoding="utf-8"))
        for forbidden in (
            "baken_runtime_run(",
            "baken_efi_",
            "uefi_",
            "BootServices",
            "RuntimeServices",
            "LocateProtocol",
            "ReadBlocks",
            "WriteBlocks",
            "Stall(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_successful_exit_has_only_native_stack_handoff_after_firmware_shutdown(self):
        boot = BOOT.read_text(encoding="utf-8")
        marker = "if (status != EFI_SUCCESS) return status;"
        self.assertIn("baken_exit_boot_services_final(", boot)
        self.assertIn(marker, boot)
        tail = strip_comments(boot[boot.rfind(marker) + len(marker):])
        self.assertIn("x86_stack_switch_to_post_cutover_raw(", tail)
        self.assertNotIn("baken_kernel_main(&boot_info)", tail)
        for forbidden in (
            "BootServices",
            "RuntimeServices",
            "SystemTable",
            "LocateProtocol",
            "ReadBlocks",
            "WriteBlocks",
            "pointer_protocol",
            "block_io_protocol",
            "baken_runtime_run",
            "baken_efi_",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, tail)

    def test_final_foundation_order_reaches_pat_then_terminal_marker(self):
        text = POST.read_text(encoding="utf-8")
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        nvme = entry.index("foundation_nvme_probe()")
        pat = entry.index("active_framebuffer_write_combining(", nvme)
        terminal = entry.index("x86_serial_write_stage_marker('J' as u8)", pat)
        self.assertLess(nvme, pat)
        self.assertLess(pat, terminal)

    def test_qemu_fixture_verifier_requires_terminal_post_cutover_proof(self):
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("'BAKEN:STEP=)'", text)
        self.assertIn("'BAKEN:STEP=%'", text)
        self.assertIn("'BAKEN:STEP=J'", text)


if __name__ == "__main__":
    unittest.main()
