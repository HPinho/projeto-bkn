"""Sotlas Compile — frontend canônico, segurança e lowering de produção."""

# Há uma única rota de compilação de produção: bootstrap + extensões oficiais +
# política de segurança/FFI. Ferramentas podem expor ASTs auxiliares, mas não
# podem possuir um segundo lowering ou uma segunda semântica executável.
from . import bootstrap as bootstrap
from .frontend_extensions import install as _install_frontend_extensions
from .language_safety import install as _install_language_safety

_install_frontend_extensions(bootstrap)
_install_language_safety(bootstrap)

from .compiler import SotlasError

SotlasBootstrapError = bootstrap.SotlasBootstrapError
compile_source = bootstrap.compile_source
compile_project = bootstrap.compile_project
emit_c_project = bootstrap.emit_c_project

__all__ = [
    "bootstrap", "SotlasError", "SotlasBootstrapError", "compile_source",
    "compile_project", "emit_c_project",
]
