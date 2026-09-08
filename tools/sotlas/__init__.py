"""Sotlas public Python API.

The production compiler lives in :mod:`sotlas_compile`.  The historical rich
frontend remains importable only as an explicit migration/testing surface; it is
not a second production compiler.
"""

SOTLAS_VERSION = "0.2.0"
SOTLAS_LANG_VERSION = "0.2"

from .lexer import Lexer, SotlasLexError
from .parser import Parser, SotlasParseError
from .sema import Sema, SotlasSemaError
from .codegen_c import CodegenC
from sotlas_compile import (
    compile_source as _canonical_compile_source,
    SotlasBootstrapError,
)

__all__ = [
    "SOTLAS_VERSION",
    "SOTLAS_LANG_VERSION",
    "Lexer",
    "SotlasLexError",
    "Parser",
    "SotlasParseError",
    "Sema",
    "SotlasSemaError",
    "SotlasBootstrapError",
    "CodegenC",
    "compile_source",
    "compile_legacy_source",
]


def compile_source(source: str, filename: str = "<stdin>") -> str:
    """Compile through the single production Sotlas frontend."""
    return _canonical_compile_source(source, filename=filename)


def compile_legacy_source(source: str, filename: str = "<stdin>") -> str:
    """Historical frontend kept only for language-feature migration tests.

    New code, the CLI, BakenOS and external consumers must use
    :func:`compile_source`.  Once the remaining legacy-only syntax is ported or
    retired, this function and the old parser/sema/codegen modules can be
    removed without changing the public production compiler API.
    """
    tokens = Lexer(source, filename).tokenize()
    ast = Parser(tokens, filename).parse()
    Sema(ast, filename).check()
    return CodegenC(ast).emit()