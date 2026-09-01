"""Suíte de testes para o Analisador Semântico Sotlas."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sotlas.lexer import Lexer
from sotlas.parser import Parser
from sotlas.sema import Sema, SotlasSemaError
from sotlas.ast_nodes import SourceFileNode


def parse_check(src: str) -> SourceFileNode:
    """Executa o pipeline léxico → sintático → semântico completo."""
    tokens = Lexer(src, "<test>").tokenize()
    ast = Parser(tokens, "<test>").parse()
    Sema(ast, "<test>").check()
    return ast


def check_raises(src: str, fragment: str) -> None:
    """Asserta que check levanta SotlasSemaError contendo o fragmento."""
    tokens = Lexer(src, "<test>").tokenize()
    ast = Parser(tokens, "<test>").parse()
    with unittest.TestCase().assertRaisesRegex(SotlasSemaError, fragment):
        Sema(ast, "<test>").check()


class TestSemaBasicDeclarations(unittest.TestCase):
    def test_simple_function_ok(self):
        src = "module x; pub fn add(a: Int32, b: Int32) -> Int32 { return a + b; }"
        parse_check(src)   # não deve levantar

    def test_struct_with_fields_ok(self):
        src = "module x; pub struct Point { var x: Int64; var y: Int64; }"
        parse_check(src)

    def test_const_decl_ok(self):
        src = "module x; const MAX: UInt32 = 1024;"
        parse_check(src)


class TestSemaSymbolResolution(unittest.TestCase):
    def test_undeclared_symbol_raises(self):
        src = "module x; fn f() -> Void { let r = missing; }"
        with self.assertRaises(SotlasSemaError) as ctx:
            parse_check(src)
        self.assertIn("não declarado", str(ctx.exception))

    def test_declared_symbol_ok(self):
        src = "module x; fn f() -> Void { let x: Int32 = 0; let y: Int32 = x; }"
        parse_check(src)   # não deve levantar

    def test_function_param_visible_in_body(self):
        src = "module x; fn f(x: Int32) -> Int32 { return x; }"
        parse_check(src)

    def test_unknown_struct_type_raises(self):
        src = "module x; fn f(p: UnknownType) -> Void {}"
        with self.assertRaises(SotlasSemaError) as ctx:
            parse_check(src)
        self.assertIn("não declarado", str(ctx.exception))

    def test_known_struct_type_ok(self):
        src = """module x;
        struct Vec2 { var x: Int64; var y: Int64; }
        fn f(v: Vec2) -> Void {}
        """
        parse_check(src)


class TestSemaBarecoreIsolation(unittest.TestCase):
    """Verifica que módulos barecore rejeitam construtos de alocação dinâmica."""

    def test_barecore_rejects_co_owned(self):
        src = """barecore;
        module hal::x;
        fn f(b: co-owned UInt8) -> Void {}
        """
        with self.assertRaises(SotlasSemaError) as ctx:
            parse_check(src)
        self.assertIn("co-owned", str(ctx.exception))

    def test_barecore_rejects_class_decl(self):
        src = """barecore;
        module hal::x;
        class Foo {}
        """
        with self.assertRaises(SotlasSemaError) as ctx:
            parse_check(src)
        self.assertIn("barecore", str(ctx.exception))

    def test_barecore_allows_sole(self):
        src = """barecore;
        module hal::x;
        fn alloc(p: sole UInt8) -> Void {}
        """
        parse_check(src)  # sole é permitido em barecore

    def test_barecore_allows_direct(self):
        src = """barecore;
        module hal::x;
        fn io(p: direct UInt8) -> Void {}
        """
        parse_check(src)

    def test_barecore_allows_rawphys(self):
        src = """barecore;
        module hal::x;
        fn mmio(p: *rawphys UInt32) -> Void {}
        """
        parse_check(src)

    def test_non_barecore_allows_co_owned(self):
        src = """module app::x;
        struct Buf { var data: co-owned UInt8; }
        """
        parse_check(src)  # co-owned é válido fora de barecore


class TestSemaSRGOwnership(unittest.TestCase):
    """Verifica regras semânticas de posse SRG."""

    def test_handover_on_sole_ok(self):
        src = """module x;
        struct Node { var val: Int32; }
        fn transfer(n: sole Node) -> Void { handover n; }
        """
        parse_check(src)

    def test_quarantine_marks_island(self):
        src = """module x;
        struct Buf { var len: UInt32; }
        fn isolate(b: Buf) -> Void { quarantine b; }
        """
        parse_check(src)  # quarantine é válido sem verificação de tipo estrito no MVP

    def test_fn_with_island_param_ok(self):
        src = """module x;
        struct Buffer { var len: UInt32; }
        fn process(buf: island Buffer) -> Void { return; }
        """
        parse_check(src)

    def test_fn_with_whisper_param_ok(self):
        src = """module x;
        struct Node { var val: Int32; }
        fn peek(n: whisper Node) -> Int32 { return n.val; }
        """
        parse_check(src)


class TestSemaControlFlow(unittest.TestCase):
    def test_if_ok(self):
        src = "module x; fn f(x: Int32) -> Void { if x > 0 { return; } }"
        parse_check(src)

    def test_while_ok(self):
        src = "module x; fn f() -> Void { let i: Int32 = 0; while i < 10 { i = i + 1; } }"
        parse_check(src)

    def test_for_in_ok(self):
        src = "module x; fn f(items: UInt8) -> Void { for item in items { return; } }"
        parse_check(src)

    def test_clinch_ok(self):
        src = """module x;
        fn f() -> Void {
            clinch { return; } revert { return; }
        }"""
        parse_check(src)

    def test_quench_ok(self):
        src = "module x; fn f() -> Void { quench { return; } }"
        parse_check(src)

    def test_gate_ok(self):
        src = "module x; fn f(x: Int32) -> Void { gate(x > 0) { return; } }"
        parse_check(src)

    def test_match_ok(self):
        src = """module x;
        fn f(x: Int32) -> Void {
            match x { 0 => { return; } _ => { return; } }
        }"""
        parse_check(src)


class TestSemaHardware(unittest.TestCase):
    def test_emit_ok(self):
        src = """barecore;
        module hal::x;
        fn nop() -> Void { unsafe { emit("nop"); } }
        """
        parse_check(src)

    def test_trapfn_with_rebound_ok(self):
        src = """barecore;
        module hal::x;
        trapfn timer_isr(frame: *rawphys UInt8) -> Void { rebound; }
        """
        parse_check(src)


class TestSemaSpecs(unittest.TestCase):
    def test_struct_adopts_unknown_spec_ok(self):
        """No MVP a verificação de conformidade com spec é leve — apenas verifica que o spec existe."""
        src = """module x;
        spec Hashable { fn hash() -> UInt64; }
        struct Key adopts Hashable {
            var value: UInt64;
            fn hash() -> UInt64 { return value; }
        }
        """
        parse_check(src)


class TestSemaFixtures(unittest.TestCase):
    def test_sample_counter_passes_sema(self):
        path = ROOT / "tests" / "fixtures" / "sample_counter.sotlas"
        text = path.read_text(encoding="utf-8")
        parse_check(text)

    def test_srg_scope_passes_sema(self):
        path = ROOT / "tests" / "fixtures" / "srg_scope.sotlas"
        text = path.read_text(encoding="utf-8")
        parse_check(text)


if __name__ == "__main__":
    unittest.main()
