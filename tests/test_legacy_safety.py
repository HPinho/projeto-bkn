#!/usr/bin/env python3
"""Regressões de arquitetura e identidade da rota Sotlas."""
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[1]
class LegacySafetyTests(unittest.TestCase):
    def test_sotlas_tree_has_unique_module_declarations_and_no_retired_runtime(self):
        modules={}
        for root in (ROOT/"kernel",ROOT/"libbkn",ROOT/"boot",ROOT/"apps"):
            if not root.is_dir(): continue
            for path in root.rglob("*.sotlas"):
                text=path.read_text(encoding="utf-8"); match=re.search(r"(?m)^\s*module\s+([A-Za-z_][\w:]*)\s*;",text)
                if not match: continue
                name=match.group(1); self.assertNotIn(name,modules,f"módulo Sotlas duplicado: {name}"); modules[name]=path.relative_to(ROOT).as_posix()
        self.assertIn("kernel::main",modules); self.assertIn("kernel::arch::x86_64::post_cutover",modules); self.assertIn("kernel::baken_native_runtime",modules); self.assertNotIn("kernel::baken_runtime",modules)
        self.assertFalse((ROOT/"kernel/src/baken_runtime.sotlas").exists())
    def test_no_unlinked_sotlas_test_module_remains(self):
        for path in (ROOT/"tests").rglob("*.sotlas"): self.assertIn("fixtures",path.parts,path)
    def test_sotlas_toolchain_and_vscode_extension_are_canonical(self):
        compiler=(ROOT/"tools/sotlas_compile/compiler.py").read_text(encoding="utf-8"); cmake=(ROOT/"CMakeLists.txt").read_text(encoding="utf-8"); extension=(ROOT/"tools/vscode-sotlas/package.json").read_text(encoding="utf-8")
        self.assertIn("class SotlasError",compiler); self.assertIn("tools/sotlas_compile/compiler.py",cmake); self.assertIn('".sotlas"',extension); self.assertIn('".sth"',extension); self.assertIn('"icon": "./icons/sotlas-icon.svg"',extension)
        self.assertTrue((ROOT/"tools/vscode-sotlas/icons/sotlas-icon.svg").is_file()); self.assertTrue((ROOT/"tools/vscode-sotlas/icons/sotlas-logo.svg").is_file())
    def test_uefi_handoff_uses_one_shared_versioned_contract(self):
        header=(ROOT/"kernel/include/baken_boot_info.h").read_text(encoding="utf-8"); boot=(ROOT/"boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        for token in ("BAKEN_BOOT_INFO_VERSION 2U","offsetof(BakenBootInfo, version) == 80","offsetof(BakenBootInfo, page_table_arena_physical_base) == 120","offsetof(BakenBootInfo, loaded_image_physical_base) == 144","offsetof(BakenBootInfo, transition_stack_physical_base) == 168","_Static_assert(sizeof(BakenBootInfo) == 192"): self.assertIn(token,header)
        for token in ('#include "baken_boot_info.h"',"boot_info.version = BAKEN_BOOT_INFO_VERSION","return EFI_UNSUPPORTED;","return EFI_ABORTED;"): self.assertIn(token,boot)
    def test_kernel_has_zero_gfx_occurrences(self):
        kernel_src=ROOT/"kernel/src"; offenders={}
        for file in list(kernel_src.glob("*.sotlas"))+list(kernel_src.glob("*.c")):
            count=file.read_text(encoding="utf-8",errors="ignore").count("gfx_")
            if count: offenders[file.name]=count
        self.assertEqual(offenders,{},f"Ainda existem chamadas gfx_ no kernel: {offenders}")
if __name__ == "__main__": unittest.main()
