"""Testes unitários e de integração para o servidor LSP Sotlas Bootstrap (lsp.py)."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "sotlas_compile"))
SPEC_LSP = importlib.util.spec_from_file_location("lsp", ROOT / "tools" / "sotlas_compile" / "lsp.py")
lsp = importlib.util.module_from_spec(SPEC_LSP)
sys.modules["lsp"] = lsp
SPEC_LSP.loader.exec_module(lsp)


SAMPLE_SOURCE = """
module test::app;
import core::mem::*;
import core::serial::*;

pub enum Mode {
    Fast = 1,
    Safe = 2
}

pub struct Config {
    mode: Mode;
    retries: u32;
}

pub fn run_app(cfg: *mut Config) -> bool {
    let s: Mode = Mode::Fast;
    serial_init(COM1);
    return true;
}
"""


class SotlasLspServerTests(unittest.TestCase):
    def setUp(self):
        self.server = lsp.SotlasLanguageServer()
        self.entry_path = ROOT / "bootstrap" / "sotlas" / "kernel" / "main.st"
        self.entry_uri = lsp.path_to_uri(self.entry_path)

    def test_validate_publishes_no_diagnostics_on_valid_source(self):
        diagnostics = self.server.validate(self.entry_uri, self.entry_path.read_text(encoding="utf-8"))
        self.assertEqual(len(diagnostics), 0)

    def test_validate_publishes_diagnostic_on_syntax_error(self):
        bad_uri = "file:///test/bad.st"
        diagnostics = self.server.validate(bad_uri, "module bad; fn invalid() { return @; }")
        self.assertGreater(len(diagnostics), 0)
        self.assertIn("caractere léxico inválido", diagnostics[0]["message"])

    def test_completion_returns_keywords_and_types(self):
        uri = "file:///test/comp.st"
        self.server.validate(uri, "module test::comp;\nfn test() {\n    \n}")
        items = self.server.completion(uri, line=2, character=4)
        labels = [item["label"] for item in items]
        self.assertIn("let", labels)
        self.assertIn("while", labels)
        self.assertIn("u32", labels)
        self.assertIn("usize", labels)

    def test_completion_suggests_attributes_on_at(self):
        uri = "file:///test/attr.st"
        self.server.validate(uri, "module test::attr;\n@")
        items = self.server.completion(uri, line=1, character=1)
        labels = [item["label"] for item in items]
        self.assertIn("@repr(C)", labels)
        self.assertIn("@packed", labels)
        self.assertIn("@system", labels)
        self.assertIn("@export", labels)

    def test_completion_suggests_enum_variants_on_double_colon(self):
        uri = "file:///test/enum_comp.st"
        source = "module test::enum_comp;\npub enum Status { Active = 1, Inactive = 0 }\nfn run() { Status::\n}"
        self.server.validate(uri, source)
        items = self.server.completion(uri, line=2, character=19)
        labels = [item["label"] for item in items]
        self.assertIn("Active", labels)
        self.assertIn("Inactive", labels)

    def test_completion_suggests_imported_functions(self):
        source = self.entry_path.read_text(encoding="utf-8")
        self.server.validate(self.entry_uri, source)
        items = self.server.completion(self.entry_uri, line=10, character=0)
        labels = [item["label"] for item in items]
        # Funções importadas de core::mem, core::serial, core::vga
        self.assertIn("zero_memory", labels)
        self.assertIn("serial_init", labels)
        self.assertIn("clear", labels)
        self.assertIn("rgb", labels)

    def test_hover_on_functions_structs_and_enums(self):
        uri = "file:///test/hover.st"
        self.server.validate(uri, SAMPLE_SOURCE)

        # Hover em função (linha 15, col 8: run_app)
        hover_fn = self.server.hover(uri, line=15, character=8)
        self.assertIsNotNone(hover_fn)
        self.assertIn("fn run_app", hover_fn["contents"]["value"])

        # Hover em struct (linha 10, col 12: Config)
        hover_st = self.server.hover(uri, line=10, character=12)
        self.assertIsNotNone(hover_st)
        self.assertIn("struct Config", hover_st["contents"]["value"])

        # Hover em enum (linha 5, col 10: Mode)
        hover_en = self.server.hover(uri, line=5, character=10)
        self.assertIsNotNone(hover_en)
        self.assertIn("enum Mode", hover_en["contents"]["value"])

    def test_definition_locates_symbol_declaration(self):
        source = self.entry_path.read_text(encoding="utf-8")
        self.server.validate(self.entry_uri, source)

        # Procura a definição de 'serial_init' chamada em main.st
        lines = source.splitlines()
        serial_line_idx = next(i for i, l in enumerate(lines) if "serial_init" in l)
        serial_char_idx = lines[serial_line_idx].find("serial_init")

        target = self.server.definition(self.entry_uri, serial_line_idx, serial_char_idx)
        self.assertIsNotNone(target)
        self.assertIn("serial.st", target["uri"])

    def test_document_symbols_extracts_tree(self):
        uri = "file:///test/symbols.st"
        self.server.validate(uri, SAMPLE_SOURCE)
        symbols = self.server.document_symbols(uri)
        names = [s["name"] for s in symbols]
        self.assertIn("Mode", names)
        self.assertIn("Config", names)
        self.assertIn("run_app", names)


if __name__ == "__main__":
    unittest.main()
