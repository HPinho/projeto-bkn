"""Sotlas Compiler — Bootstrap Python Package (Estágio 0)."""

SOTLAS_VERSION = "0.1.0"
SOTLAS_LANG_VERSION = "0.1"

from .lexer import Lexer, SotlasLexError
from .parser import Parser, SotlasParseError
from .sema import Sema, SotlasSemaError
from .codegen_c import CodegenC

__all__ = [
    "SOTLAS_VERSION",
    "SOTLAS_LANG_VERSION",
    "Lexer",
    "SotlasLexError",
    "Parser",
    "SotlasParseError",
    "Sema",
    "SotlasSemaError",
    "CodegenC",
]


def compile_source(source: str, filename: str = "<stdin>") -> str:
    """Pipeline completo: source → C99 freestanding.

    Args:
        source: Texto-fonte Sotlas (.st).
        filename: Nome do arquivo (para mensagens de erro).

    Returns:
        String com o código C99 gerado.
    """
    tokens = Lexer(source, filename).tokenize()
    ast = Parser(tokens, filename).parse()
    Sema(ast, filename).check()
    return CodegenC(ast).emit()
