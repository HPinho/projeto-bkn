"""Suíte de testes para o Lexer Sotlas."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sotlas.lexer import Lexer, SotlasLexError, Token
from sotlas.token_types import TK


def lex(src: str) -> list[Token]:
    return Lexer(src, "<test>").tokenize()


def kinds(src: str) -> list[TK]:
    return [t.kind for t in lex(src) if t.kind != TK.EOF]


class TestLexerKeywords(unittest.TestCase):
    def test_barecore(self):
        self.assertIn(TK.KW_BARECORE, kinds("barecore;"))

    def test_module_and_dcolon(self):
        tks = kinds("module core::hal;")
        self.assertEqual(tks, [TK.KW_MODULE, TK.IDENT, TK.DCOLON, TK.IDENT, TK.SEMICOLON])

    def test_fn_keyword(self):
        self.assertIn(TK.KW_FN, kinds("fn main() {}"))

    def test_trapfn_keyword(self):
        self.assertIn(TK.KW_TRAPFN, kinds("trapfn isr() {}"))

    def test_class_keyword(self):
        self.assertIn(TK.KW_CLASS, kinds("class Foo {}"))

    def test_mesh_keyword(self):
        self.assertIn(TK.KW_MESH, kinds("mesh Frame {}"))

    def test_spec_keyword(self):
        self.assertIn(TK.KW_SPEC, kinds("spec Drop {}"))


class TestLexerSRGOwnership(unittest.TestCase):
    def test_sole(self):
        self.assertIn(TK.KW_SOLE, kinds("let x: sole Node;"))

    def test_island(self):
        self.assertIn(TK.KW_ISLAND, kinds("let b: island Buffer;"))

    def test_whisper(self):
        self.assertIn(TK.KW_WHISPER, kinds("let r: whisper Node;"))

    def test_direct(self):
        self.assertIn(TK.KW_DIRECT, kinds("let p: direct UInt8;"))

    def test_co_owned_compound(self):
        """'co-owned' deve ser resolvido como TK.KW_CO_OWNED em pós-processamento."""
        tks = kinds("let shared: co-owned Buffer;")
        self.assertIn(TK.KW_CO_OWNED, tks)
        # Não deve aparecer como IDENT "co", MINUS, IDENT "owned" separados
        values = [t.value for t in lex("let shared: co-owned Buffer;") if t.kind != TK.EOF]
        self.assertNotIn("co", values)

    def test_handover(self):
        self.assertIn(TK.KW_HANDOVER, kinds("handover x;"))

    def test_quarantine(self):
        self.assertIn(TK.KW_QUARANTINE, kinds("quarantine buf;"))


class TestLexerTopologyPointers(unittest.TestCase):
    def test_rawphys(self):
        self.assertIn(TK.KW_RAWPHYS, kinds("*rawphys UInt8"))

    def test_virtmap(self):
        self.assertIn(TK.KW_VIRTMAP, kinds("*virtmap UInt32"))

    def test_portwire(self):
        self.assertIn(TK.KW_PORTWIRE, kinds("*portwire UInt8"))

    def test_dmazone(self):
        self.assertIn(TK.KW_DMAZONE, kinds("*dmazone UInt64"))

    def test_voidzero(self):
        self.assertIn(TK.KW_VOIDZERO, kinds("*voidzero"))


class TestLexerHardwareStatements(unittest.TestCase):
    def test_clinch(self):
        self.assertIn(TK.KW_CLINCH, kinds("clinch {}"))

    def test_revert(self):
        self.assertIn(TK.KW_REVERT, kinds("revert {}"))

    def test_quench(self):
        self.assertIn(TK.KW_QUENCH, kinds("quench {}"))

    def test_gate(self):
        self.assertIn(TK.KW_GATE, kinds("gate(x) {}"))

    def test_emit(self):
        self.assertIn(TK.KW_EMIT, kinds('emit("nop");'))

    def test_rebound(self):
        self.assertIn(TK.KW_REBOUND, kinds("rebound;"))


class TestLexerBitAccessors(unittest.TestCase):
    def test_slit(self):
        self.assertIn(TK.KW_SLIT, kinds("x.slit[0..7]"))

    def test_notch(self):
        self.assertIn(TK.KW_NOTCH, kinds("x.notch[3]"))

    def test_strand(self):
        self.assertIn(TK.KW_STRAND, kinds("x.strand"))

    def test_dotdot_operator(self):
        self.assertIn(TK.DOTDOT, kinds("0..7"))


class TestLexerPrimitiveTypes(unittest.TestCase):
    def test_all_primitives(self):
        primitives = [
            ("Int8", TK.KW_INT8), ("Int16", TK.KW_INT16), ("Int32", TK.KW_INT32),
            ("Int64", TK.KW_INT64), ("UInt8", TK.KW_UINT8), ("UInt16", TK.KW_UINT16),
            ("UInt32", TK.KW_UINT32), ("UInt64", TK.KW_UINT64),
            ("Float32", TK.KW_FLOAT32), ("Float64", TK.KW_FLOAT64),
            ("USize", TK.KW_USIZE), ("ISize", TK.KW_ISIZE),
            ("Bool", TK.KW_BOOL), ("Void", TK.KW_VOID),
        ]
        for text, expected_kind in primitives:
            with self.subTest(text=text):
                self.assertIn(expected_kind, kinds(text))


class TestLexerLiterals(unittest.TestCase):
    def test_integer_literal(self):
        tks = [t for t in lex("42") if t.kind != TK.EOF]
        self.assertEqual(tks[0].kind, TK.INT_LIT)
        self.assertEqual(tks[0].value, "42")

    def test_hex_literal(self):
        tks = [t for t in lex("0xDEAD_BEEF") if t.kind != TK.EOF]
        self.assertEqual(tks[0].kind, TK.INT_LIT)
        self.assertIn("DEAD", tks[0].value.upper())

    def test_binary_literal(self):
        tks = [t for t in lex("0b1010_1010") if t.kind != TK.EOF]
        self.assertEqual(tks[0].kind, TK.INT_LIT)

    def test_float_literal(self):
        tks = [t for t in lex("3.14") if t.kind != TK.EOF]
        self.assertEqual(tks[0].kind, TK.FLOAT_LIT)
        self.assertEqual(tks[0].value, "3.14")

    def test_string_literal(self):
        tks = [t for t in lex('"hello world"') if t.kind != TK.EOF]
        self.assertEqual(tks[0].kind, TK.STR_LIT)
        self.assertEqual(tks[0].value, "hello world")

    def test_string_escape(self):
        tks = [t for t in lex(r'"line\nnext"') if t.kind != TK.EOF]
        self.assertEqual(tks[0].kind, TK.STR_LIT)
        self.assertIn("\n", tks[0].value)

    def test_char_literal(self):
        tks = [t for t in lex("'A'") if t.kind != TK.EOF]
        self.assertEqual(tks[0].kind, TK.CHAR_LIT)
        self.assertEqual(tks[0].value, "A")

    def test_true_false_nil(self):
        self.assertIn(TK.KW_TRUE, kinds("true"))
        self.assertIn(TK.KW_FALSE, kinds("false"))
        self.assertIn(TK.KW_NIL, kinds("nil"))


class TestLexerOperators(unittest.TestCase):
    def test_arrow(self):
        self.assertIn(TK.ARROW, kinds("->"))

    def test_fat_arrow(self):
        self.assertIn(TK.FAT_ARROW, kinds("=>"))

    def test_nil_coalescing(self):
        self.assertIn(TK.NIL_COAL, kinds("??"))

    def test_shl_eq(self):
        self.assertIn(TK.SHL_EQ, kinds("<<="))

    def test_shr_eq(self):
        self.assertIn(TK.SHR_EQ, kinds(">>="))

    def test_logical_and(self):
        self.assertIn(TK.AND, kinds("&&"))

    def test_logical_or(self):
        self.assertIn(TK.OR, kinds("||"))


class TestLexerComments(unittest.TestCase):
    def test_line_comment_ignored(self):
        # Comentário de linha não gera tokens
        tks = kinds("// isso é um comentário\nfn")
        self.assertEqual(tks, [TK.KW_FN])

    def test_block_comment_ignored(self):
        tks = kinds("(* bloco *) fn")
        self.assertEqual(tks, [TK.KW_FN])


class TestLexerLineCol(unittest.TestCase):
    def test_token_line_tracking(self):
        tks = lex("fn\nmain")
        fn_tok = tks[0]
        main_tok = tks[1]
        self.assertEqual(fn_tok.line, 1)
        self.assertEqual(main_tok.line, 2)

    def test_token_col_tracking(self):
        tks = lex("  fn")
        fn_tok = next(t for t in tks if t.kind == TK.KW_FN)
        self.assertEqual(fn_tok.col, 3)


class TestLexerErrors(unittest.TestCase):
    def test_invalid_char_raises(self):
        with self.assertRaises(SotlasLexError) as ctx:
            lex("module bad; fn x() { §; }")
        self.assertIn("caractere léxico inválido", str(ctx.exception))

    def test_error_has_location(self):
        try:
            lex("fn ok() { §; }")
        except SotlasLexError as e:
            self.assertIn("1:", str(e))


class TestLexerFixtures(unittest.TestCase):
    def test_sample_counter_tokenizes(self):
        path = ROOT / "tests" / "fixtures" / "sample_counter.sotlas"
        text = path.read_text(encoding="utf-8")
        tks = lex(text)
        self.assertTrue(any(t.kind == TK.KW_MODULE for t in tks))
        self.assertTrue(any(t.kind == TK.KW_STRUCT for t in tks))
        self.assertTrue(any(t.kind == TK.KW_FN for t in tks))

    def test_barecore_vga_tokenizes(self):
        path = ROOT / "tests" / "fixtures" / "barecore_vga.sotlas"
        text = path.read_text(encoding="utf-8")
        tks = lex(text)
        self.assertTrue(any(t.kind == TK.KW_BARECORE for t in tks))
        self.assertTrue(any(t.kind == TK.KW_TRAPFN for t in tks))
        self.assertTrue(any(t.kind == TK.KW_RAWPHYS for t in tks))
        self.assertTrue(any(t.kind == TK.KW_PORTWIRE for t in tks))
        self.assertTrue(any(t.kind == TK.KW_SLIT for t in tks))
        self.assertTrue(any(t.kind == TK.KW_NOTCH for t in tks))
        self.assertTrue(any(t.kind == TK.KW_CLINCH for t in tks))
        self.assertTrue(any(t.kind == TK.KW_REVERT for t in tks))

    def test_srg_scope_tokenizes(self):
        path = ROOT / "tests" / "fixtures" / "srg_scope.sotlas"
        text = path.read_text(encoding="utf-8")
        tks = lex(text)
        self.assertTrue(any(t.kind == TK.KW_CO_OWNED for t in tks))
        self.assertTrue(any(t.kind == TK.KW_SOLE for t in tks))
        self.assertTrue(any(t.kind == TK.KW_ISLAND for t in tks))
        self.assertTrue(any(t.kind == TK.KW_WHISPER for t in tks))
        self.assertTrue(any(t.kind == TK.KW_HANDOVER for t in tks))
        self.assertTrue(any(t.kind == TK.KW_QUARANTINE for t in tks))


if __name__ == "__main__":
    unittest.main()
