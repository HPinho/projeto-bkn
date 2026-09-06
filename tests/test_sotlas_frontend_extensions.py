"""Regressões da gramática/lowering usados pelo compilador Sotlas modular."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.sotlas_compile import bootstrap

ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "tools" / "sotlas_compile" / "compiler.py"


class SotlasFrontendExtensionTests(unittest.TestCase):
    def test_lexer_and_parser_accept_complete_compound_assignment_family(self):
        token_kinds = {
            token.kind
            for token in bootstrap.lex("a += 1; a -= 1; a *= 2; a /= 2; a %= 3; a &= 7; a |= 8; a ^= 4; a <<= 1; a >>= 1;")
        }
        for operator in ("+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="):
            self.assertIn(operator, token_kinds)

        source = """
        module test::compound;
        pub fn exercise() -> u32 {
            let mut value: u32 = 64;
            value ^= 3;
            value <<= 1;
            value >>= 2;
            value %= 7;
            return value;
        }
        """
        module = bootstrap.parse(source)
        bootstrap.check(module)
        emitted = bootstrap.emit_c(module, include_preamble=False)
        self.assertIn("value = (value ^ 3);", emitted)
        self.assertIn("value = (value << 1);", emitted)
        self.assertIn("value = (value >> 2);", emitted)
        self.assertIn("value = (value % 7);", emitted)

    def test_mutable_local_array_remains_writable_and_c_keyword_is_mangled(self):
        source = """
        module test::mutable_array;
        pub fn exercise() -> u16 {
            let mut short: [u16; 4] = [0; 4];
            short[0] = 7;
            short[1] ^= 3;
            return short[0];
        }
        """
        module = bootstrap.parse(source)
        bootstrap.check(module)
        emitted = bootstrap.emit_c(module, include_preamble=False)
        self.assertIn("uint16_t sotlas_c_kw_short[4] = {0};", emitted)
        self.assertIn("sotlas_c_kw_short[0] = 7;", emitted)
        self.assertIn("sotlas_c_kw_short[1] = (sotlas_c_kw_short[1] ^ 3);", emitted)
        self.assertNotIn("static const uint16_t sotlas_c_kw_short", emitted)
        self.assertNotIn(_marker := "__SOTLAS_MUT_", emitted, _marker)

    def test_defer_uses_the_same_compound_assignment_grammar(self):
        source = """
        module test::defer_compound;
        pub fn exercise() -> u32 {
            let mut value: u32 = 1;
            defer value <<= 1;
            return value;
        }
        """
        module = bootstrap.parse(source)
        bootstrap.check(module)
        emitted = bootstrap.emit_c(module, include_preamble=False)
        self.assertIn("value = (value << 1);", emitted)

    def test_direct_compiler_cli_installs_the_same_frontend_extensions(self):
        source = """
        module test::direct_cli;
        pub fn exercise() -> u16 {
            let mut short: [u16; 4] = [0; 4];
            short[0] = 7;
            short[1] ^= 3;
            return short[0];
        }
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source_path = temp / "direct_cli.sotlas"
            output_path = temp / "direct_cli.c"
            source_path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(COMPILER), "bootstrap-emit-c", str(source_path), "-o", str(output_path)],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            emitted = output_path.read_text(encoding="utf-8")
            self.assertIn("uint16_t sotlas_c_kw_short[4] = {0};", emitted)
            self.assertIn("sotlas_c_kw_short[0] = 7;", emitted)
            self.assertIn("sotlas_c_kw_short[1] = (sotlas_c_kw_short[1] ^ 3);", emitted)
            self.assertNotIn("static const uint16_t sotlas_c_kw_short", emitted)


if __name__ == "__main__":
    unittest.main()
