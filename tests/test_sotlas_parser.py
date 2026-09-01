"""Suíte de testes para o Parser Sotlas."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sotlas.lexer import Lexer
from sotlas.parser import Parser, SotlasParseError
from sotlas.ast_nodes import *
from sotlas.token_types import TK


def parse(src: str) -> SourceFileNode:
    tokens = Lexer(src, "<test>").tokenize()
    return Parser(tokens, "<test>").parse()


class TestParserModuleDecl(unittest.TestCase):
    def test_simple_module(self):
        ast = parse("module core::hal; fn dummy() -> Void {}")
        self.assertEqual(ast.module.path, ["core", "hal"])

    def test_barecore_header(self):
        ast = parse("barecore;\nmodule hal::vga; fn x() -> Void {}")
        self.assertTrue(ast.is_barecore)

    def test_import_wildcard(self):
        ast = parse("module x; import core::mem::*;")
        self.assertEqual(len(ast.imports), 1)
        self.assertIsNone(ast.imports[0].items)  # wildcard

    def test_import_named(self):
        ast = parse("module x; import core::{Alloc, Free};")
        self.assertEqual(ast.imports[0].items, ["Alloc", "Free"])


class TestParserStructDecl(unittest.TestCase):
    def test_simple_struct(self):
        src = "module x; pub struct Point { var x: Int32; var y: Int32; }"
        ast = parse(src)
        s = ast.decls[0]
        self.assertIsInstance(s, StructDeclNode)
        self.assertTrue(s.is_pub)
        self.assertEqual(s.name, "Point")
        self.assertEqual(len(s.members), 2)

    def test_struct_with_default_field(self):
        src = "module x; struct Cfg { var timeout: UInt32 = 1000; }"
        ast = parse(src)
        field = ast.decls[0].members[0]
        self.assertIsNotNone(field.default)

    def test_struct_adopts_spec(self):
        src = "module x; struct Node adopts Drop { var val: Int64; }"
        ast = parse(src)
        self.assertIn("Drop", ast.decls[0].adopts)


class TestParserClassDecl(unittest.TestCase):
    def test_class_with_base(self):
        src = "module x; class Dog : Animal adopts Sound { var name: String; }"
        ast = parse(src)
        c = ast.decls[0]
        self.assertIsInstance(c, ClassDeclNode)
        self.assertEqual(c.base, "Animal")
        self.assertIn("Sound", c.adopts)

    def test_class_moldable_method(self):
        src = """module x;
        class Shape {
            moldable fn area() -> Float64 { return 0.0; }
        }"""
        ast = parse(src)
        m = ast.decls[0].members[0]
        self.assertIsInstance(m, FnDeclNode)
        self.assertTrue(m.is_moldable)


class TestParserTypeSystem(unittest.TestCase):
    def test_rawphys_pointer(self):
        src = "module x; fn vga(p: *rawphys UInt16) -> Void {}"
        ast = parse(src)
        fn = ast.decls[0]
        t = fn.params[0].type_ann
        self.assertTrue(t.is_topology_ptr)
        self.assertEqual(t.topology_ptr, TK.KW_RAWPHYS)

    def test_virtmap_pointer(self):
        src = "module x; fn map(p: *virtmap UInt64) -> Void {}"
        ast = parse(src)
        t = ast.decls[0].params[0].type_ann
        self.assertEqual(t.topology_ptr, TK.KW_VIRTMAP)

    def test_portwire_pointer(self):
        src = "module x; fn io(p: *portwire UInt8) -> Void {}"
        ast = parse(src)
        t = ast.decls[0].params[0].type_ann
        self.assertEqual(t.topology_ptr, TK.KW_PORTWIRE)

    def test_sole_ownership(self):
        src = "module x; fn alloc() -> sole Node { return nil; }"
        ast = parse(src)
        t = ast.decls[0].ret
        self.assertEqual(t.ownership, TK.KW_SOLE)

    def test_island_ownership(self):
        src = "module x; fn isolate(b: island Buffer) -> Void {}"
        ast = parse(src)
        t = ast.decls[0].params[0].type_ann
        self.assertEqual(t.ownership, TK.KW_ISLAND)

    def test_optional_type(self):
        src = "module x; fn find() -> Int32? { return nil; }"
        ast = parse(src)
        t = ast.decls[0].ret
        self.assertTrue(t.is_optional)

    def test_array_type(self):
        src = "module x; fn buf() -> [UInt8; 512] { return 0; }"
        ast = parse(src)
        t = ast.decls[0].ret
        self.assertTrue(t.is_array)


class TestParserStatements(unittest.TestCase):
    def _fn_stmts(self, body_src: str) -> list:
        src = f"module x; fn f() -> Void {{ {body_src} }}"
        ast = parse(src)
        return ast.decls[0].body

    def test_let_decl(self):
        stmts = self._fn_stmts("let x: Int64 = 42;")
        self.assertIsInstance(stmts[0], LocalVarDeclNode)
        self.assertFalse(stmts[0].is_var)
        self.assertEqual(stmts[0].name, "x")

    def test_var_decl(self):
        stmts = self._fn_stmts("var y: UInt32 = 0;")
        self.assertTrue(stmts[0].is_var)

    def test_assignment(self):
        stmts = self._fn_stmts("let x: Int32 = 0; x = 5;")
        self.assertIsInstance(stmts[1], AssignmentNode)
        self.assertEqual(stmts[1].op, TK.ASSIGN)

    def test_if_else(self):
        stmts = self._fn_stmts("if x > 0 { return; } else { return; }")
        self.assertIsInstance(stmts[0], IfNode)

    def test_while_loop(self):
        stmts = self._fn_stmts("while i < 10 { i = i + 1; }")
        self.assertIsInstance(stmts[0], WhileNode)

    def test_for_in(self):
        stmts = self._fn_stmts("for item in items { return; }")
        self.assertIsInstance(stmts[0], ForNode)
        self.assertEqual(stmts[0].var, "item")

    def test_match(self):
        stmts = self._fn_stmts("match x { 0 => { return; } _ => { return; } }")
        self.assertIsInstance(stmts[0], MatchNode)
        self.assertEqual(len(stmts[0].arms), 2)

    def test_return(self):
        stmts = self._fn_stmts("return 42;")
        self.assertIsInstance(stmts[0], ReturnNode)

    def test_break_continue(self):
        stmts = self._fn_stmts("while true { break; continue; }")
        body = stmts[0].body
        self.assertIsInstance(body[0], BreakNode)
        self.assertIsInstance(body[1], ContinueNode)

    def test_handover(self):
        stmts = self._fn_stmts("handover node;")
        self.assertIsInstance(stmts[0], HandoverNode)

    def test_quarantine(self):
        stmts = self._fn_stmts("quarantine buf;")
        self.assertIsInstance(stmts[0], QuarantineNode)

    def test_clinch_revert(self):
        stmts = self._fn_stmts("clinch { return; } revert { return; }")
        self.assertIsInstance(stmts[0], ClinchNode)
        self.assertTrue(len(stmts[0].revert) > 0)

    def test_quench(self):
        stmts = self._fn_stmts("quench { return; }")
        self.assertIsInstance(stmts[0], QuenchNode)

    def test_gate(self):
        stmts = self._fn_stmts("gate(x > 0) { return; }")
        self.assertIsInstance(stmts[0], GateNode)

    def test_emit(self):
        stmts = self._fn_stmts('emit("nop" : : : "memory");')
        self.assertIsInstance(stmts[0], EmitNode)
        self.assertEqual(stmts[0].template, "nop")

    def test_guard(self):
        stmts = self._fn_stmts("guard x != nil else { return; }")
        self.assertIsInstance(stmts[0], GuardNode)

    def test_unsafe(self):
        stmts = self._fn_stmts("unsafe { return; }")
        self.assertIsInstance(stmts[0], UnsafeBlockNode)

    def test_rebound(self):
        stmts = self._fn_stmts("rebound;")
        self.assertIsInstance(stmts[0], ReboundNode)


class TestParserExpressions(unittest.TestCase):
    def _expr(self, expr_src: str) -> ExprNode:
        src = f"module x; fn f() -> Void {{ let r = {expr_src}; }}"
        ast = parse(src)
        return ast.decls[0].body[0].init

    def test_binary_add(self):
        e = self._expr("a + b")
        self.assertIsInstance(e, BinaryExprNode)
        self.assertEqual(e.op, TK.PLUS)

    def test_unary_minus(self):
        e = self._expr("-x")
        self.assertIsInstance(e, UnaryExprNode)
        self.assertEqual(e.op, TK.MINUS)

    def test_bit_slice(self):
        e = self._expr("reg.slit[3..7]")
        self.assertIsInstance(e, BitSliceExprNode)

    def test_bit_notch(self):
        e = self._expr("reg.notch[4]")
        self.assertIsInstance(e, BitNotchExprNode)

    def test_bit_strand(self):
        e = self._expr("val.strand")
        self.assertIsInstance(e, BitStrandExprNode)

    def test_cast(self):
        e = self._expr("x as UInt8")
        self.assertIsInstance(e, CastExprNode)

    def test_call(self):
        e = self._expr("foo(1, 2)")
        self.assertIsInstance(e, CallExprNode)

    def test_array_literal(self):
        e = self._expr("[1, 2, 3]")
        self.assertIsInstance(e, ArrayLitExprNode)
        self.assertEqual(len(e.elements), 3)

    def test_optional_chain(self):
        e = self._expr("ptr?")
        self.assertIsInstance(e, OptionalChainExprNode)

    def test_force_unwrap(self):
        e = self._expr("ptr!")
        self.assertIsInstance(e, ForceUnwrapExprNode)

    def test_nil_coalescing(self):
        e = self._expr("val ?? 0")
        self.assertIsInstance(e, BinaryExprNode)
        self.assertEqual(e.op, TK.NIL_COAL)


class TestParserTrapFn(unittest.TestCase):
    def test_trapfn_parsed(self):
        src = "module x; trapfn kbd_isr(frame: *rawphys UInt8) -> Void { rebound; }"
        ast = parse(src)
        fn = ast.decls[0]
        self.assertIsInstance(fn, TrapFnDeclNode)
        self.assertEqual(fn.name, "kbd_isr")
        self.assertIsInstance(fn.body[-1], ReboundNode)


class TestParserErrors(unittest.TestCase):
    def test_missing_module(self):
        with self.assertRaises(SotlasParseError):
            parse("fn x() {}")

    def test_missing_semicolon_in_module(self):
        with self.assertRaises(SotlasParseError):
            parse("module core\nfn x() {}")

    def test_unexpected_token_in_top_level(self):
        with self.assertRaises(SotlasParseError):
            parse("module x; 42;")

    def test_error_has_location(self):
        try:
            parse("module x;\nfn bad")
        except SotlasParseError as e:
            self.assertIn(":", str(e))


class TestParserFixtures(unittest.TestCase):
    def test_sample_counter(self):
        path = ROOT / "tests" / "fixtures" / "sample_counter.sotlas"
        ast = parse(path.read_text(encoding="utf-8"))
        self.assertEqual(ast.module.path, ["core", "counter"])
        struct_names = [d.name for d in ast.decls if isinstance(d, StructDeclNode)]
        fn_names = [d.name for d in ast.decls if isinstance(d, FnDeclNode)]
        self.assertIn("Counter", struct_names)
        self.assertIn("sum", fn_names)

    def test_barecore_vga(self):
        path = ROOT / "tests" / "fixtures" / "barecore_vga.sotlas"
        ast = parse(path.read_text(encoding="utf-8"))
        self.assertTrue(ast.is_barecore)
        self.assertEqual(ast.module.path, ["hal", "vga"])
        trapfns = [d for d in ast.decls if isinstance(d, TrapFnDeclNode)]
        self.assertTrue(len(trapfns) > 0, "deve ter pelo menos um trapfn")
        self.assertEqual(trapfns[0].name, "keyboard_isr")

    def test_srg_scope(self):
        path = ROOT / "tests" / "fixtures" / "srg_scope.sotlas"
        ast = parse(path.read_text(encoding="utf-8"))
        fn_names = [d.name for d in ast.decls if isinstance(d, FnDeclNode)]
        self.assertIn("create_node", fn_names)
        self.assertIn("process_isolated", fn_names)
        spec_names = [d.name for d in ast.decls if isinstance(d, SpecDeclNode)]
        self.assertIn("Owned", spec_names)


if __name__ == "__main__":
    unittest.main()
