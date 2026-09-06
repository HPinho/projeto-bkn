"""Sotlas Compile — resolvedor modular e frontend bootstrap."""

# Instala a gramática/lowering de produção antes de carregar o compilador. Isso
# garante que todos os consumidores de ``tools.sotlas_compile.bootstrap`` usem
# o mesmo contrato de lexer, parser e emissão C.
from . import bootstrap as bootstrap
from .frontend_extensions import install as _install_frontend_extensions

_install_frontend_extensions(bootstrap)

from .compiler import SotlasError

SotlasBootstrapError = bootstrap.SotlasBootstrapError
compile_source = bootstrap.compile_source
compile_project = bootstrap.compile_project
emit_c_project = bootstrap.emit_c_project

__all__ = [
    "bootstrap", "SotlasError", "SotlasBootstrapError", "compile_source",
    "compile_project", "emit_c_project",
]
