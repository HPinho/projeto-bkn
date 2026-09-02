#!/usr/bin/env python3
"""Sotlas Compile: frontend e backend modular da linguagem Sotlas.

O compilador resolve o grafo Sotlas, valida sua interface pública e emite uma
unidade C isolada para cada módulo. A entrada do kernel e a linkedição
pertencem integralmente ao grafo Sotlas.

Extensão oficial: .sotlas
"""
import argparse
import json
import os
import re
import sys
import hashlib
from pathlib import Path

MODULE_RE = re.compile(r"^\s*module\s+([A-Za-z_][A-Za-z0-9_:]*)\s*;", re.MULTILINE)
MODULE_KEYWORD_RE = re.compile(r"^\s*module\b", re.MULTILINE)
IMPORT_RE = re.compile(
    r"^\s*(?:pub\s+)?import\s+"
    r"(?P<module>[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*)"
    r"::\*\s*;\s*(?://.*)?$",
    re.MULTILINE,
)
IMPORT_LINE_RE = re.compile(r"^\s*(?:pub\s+)?import\b.*$", re.MULTILINE)
# Somente declarações na margem são exports de módulo. Métodos podem repetir
# nomes em tipos distintos e serão tratados pelo gerador de tipos, não aqui.
EXPORT_RE = re.compile(r"^pub\s+(?:fn|struct|class|enum)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
KERNEL_ENTRY_RE = re.compile(
    r"^\s*@export\s*\n\s*pub\s+fn\s+baken_kernel_main\s*\(", re.MULTILINE
)
# Módulos Sotlas não podem delegar silenciosamente sua semântica ao
# pré-processador C. O bootloader e ferramentas de host não declaram `module`
# e, por isso, ficam fora desta regra deliberadamente.
C_PREPROCESSOR_RE = re.compile(r"^\s*#\s*(?:include|define|if|ifdef|ifndef|pragma)\b", re.MULTILINE)

class SotlasError(Exception):
    pass

def project_root(entry):
    for candidate in (entry.parent, *entry.parents):
        if (candidate / "kernel").is_dir():
            return candidate
    raise SotlasError("não foi possível localizar a raiz do projeto Sotlas")

def discover_units(root):
    units, duplicates = {}, []
    for source_root in (root / "kernel", root / "libbkn", root / "boot", root / "apps"):
        if not source_root.is_dir():
            continue
        for ext in ("*.sotlas", "*.sth", "*.st"):
            for path in source_root.rglob(ext):
                text = path.read_text(encoding="utf-8")
                declarations = list(MODULE_RE.finditer(text))
                if not declarations:
                    if MODULE_KEYWORD_RE.search(text):
                        raise SotlasError(f"{path.relative_to(root)}: declaração module inválida")
                    continue
                if len(declarations) != 1:
                    raise SotlasError(
                        f"{path.relative_to(root)}: um arquivo Sotlas pode declarar exatamente um módulo"
                    )
                name = declarations[0].group(1)
                if name in units:
                    existing_path = units[name]["path"]
                    duplicates.append((name, existing_path, path))
                else:
                    units[name] = {"path": path, "text": text}
    if duplicates:
        lines = [f"{name}: {first} e {second}" for name, first, second in duplicates]
        raise SotlasError("módulos declarados mais de uma vez:\n" + "\n".join(lines))
    return units

def resolve_import(name, units):
    parts = name.split("::")
    while parts:
        candidate = "::".join(parts)
        if candidate in units:
            return candidate
        parts.pop()
    return None

def validate_module_dialect(units, root):
    """Impede que fontes descobertas como Sotlas escondam trechos de C."""
    for unit in units.values():
        if C_PREPROCESSOR_RE.search(unit["text"]):
            raise SotlasError(
                f"{unit['path'].relative_to(root)}: módulo Sotlas não pode usar "
                "pré-processador C"
            )
        for import_line in IMPORT_LINE_RE.findall(unit["text"]):
            if not IMPORT_RE.fullmatch(import_line):
                raise SotlasError(
                    f"{unit['path'].relative_to(root)}: import Sotlas inválido; "
                    "use import modulo::*;"
                )

def validate_all_cycles(graph):
    """Rejeita ciclos até em módulos que ainda não pertencem à entrada."""
    visiting, visited = [], set()

    def visit(module):
        if module in visiting:
            cycle = visiting[visiting.index(module):] + [module]
            raise SotlasError("dependência circular: " + " -> ".join(cycle))
        if module in visited:
            return
        visiting.append(module)
        for dependency in graph[module]:
            visit(dependency)
        visiting.pop()
        visited.add(module)

    for module in graph:
        visit(module)

def analyze(entry):
    entry = entry.resolve()
    root = project_root(entry)
    units = discover_units(root)
    validate_module_dialect(units, root)
    entry_match = MODULE_RE.search(entry.read_text(encoding="utf-8"))
    if not entry_match:
        raise SotlasError(f"{entry} não declara um módulo Sotlas")
    entry_module = entry_match.group(1)
    if entry_module not in units:
        raise SotlasError(f"entrada {entry_module} não foi descoberta")
    graph = {}
    for module, unit in units.items():
        imports = []
        for match in IMPORT_RE.finditer(unit["text"]):
            raw = match.group("module")
            target = resolve_import(raw, units)
            if not target:
                raise SotlasError(f"{unit['path'].relative_to(root)}: import não resolvido: {raw}")
            if target == module:
                raise SotlasError(f"{unit['path'].relative_to(root)}: módulo não pode importar a si mesmo")
            if target not in imports:
                imports.append(target)
        graph[module] = imports
    validate_all_cycles(graph)
    reachable, visiting, visited = [], [], set()
    def visit(module):
        if module in visiting:
            cycle = visiting[visiting.index(module):] + [module]
            raise SotlasError("dependência circular: " + " -> ".join(cycle))
        if module in visited:
            return
        visiting.append(module)
        for dependency in graph[module]:
            visit(dependency)
        visiting.pop()
        visited.add(module)
        reachable.append(module)
    visit(entry_module)
    exports = {}
    for module in reachable:
        for symbol in EXPORT_RE.findall(units[module]["text"]):
            qualified = f"{module}::{symbol}"
            if qualified in exports:
                raise SotlasError(f"símbolo exportado duas vezes: {qualified}")
            exports[qualified] = str(units[module]["path"].relative_to(root))
    if entry_module == "kernel::main":
        entry_exports = [module for module in reachable if KERNEL_ENTRY_RE.search(units[module]["text"])]
        entry_count = sum(len(KERNEL_ENTRY_RE.findall(units[module]["text"])) for module in reachable)
        if entry_exports != ["kernel::main"] or entry_count != 1:
            detail = ", ".join(entry_exports) if entry_exports else "nenhum"
            raise SotlasError(
                "a rota do kernel precisa exportar exatamente um baken_kernel_main em "
                f"kernel::main; encontrado: {detail} ({entry_count} declarações)"
            )
    unreachable = sorted(set(units) - set(reachable))
    imported_modules = {dependency for dependencies in graph.values() for dependency in dependencies}
    orphan_roots = sorted(module for module in unreachable if module not in imported_modules)
    return {"project_root": str(root), "entry": entry_module, "audited_modules": len(units), "compile_order": reachable,
            "unreachable_modules": unreachable, "orphan_roots": orphan_roots,
            "units": [{"module": m, "path": str(units[m]["path"].relative_to(root)), "imports": graph[m]} for m in reachable],
            "exports": exports}

def find_gcc(root: Path) -> Path:
    import shutil
    configured = os.environ.get("SOTLAS_CC")
    if configured:
        configured_path = Path(configured)
        resolved = configured_path if configured_path.exists() else shutil.which(configured)
        if resolved:
            return Path(resolved)
        raise SotlasError(f"compilador configurado em SOTLAS_CC não encontrado: {configured}")
    candidates = []
    if os.name == "nt":
        candidates = [
            root / "tools" / "w64devkit" / "bin" / "gcc.exe",
            Path(r"C:\Projetos\projeto-bkn\tools\w64devkit\bin\gcc.exe"),
        ]
    for c in candidates:
        if c.exists():
            return c
    # O compilador implícito deve pertencer ao host: vários testes geram e
    # executam binários locais. Cross-compilação só é ativada por SOTLAS_CC.
    which_gcc = shutil.which("gcc")
    if which_gcc:
        return Path(which_gcc)
    raise SotlasError("compilador GCC não encontrado; configure SOTLAS_CC para cross-compilar")

# =============================================================================
# PARSER & TYPECHECKER SOTLAS (Fase VIII: Backend Sotlas Nativo)
# =============================================================================

KNOWN_PRIMITIVE_TYPES = {
    "u8", "u16", "u32", "u64", "usize",
    "i8", "i16", "i32", "i64", "isize",
    "f32", "f64", "bool", "void", "str", "!"
}

class SotlasType:
    def __init__(self, name: str, is_ptr: bool = False, is_mut: bool = False):
        self.name = name
        self.is_ptr = is_ptr
        self.is_mut = is_mut

    def __repr__(self):
        if self.is_ptr:
            prefix = "*mut " if self.is_mut else "*const "
            return f"{prefix}{self.name}"
        return self.name

class SotlasField:
    def __init__(self, name: str, type_info: SotlasType, is_pub: bool = False):
        self.name = name
        self.type_info = type_info
        self.is_pub = is_pub

class SotlasFunction:
    def __init__(self, name: str, params: list, return_type: SotlasType, is_pub: bool = False, attributes: list | None = None, line: int = 0, body: str = ""):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.is_pub = is_pub
        self.attributes = attributes or []
        self.line = line
        self.body = body

class SotlasStruct:
    def __init__(self, name: str, fields: list, is_pub: bool = False):
        self.name = name
        self.fields = fields
        self.is_pub = is_pub

class SotlasClass:
    def __init__(self, name: str, fields: list, methods: list, is_pub: bool = False):
        self.name = name
        self.fields = fields
        self.methods = methods
        self.is_pub = is_pub

class SotlasModuleAst:
    def __init__(self, name: str):
        self.name = name
        self.imports = []
        self.structs = []
        self.classes = []
        self.functions = []
        self.static_variables = []

def parse_st_type(raw_type: str) -> SotlasType:
    raw = raw_type.strip()
    if raw.startswith("*mut "):
        return SotlasType(raw[5:].strip(), is_ptr=True, is_mut=True)
    if raw.startswith("*const "):
        return SotlasType(raw[7:].strip(), is_ptr=True, is_mut=False)
    if raw.startswith("*"):
        return SotlasType(raw[1:].strip(), is_ptr=True, is_mut=False)
    if raw.startswith("&mut "):
        return SotlasType(raw[5:].strip(), is_ptr=True, is_mut=True)
    if raw.startswith("&"):
        return SotlasType(raw[1:].strip(), is_ptr=True, is_mut=False)
    return SotlasType(raw)

def _top_level_offsets(text: str) -> set:
    """Retorna offsets fora de corpos de tipos/funções, ignorando comentários e strings."""
    result, depth, index = set(), 0, 0
    while index < len(text):
        if text.startswith("//", index):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        if text[index] == '"':
            index += 1
            while index < len(text) and text[index] != '"':
                if text[index] == '\\':
                    index += 1
                index += 1
            index += 1
            continue
        if text[index] == "'":
            index += 1
            while index < len(text) and text[index] != "'":
                if text[index] == '\\':
                    index += 1
                index += 1
            index += 1
            continue
        ch = text[index]
        if ch == "{": depth += 1
        elif ch == "}": depth = max(0, depth - 1)
        if depth == 0:
            result.add(index)
        index += 1
    return result

def _matching_brace(text: str, opening: int) -> int:
    """Encontra o fim do bloco, respeitando comentários e strings."""
    depth, index = 0, opening
    while index < len(text):
        if text.startswith("//", index):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        if text[index] == '"':
            index += 1
            while index < len(text) and text[index] != '"':
                if text[index] == '\\':
                    index += 1
                index += 1
            index += 1
            continue
        if text[index] == "'":
            index += 1
            while index < len(text) and text[index] != "'":
                if text[index] == '\\':
                    index += 1
                index += 1
            index += 1
            continue
        if text[index] == "{": depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0: return index
        index += 1
    raise SotlasError("bloco Sotlas sem chave de fechamento")

def _parse_fields(body: str) -> list:
    fields, depth = [], 0
    for raw_line in body.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if depth == 0:
            match = re.match(r"(?:pub\s+)?(?:mut\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^=;{]+)", line)
            if match:
                fields.append(SotlasField(match.group(1), parse_st_type(match.group(2).strip())))
        depth += line.count("{") - line.count("}")
    return fields

def parse_module_ast(text: str, path: Path | None = None) -> SotlasModuleAst:
    mod_match = MODULE_RE.search(text)
    if not mod_match:
        raise SotlasError(f"{path or 'unidade'}: declaração module ausente")
    mod_name = mod_match.group(1)
    ast = SotlasModuleAst(mod_name)

    # Coleta imports
    for imp in IMPORT_RE.finditer(text):
        ast.imports.append(imp.group("module"))

    # Coleta structs
    struct_re = re.compile(r"(pub\s+)?struct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}", re.MULTILINE)
    for smatch in struct_re.finditer(text):
        is_pub = bool(smatch.group(1))
        sname = smatch.group(2)
        body = smatch.group(3)
        fields = []
        for line in body.split(";"):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            f_pub = line.startswith("pub ")
            if f_pub:
                line = line[4:].strip()
            if ":" in line:
                fname, ftype = line.split(":", 1)
                fields.append(SotlasField(fname.strip(), parse_st_type(ftype.strip()), is_pub=f_pub))
        ast.structs.append(SotlasStruct(sname, fields, is_pub=is_pub))

    # Classes podem conter métodos com blocos internos; por isso não usam a
    # regex curta das structs. O scanner procura a chave correspondente.
    class_re = re.compile(r"(pub\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+extends\s+[A-Za-z_][A-Za-z0-9_]*)?\s*\{")
    for cmatch in class_re.finditer(text):
        close = _matching_brace(text, cmatch.end() - 1)
        ast.classes.append(SotlasClass(cmatch.group(2), _parse_fields(text[cmatch.end():close]), [], bool(cmatch.group(1))))

    static_re = re.compile(r"^\s*static\s+mut\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^=;{]+)", re.MULTILINE)
    for vmatch in static_re.finditer(text):
        ast.static_variables.append((vmatch.group(1), parse_st_type(vmatch.group(2).strip())))

    # Coleta somente funções declaradas no escopo do módulo. Métodos de classe
    # têm o mesmo formato superficial, mas não podem virar exports globais.
    top_level = _top_level_offsets(text)
    fn_re = re.compile(r"((?:@[A-Za-z_]+\s*\n\s*)*)(pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*(?:->\s*([^{]+))?\{", re.MULTILINE)
    for fmatch in fn_re.finditer(text):
        if fmatch.start() not in top_level:
            continue
        attrs = [a.strip() for a in (fmatch.group(1) or "").split() if a.startswith("@")]
        is_pub = bool(fmatch.group(2))
        fname = fmatch.group(3)
        raw_params = fmatch.group(4)
        raw_ret = fmatch.group(5) or "void"
        ret_type = parse_st_type(raw_ret)
        params = []
        for p in raw_params.split(","):
            p = p.strip()
            if not p:
                continue
            if ":" in p:
                pname, ptype = p.split(":", 1)
                params.append((pname.strip(), parse_st_type(ptype.strip())))
        body_start = fmatch.end() - 1
        body_end = _matching_brace(text, body_start)
        ast.functions.append(SotlasFunction(fname, params, ret_type, is_pub=is_pub, attributes=attrs,
                                        line=text.count("\n", 0, fmatch.start()) + 1,
                                        body=text[body_start + 1:body_end]))

    return ast

def _base_type_name(type_info: SotlasType) -> str:
    raw = type_info.name.strip()
    if raw.startswith("["):
        raw = raw[1:].split(";", 1)[0].strip()
    for prefix in ("*mut ", "*const ", "*", "&mut ", "&"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
            break
    return raw.split("::")[-1]

def typecheck_ast(ast: SotlasModuleAst, known_types: set | None = None) -> bool:
    types = set(KNOWN_PRIMITIVE_TYPES)
    if known_types:
        types.update(known_types)
    for s in ast.structs:
        types.add(s.name)
    for c in ast.classes:
        types.add(c.name)

    # Valida tipos de campos das structs
    for s in ast.structs:
        for f in s.fields:
            base_type = _base_type_name(f.type_info)
            if base_type not in types:
                raise SotlasError(f"{ast.name}: tipo desconhecido no campo {s.name}.{f.name}: {f.type_info}")
    for c in ast.classes:
        for f in c.fields:
            base_type = _base_type_name(f.type_info)
            if base_type not in types:
                raise SotlasError(f"{ast.name}: tipo desconhecido no campo {c.name}.{f.name}: {f.type_info}")
    for variable_name, type_info in ast.static_variables:
        base_type = _base_type_name(type_info)
        if base_type not in types:
            raise SotlasError(f"{ast.name}: tipo desconhecido na variável estática {variable_name}: {type_info}")

    # Valida assinaturas de funções
    for fn in ast.functions:
        all_types = list(fn.params) + [("retorno", fn.return_type)]
        for parameter_name, type_info in all_types:
            base_type = _base_type_name(type_info)
            if base_type not in types:
                raise SotlasError(f"{ast.name}:{fn.line}: tipo desconhecido em {fn.name} ({parameter_name}): {type_info}")

    return True

def exported_type_names(ast: SotlasModuleAst) -> set:
    """Tipos que outro módulo pode usar por meio de `import modulo::*`."""
    return {item.name for item in ast.structs if item.is_pub} | {
        item.name for item in ast.classes if item.is_pub
    }

def validate_module_interfaces(asts: dict, manifest: dict) -> None:
    """Aplica visibilidade de tipos e detecta colisões na interface Sotlas."""
    imports = {unit["module"]: unit["imports"] for unit in manifest["units"]}
    for module, ast in asts.items():
        local = {item.name for item in ast.structs} | {item.name for item in ast.classes}
        public = set(KNOWN_PRIMITIVE_TYPES) | local
        for imported in imports[module]:
            public.update(exported_type_names(asts[imported]))
        typecheck_ast(ast, public)
        seen = set()
        for fn in ast.functions:
            if fn.name in seen:
                raise SotlasError(f"{module}:{fn.line}: função declarada mais de uma vez: {fn.name}")
            seen.add(fn.name)
        callable_names = {fn.name for fn in ast.functions}
        for imported in imports[module]:
            callable_names.update(fn.name for fn in asts[imported].functions if fn.is_pub)
        language_calls = {
            "if", "while", "for", "loop", "return", "unsafe", "sizeof", "mut",
            "baken_runtime_init_assets", "baken_runtime_run",
        }
        for fn in ast.functions:
            body = re.sub(r"//[^\n]*", "", fn.body)
            body = re.sub(r'"[^"]*"', '""', body)
            body = re.sub(r"'[^']*'", "''", body)
            for call in re.finditer(r"(?<![.A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
                name = call.group(1)
                if name not in callable_names and name not in language_calls:
                    raise SotlasError(f"{module}:{fn.line}: chamada não resolvida em {fn.name}: {name}")

def _c_identifier(module: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", module)

def emit_c_header(ast: SotlasModuleAst, output: Path, unit: dict | None = None) -> Path:
    """Gera a ABI C real diretamente da interface pública Sotlas."""
    if unit is None:
        raise SotlasError(f"fonte ausente para interface do módulo {ast.name}")
    try:
        from tools.sotlas_compile import bootstrap
    except ImportError:
        import bootstrap
    module = bootstrap.parse(unit["text"], filename=str(unit["path"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(bootstrap.emit_header(module), encoding="utf-8")
    return output

def emit_interface_manifest(ast: SotlasModuleAst, output: Path) -> Path:
    """Materializa a interface pública para ferramentas e linkedição Sotlas."""
    data = {
        "module": ast.name,
        "imports": ast.imports,
        "types": [
            {"kind": "struct", "name": item.name,
             "fields": [{"name": field.name, "type": repr(field.type_info)} for field in item.fields]}
            for item in ast.structs if item.is_pub
        ] + [
            {"kind": "class", "name": item.name,
             "fields": [{"name": field.name, "type": repr(field.type_info)} for field in item.fields]}
            for item in ast.classes if item.is_pub
        ],
        "functions": [
            {"name": fn.name, "parameters": [{"name": name, "type": repr(type_info)} for name, type_info in fn.params],
             "return_type": repr(fn.return_type), "attributes": fn.attributes}
            for fn in ast.functions if fn.is_pub
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output

def emit_c_module(ast: SotlasModuleAst, output: Path, header: Path, unit: dict | None = None,
                  imported_units: list[dict] | None = None) -> Path:
    """Reduz um módulo Sotlas para C11 usando exclusivamente o AST bootstrap.

    O compilador coordena parsing, interfaces e arquivos; implementações de UI
    permanecem nos módulos .sotlas e nunca são sintetizadas aqui.
    """
    if unit is None:
        raise SotlasError(f"fonte ausente para lowering do módulo {ast.name}")
    try:
        from tools.sotlas_compile import bootstrap
    except ImportError:
        import bootstrap

    module = bootstrap.parse(unit["text"], filename=str(unit["path"]))
    dependencies = [
        bootstrap.parse(item["text"], filename=str(item["path"]))
        for item in (imported_units or [])
    ]
    c_text = bootstrap.compile_module(
        module,
        imported_modules=dependencies,
        include_import_headers=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(c_text, encoding="utf-8")
    return output
def emit_st_kernel_entry(output: Path) -> Path:
    """Entrada EFI canônica gerada a partir de kernel::main."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join((
        "/* Gerado pelo Sotlas Compile a partir de kernel::main. */",
        '#include "baken_boot_info.h"',
        "extern void baken_kernel_main(const BakenBootInfo *boot_info);",
        "void st_kernel_entry(const BakenBootInfo *boot_info) {",
        "    baken_kernel_main(boot_info);",
        "}",
        "",
    )), encoding="utf-8")
    return output

def frontend(entry: Path) -> tuple:
    """Executa todas as fases semânticas antes da geração de objetos."""
    entry = entry.resolve()
    root = project_root(entry)
    manifest = analyze(entry)
    units = discover_units(root)
    asts = {
        mod_name: parse_module_ast(units[mod_name]["text"], units[mod_name]["path"])
        for mod_name in manifest["compile_order"]
    }
    validate_module_interfaces(asts, manifest)
    return root, manifest, units, asts

def build_modular(entry: Path, output: Path | None = None) -> dict:
    """Compilação e linkedição modular do kernel Sotlas / UEFI."""
    import subprocess
    entry = entry.resolve()
    root, manifest, units, asts = frontend(entry)
    gcc = find_gcc(root)

    obj_dir = root / "build" / "obj" / "st"
    generated_dir = root / "build" / "generated" / "st"
    obj_dir.mkdir(parents=True, exist_ok=True)
    include_dir = root / "kernel" / "include"

    env = dict(os.environ)
    env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")

    compiled_objects = []
    generated_sources = []
    generated_headers = []
    generated_interfaces = []
    common_flags = [
        "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-pointer-sign", "-Wno-duplicate-decl-specifier", "-ffreestanding",
        "-fshort-wchar", "-mno-red-zone", "-fno-stack-protector",
        "-fno-asynchronous-unwind-tables", "-nostdlib", "-I", str(include_dir),
        "-I", str(generated_dir), "-c",
    ]

    # Emite e compila uma unidade C isolada por módulo Sotlas. Módulos escritos em Sotlas
    # compilam diretamente com o backend bootstrap.
    for mod_name in manifest["compile_order"]:
        module_id = _c_identifier(mod_name)
        header = emit_c_header(asts[mod_name], generated_dir / f"{module_id}.h", units.get(mod_name))
        interface = emit_interface_manifest(asts[mod_name], generated_dir / f"{module_id}.soti.json")
        imported_units = [units[name] for name in asts[mod_name].imports]
        generated = emit_c_module(
            asts[mod_name], generated_dir / f"{module_id}.c", header,
            units.get(mod_name), imported_units,
        )
        obj = obj_dir / f"{module_id}.o"
        res = subprocess.run([str(gcc), *common_flags, str(generated), "-o", str(obj)],
                             capture_output=True, text=True, env=env)
        if res.returncode != 0:
            raise SotlasError(f"falha ao compilar módulo Sotlas {mod_name}: {res.stderr}")
        generated_sources.append(generated)
        generated_headers.append(header)
        generated_interfaces.append(interface)
        compiled_objects.append(obj)

    # Adaptador de firmware sem UI: eventos, relógio de quadro e ligação dos
    # atlas gerados às APIs Sotlas. Ele não contém primitivas de desenho.
    runtime_src = root / "kernel" / "src" / "baken_runtime.c"
    if runtime_src.exists():
        runtime_obj = obj_dir / "baken_runtime.o"
        res = subprocess.run(
            [str(gcc), *common_flags, str(runtime_src), "-o", str(runtime_obj)],
            capture_output=True, text=True, env=env,
        )
        if res.returncode != 0:
            raise SotlasError(f"falha ao compilar adaptador UEFI: {res.stderr}")
        compiled_objects.append(runtime_obj)

    # Compila o bootloader UEFI Sotlas.
    bootloader_src = root / "boot" / "uefi_bootloader.sotlas"
    if bootloader_src.exists():
        bootloader_obj = obj_dir / "uefi_bootloader.o"
        cmd = [str(gcc), *common_flags, "-x", "c", str(bootloader_src), "-o", str(bootloader_obj)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if res.returncode != 0:
            raise SotlasError(f"falha ao compilar bootloader UEFI: {res.stderr}")
        compiled_objects.append(bootloader_obj)

    # 3. Executa a linkedição do binário BOOTX64.EFI
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        link_cmd = [
            str(gcc), "-nostdlib", "-shared", "-Wl,--subsystem,10",
            "-Wl,--image-base,0x10000000", "-Wl,-e,efi_main",
            "-o", str(output)
        ] + [str(obj) for obj in compiled_objects]

        res = subprocess.run(link_cmd, capture_output=True, text=True, env=env)
        if res.returncode != 0:
            raise SotlasError(f"falha no link do binário EFI: {res.stderr}")

    return {
        "manifest": manifest,
        "compiled_objects": [str(o) for o in compiled_objects],
        "generated_sources": [str(s) for s in generated_sources],
        "generated_headers": [str(h) for h in generated_headers],
        "generated_interfaces": [str(item) for item in generated_interfaces],
        "output": str(output) if output else None,
    }

def main():
    parser = argparse.ArgumentParser(description="Sotlas Compile module resolver and compiler")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "build", "parse"):
        item = sub.add_parser(command)
        item.add_argument("input", type=Path)
        item.add_argument("-m", "--manifest", type=Path)
        if command == "build":
            item.add_argument("-o", "--output", required=True, type=Path)
    # O frontend Sotlas Bootstrap é isolado do caminho de compatibilidade usado pela ISO.
    # Assim o novo parser pode amadurecer com testes sem aceitar corpos opacos.
    for command in ("bootstrap-check", "bootstrap-emit-c", "bootstrap-build"):
        item = sub.add_parser(command, help="frontend procedural estrito Sotlas Bootstrap")
        item.add_argument("input", type=Path)
        if command in ("bootstrap-emit-c", "bootstrap-build"):
            item.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command.startswith("bootstrap-"):
            from bootstrap import compile_file, compile_project, emit_c_project, parse as bootstrap_parse, check as bootstrap_check
            if args.command == "bootstrap-build":
                modules = compile_project(args.input)
                emit_c_project(args.input, args.output)
                print(f"[OK] projeto Sotlas Bootstrap emitido: {args.output} ({len(modules)} módulos)")
                return 0
            module = bootstrap_parse(args.input.read_text(encoding="utf-8"))
            bootstrap_check(module)
            if args.command == "bootstrap-emit-c":
                compile_file(args.input, args.output)
                print(f"[OK] Sotlas Bootstrap emitido: {args.output}")
            else:
                print(f"[OK] Sotlas Bootstrap: {module.name}; {len(module.structs)} structs; {len(module.functions)} funções")
            return 0
        root, manifest, units, asts = frontend(args.input)
        if args.manifest:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"[OK] {manifest['entry']}: {len(manifest['compile_order'])} módulos resolvidos; "
            f"{len(manifest['unreachable_modules'])} fora da rota ativa; "
            f"{len(manifest['orphan_roots'])} raízes órfãs"
        )
        if args.command == "parse":
            ast = asts[manifest["entry"]]
            print(f"[OK] AST do módulo {ast.name}: {len(ast.structs)} structs, {len(ast.functions)} funções")
        elif args.command == "build":
            result = build_modular(args.input, args.output)
            print(f"[OK] Build concluído com sucesso: {result['output']} ({len(result['compiled_objects'])} objetos)")
    except SotlasError as error:
        print(f"[ERRO] Sotlas: {error}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
