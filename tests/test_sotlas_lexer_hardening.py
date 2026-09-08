"""Regression tests for canonical Sotlas comment and character handling."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sotlas.lexer import Lexer, SotlasLexError
from sotlas.token_types import TK
from sotlas_compile import bootstrap as production_bootstrap


def significant(source: str):
    return [token for token in Lexer(source, "<lexer-hardening>").tokenize() if token.kind != TK.EOF]


def production_significant(source: str):
    return [
        token for token in production_bootstrap.lex(source, "<lexer-hardening>")
        if token.kind != "EOF"
    ]


class SotlasLexerHardeningTests(unittest.TestCase):
    def test_c_style_block_comment_is_canonical_in_both_frontends(self):
        tokens = significant("/* hardware note */ fn")
        self.assertEqual([token.kind for token in tokens], [TK.KW_FN])
        production = production_significant("/* hardware note */ fn")
        self.assertEqual([token.kind for token in production], ["fn"])

    def test_grouped_raw_dereference_is_never_a_pascal_comment(self):
        tokens = significant("(*ptr).field")
        self.assertEqual(
            [token.kind for token in tokens],
            [TK.LPAREN, TK.STAR, TK.IDENT, TK.RPAREN, TK.DOT, TK.IDENT],
        )
        production = production_significant("(*ptr).field")
        self.assertEqual(
            [token.kind for token in production],
            ["(", "*", "IDENT", ")", ".", "IDENT"],
        )

    def test_unterminated_c_style_block_comment_is_rejected_at_opening(self):
        with self.assertRaises(SotlasLexError) as legacy_ctx:
            significant("fn x() {}\n/* missing close")
        legacy_error = str(legacy_ctx.exception)
        self.assertIn(":2:1:", legacy_error)
        self.assertIn("comentário de bloco", legacy_error)

        with self.assertRaises(production_bootstrap.SotlasBootstrapError) as production_ctx:
            production_significant("fn x() {}\n/* missing close")
        production_error = str(production_ctx.exception)
        self.assertIn(":2:1:", production_error)
        self.assertIn("comentário de bloco", production_error)

    def test_character_escape_is_decoded_consistently_with_strings(self):
        token = significant(r"'\n'")[0]
        self.assertEqual(token.kind, TK.CHAR_LIT)
        self.assertEqual(token.value, "\n")

    def test_empty_and_unterminated_character_literals_are_rejected(self):
        for source in ("''", "'x"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(SotlasLexError, "literal char inválido"):
                    significant(source)


if __name__ == "__main__":
    unittest.main()
