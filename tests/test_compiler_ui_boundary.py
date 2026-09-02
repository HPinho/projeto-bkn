#!/usr/bin/env python3
"""Impede que UI volte a ser implementada dentro do compilador Sotlas."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CompilerUiBoundaryTests(unittest.TestCase):
    def test_compiler_contains_no_visual_domain_tokens(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        forbidden = {
            "gfx API": r"\bgfx_",
            "draw API": r"\bdraw_",
            "wallpaper": r"\bwallpaper\b",
            "dock": r"\bdock\b",
            "tela": r"\btela\b",
            "screen": r"\bscreen\b",
        }
        for label, pattern in forbidden.items():
            with self.subTest(label=label):
                self.assertIsNone(re.search(pattern, compiler, re.IGNORECASE))

    def test_bootstrap_preamble_has_no_ui_forward_declarations(self):
        bootstrap = (ROOT / "tools/sotlas_compile/bootstrap.py").read_text(encoding="utf-8")
        preamble = bootstrap.split('PREAMBLE = """', 1)[1].split('"""', 1)[0]
        self.assertNotRegex(preamble, r"\b(?:gfx_|draw_|wallpaper|dock|screen|tela)")

    def test_monolithic_bridge_is_absent(self):
        self.assertFalse((ROOT / "kernel/src/baken_kernel_all.c").exists())


if __name__ == "__main__":
    unittest.main()
