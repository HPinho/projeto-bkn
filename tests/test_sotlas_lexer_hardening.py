"""Regression tests for strict Sotlas comment and character literal handling."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sotlas.lexer import Lexer, SotlasLexError
from sotlas.token_types import TK


def significant(source: str):
    return [token for token in Lexer(source, "<lexer-hardening>").tokenize() if token.kind != TK.EOF]


class SotlasLexerHardeningTests(unittest.TestCase):
    def test_c_style_block_comment_is_accepted(self):
        tokens = significant("/* hardware note */ fn")
        self.assertEqual([token.kind for token in tokens], [TK.KW_FN])

    def test_pascal_style_block_comment_can_contain_parentheses(self):
        tokens = significant("(* AP(1) waits for BSP *) fn")
        self.assertEqual([token.kind for token in tokens], [TK.KW_FN])

    def test_unterminated_c_style_block_comment_is_rejected_at_opening(self):
        with self.assertRaisesRegex(SotlasLexError, "comentário de bloco não terminado") as ctx:
            significant("fn x() {}\n/* missing close")
        self.assertIn(":2:1:", str(ctx.exception))

    def test_unterminated_pascal_style_block_comment_is_rejected_at_opening(self):
        with self.assertRaisesRegex(SotlasLexError, "comentário de bloco não terminado"):
            significant("(* missing close")

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
