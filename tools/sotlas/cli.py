"""Sotlas CLI — Driver de compilação da toolchain Sotlas."""
from __future__ import annotations
import argparse
import sys
import subprocess
from pathlib import Path

# Adiciona o diretório pai ao path para importar o pacote sotlas
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from sotlas import compile_source, SOTLAS_VERSION
from sotlas.lexer import SotlasLexError
from sotlas.parser import SotlasParseError
from sotlas.sema import SotlasSemaError


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sotlas",
        description=f"Compilador Sotlas Bootstrap v{SOTLAS_VERSION}",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # sotlas compile <arquivo.st> [-o saída] [--target] [--emit-c]
    cp = sub.add_parser("compile", help="Compila um arquivo .st para binário ou C99")
    cp.add_argument("source", help="Arquivo fonte .st")
    cp.add_argument("-o", "--output", default=None, help="Arquivo de saída")
    cp.add_argument(
        "--target",
        choices=["x86_64-freestanding", "host"],
        default="host",
        help="Alvo de compilação",
    )
    cp.add_argument(
        "--emit-c",
        action="store_true",
        help="Emite apenas o arquivo C99 (não invoca o compilador C)",
    )
    cp.add_argument(
        "--cc",
        default="gcc",
        help="Compilador C a invocar (padrão: gcc)",
    )

    # sotlas version
    sub.add_parser("version", help="Exibe a versão do compilador")

    # sotlas check <arquivo.st> — apenas análise léxica, sintática e semântica
    chk = sub.add_parser("check", help="Verifica o arquivo sem gerar código")
    chk.add_argument("source", help="Arquivo fonte .st")

    args = parser.parse_args()

    if args.cmd == "version":
        print(f"Sotlas {SOTLAS_VERSION}")
        return 0

    if args.cmd == "check":
        return _run_check(args.source)

    if args.cmd == "compile":
        return _run_compile(args)

    return 1


def _run_check(source_path: str) -> int:
    src = Path(source_path)
    if not src.exists():
        print(f"sotlas: erro: arquivo não encontrado: {source_path}", file=sys.stderr)
        return 1
    text = src.read_text(encoding="utf-8")
    try:
        from sotlas.lexer import Lexer
        from sotlas.parser import Parser
        from sotlas.sema import Sema
        tokens = Lexer(text, source_path).tokenize()
        ast = Parser(tokens, source_path).parse()
        Sema(ast, source_path).check()
        print(f"sotlas: ok — {source_path}")
        return 0
    except (SotlasLexError, SotlasParseError, SotlasSemaError) as e:
        print(f"sotlas: erro: {e}", file=sys.stderr)
        return 1


def _run_compile(args) -> int:
    src = Path(args.source)
    if not src.exists():
        print(f"sotlas: erro: arquivo não encontrado: {args.source}", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8")
    try:
        c_code = compile_source(text, args.source)
    except SotlasLexError as e:
        print(f"sotlas: erro léxico: {e}", file=sys.stderr)
        return 1
    except SotlasParseError as e:
        print(f"sotlas: erro sintático: {e}", file=sys.stderr)
        return 1
    except SotlasSemaError as e:
        print(f"sotlas: erro semântico: {e}", file=sys.stderr)
        return 1

    # Determinar arquivo de saída
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = src.with_suffix(".bin" if not args.emit_c else ".c")

    if args.emit_c:
        out_path.with_suffix(".c").write_text(c_code, encoding="utf-8")
        print(f"sotlas: C99 emitido em {out_path.with_suffix('.c')}")
        return 0

    # Escreve C temporário e invoca compilador C
    c_file = out_path.with_suffix(".c")
    c_file.write_text(c_code, encoding="utf-8")

    cc_flags = ["-std=c99", "-Wall", "-Wextra"]
    if args.target == "x86_64-freestanding":
        cc_flags += [
            "-ffreestanding", "-nostdlib", "-nostdinc",
            "-mno-red-zone", "-mno-mmx", "-mno-sse", "-mno-sse2",
            "-target", "x86_64-elf",
        ]

    cmd = [args.cc, str(c_file), "-o", str(out_path)] + cc_flags
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"sotlas: erro do compilador C:\n{result.stderr}", file=sys.stderr)
            return result.returncode
        print(f"sotlas: binário gerado em {out_path}")
        return 0
    except FileNotFoundError:
        print(f"sotlas: compilador C '{args.cc}' não encontrado — use --emit-c para gerar apenas o C99", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
