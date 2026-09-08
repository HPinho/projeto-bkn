"""Sotlas CLI — canonical driver for the Sotlas production frontend.

Uso:
    sotlas compile arquivo.sotlas [-o saída] [--target x86_64-freestanding] [--emit-c]
    sotlas check   arquivo.sotlas
    sotlas version
"""
from __future__ import annotations
import argparse
import sys
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from sotlas import compile_source, SOTLAS_VERSION, SotlasBootstrapError
from sotlas_compile import bootstrap as production_frontend

SOTLAS_EXT = ".sotlas"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sotlas",
        description=f"Compilador Sotlas v{SOTLAS_VERSION}",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    cp = sub.add_parser("compile", help=f"Compila um arquivo {SOTLAS_EXT} para binário ou C11")
    cp.add_argument("source", help=f"Arquivo fonte {SOTLAS_EXT}")
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
        help="Emite apenas o C11 intermediário (não invoca o compilador C)",
    )
    cp.add_argument(
        "--cc",
        default="gcc",
        help="Compilador C a invocar (padrão: gcc)",
    )

    sub.add_parser("version", help="Exibe a versão do compilador")

    chk = sub.add_parser("check", help="Executa lexer, parser, tipos e safety sem gerar código")
    chk.add_argument("source", help=f"Arquivo fonte {SOTLAS_EXT}")

    args = parser.parse_args()

    if args.cmd == "version":
        print(f"Sotlas {SOTLAS_VERSION}")
        return 0
    if args.cmd == "check":
        return _run_check(args.source)
    if args.cmd == "compile":
        return _run_compile(args)
    return 1


def _read_source(source_path: str) -> tuple[Path, str] | None:
    src = Path(source_path)
    if not src.exists():
        print(f"sotlas: erro: arquivo não encontrado: {source_path}", file=sys.stderr)
        return None
    if src.suffix not in (SOTLAS_EXT, ".st"):
        print(
            f"sotlas: aviso: extensão não reconhecida '{src.suffix}' (esperado {SOTLAS_EXT})",
            file=sys.stderr,
        )
    return src, src.read_text(encoding="utf-8")


def _run_check(source_path: str) -> int:
    loaded = _read_source(source_path)
    if loaded is None:
        return 1
    _, text = loaded
    try:
        module = production_frontend.parse(text, filename=source_path)
        production_frontend.check(module)
    except SotlasBootstrapError as error:
        print(f"sotlas: erro: {error}", file=sys.stderr)
        return 1
    print(f"sotlas: ok — {source_path}")
    return 0


def _run_compile(args) -> int:
    loaded = _read_source(args.source)
    if loaded is None:
        return 1
    src, text = loaded

    try:
        c_code = compile_source(text, args.source)
    except SotlasBootstrapError as error:
        print(f"sotlas: erro: {error}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = src.with_suffix(".bin" if not args.emit_c else ".c")

    if args.emit_c:
        c_path = out_path.with_suffix(".c")
        c_path.write_text(c_code, encoding="utf-8")
        print(f"sotlas: C11 emitido em {c_path}")
        return 0

    c_file = out_path.with_suffix(".c")
    c_file.write_text(c_code, encoding="utf-8")

    cc_flags = ["-std=c11", "-Wall", "-Wextra"]
    if args.target == "x86_64-freestanding":
        cc_flags += [
            "-ffreestanding", "-nostdlib", "-nostdinc",
            "-mno-red-zone", "-mno-mmx", "-mno-sse", "-mno-sse2",
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
        print(
            f"sotlas: compilador C '{args.cc}' não encontrado — use --emit-c para gerar apenas o C11",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())