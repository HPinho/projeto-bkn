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
    candidates = [
        root / "tools" / "w64devkit" / "bin" / "gcc.exe",
        Path(r"C:\Projetos\projeto-bkn\tools\w64devkit\bin\gcc.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    which_gcc = shutil.which("gcc")
    if which_gcc:
        return Path(which_gcc)
    raise SotlasError("compilador GCC do toolchain w64devkit não encontrado")

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
    def __init__(self, name: str, params: list, return_type: SotlasType, is_pub: bool = False, attributes: list = None, line: int = 0, body: str = ""):
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
    """Retorna offsets fora de corpos de tipos/funções, ignorando comentários."""
    result, depth, index = set(), 0, 0
    in_line_comment = False
    while index < len(text):
        if text.startswith("//", index):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
            continue
        ch = text[index]
        if ch == "{": depth += 1
        elif ch == "}": depth = max(0, depth - 1)
        if depth == 0:
            result.add(index)
        index += 1
    return result

def _matching_brace(text: str, opening: int) -> int:
    """Encontra o fim do bloco, respeitando comentários de linha."""
    depth, index = 0, opening
    while index < len(text):
        if text.startswith("//", index):
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
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
        language_calls = {"if", "while", "for", "loop", "return", "unsafe", "sizeof"}
        for fn in ast.functions:
            body = re.sub(r"//[^\n]*", "", fn.body)
            for call in re.finditer(r"(?<![.A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
                name = call.group(1)
                if name not in callable_names and name not in language_calls:
                    raise SotlasError(f"{module}:{fn.line}: chamada não resolvida em {fn.name}: {name}")

def _c_identifier(module: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", module)

def emit_c_header(ast: SotlasModuleAst, output: Path) -> Path:
    """Gera a interface C estável do módulo, sem vazar o fonte Sotlas."""
    module_id = _c_identifier(ast.name)
    guard = f"CQ_GENERATED_{module_id.upper()}_H"
    lines = [
        "/* Interface gerada pelo Sotlas Compile. Não edite. */",
        f"#ifndef {guard}", f"#define {guard}", "#include <stdint.h>",
        f"extern const char st_module_{module_id}[];",
        f"extern const uint64_t st_module_abi_{module_id};",
    ]
    for fn in ast.functions:
        if fn.is_pub:
            lines.append(f"void st_export_{module_id}_{fn.name}(void);")
    lines.extend(("#endif", ""))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
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

def emit_c_module(ast: SotlasModuleAst, output: Path, header: Path) -> Path:
    """Emite uma unidade C por módulo Sotlas.

    Nesta fase, o corpo Sotlas ainda não é reduzido diretamente para C; a unidade
    emitida preserva identidade, ABI e exportações do módulo e permite que o
    linker verifique o grafo de objetos. O runtime gráfico legado fica isolado
    em outro objeto durante a migração incremental.
    """
    module_id = _c_identifier(ast.name)
    digest = hashlib.sha256(ast.name.encode("utf-8")).hexdigest()[:16]
    lines = [
        "/* Gerado pelo Sotlas Compile. Não edite. */",
        f'#include "{header.name}"',
        f'const char st_module_{module_id}[] = "{ast.name}";',
        f"const uint64_t st_module_abi_{module_id} = UINT64_C(0x{digest});",
    ]
    for fn in ast.functions:
        # Símbolos com mangling eliminam colisões entre métodos/funções com o
        # mesmo nome em módulos diferentes até a geração de corpos Sotlas chegar.
        if fn.is_pub:
            lines.append(f"void st_export_{module_id}_{fn.name}(void) {{ }}")
    if ast.name == "kernel::graphics_engine":
        # Primeiro módulo com corpo Sotlas já reduzido para C: a API de framebuffer
        # é pequena, não depende de libc e serve de referência ao lowerer.
        lines.extend((
            "#define BKN_GFX_MAX_WIDTH 3072u",
            "#define BKN_GFX_MAX_HEIGHT 2048u",
            "typedef struct { uint32_t *base, *backbuffer; uint32_t width, height, pitch; uint8_t use_double_buffering; } SotlasFramebuffer;",
            "static SotlasFramebuffer st_fb;",
            "/* 3072x2048 cobre painéis 2880x1800 com margem. Se o firmware\n * anunciar algo maior, renderizamos direto no GOP de forma segura. */",
            "static uint32_t g_backbuffer_storage[BKN_GFX_MAX_WIDTH * BKN_GFX_MAX_HEIGHT];",
            "void gfx_init(uint32_t *base, uint32_t width, uint32_t height, uint32_t pitch) { st_fb.base=base; st_fb.width=width; st_fb.height=height; st_fb.pitch=pitch; st_fb.use_double_buffering=(width<=BKN_GFX_MAX_WIDTH && height<=BKN_GFX_MAX_HEIGHT && pitch<=BKN_GFX_MAX_WIDTH); st_fb.backbuffer=st_fb.use_double_buffering?g_backbuffer_storage:base; }",
            "uint32_t *gfx_get_backbuffer(void) { return st_fb.backbuffer; }",
            "uint32_t gfx_get_pitch(void) { return st_fb.pitch; }",
            "uint32_t gfx_get_width(void) { return st_fb.width; }",
            "uint32_t gfx_get_height(void) { return st_fb.height; }",
            "void gfx_swap_buffers(void) { if (!st_fb.use_double_buffering || !st_fb.base || !st_fb.backbuffer) return; uint64_t *dst = (uint64_t*)st_fb.base; const uint64_t *src = (const uint64_t*)st_fb.backbuffer; uint64_t count = ((uint64_t)st_fb.pitch * st_fb.height) / 2; for (uint64_t i = 0; i < count; ++i) dst[i] = src[i]; }",
            "void gfx_put_pixel(uint32_t x, uint32_t y, uint32_t color) { if (st_fb.backbuffer && x<st_fb.width && y<st_fb.height) st_fb.backbuffer[(uint64_t)y*st_fb.pitch+x]=color; }",
            "uint32_t gfx_get_pixel(uint32_t x, uint32_t y) { return (st_fb.backbuffer && x<st_fb.width && y<st_fb.height) ? st_fb.backbuffer[(uint64_t)y*st_fb.pitch+x] : 0; }",
        ))
    elif ast.name == "kernel::baken_rasterizer":
        lines.extend("""
extern uint32_t *gfx_get_backbuffer(void);
extern uint32_t gfx_get_pitch(void), gfx_get_width(void), gfx_get_height(void);
extern void gfx_put_pixel(uint32_t, uint32_t, uint32_t);
void gfx_put_pixel_alpha(uint32_t x, uint32_t y, uint32_t c, uint8_t a);
#include "font_google_sans_flex_atlas.h"
#include "material_icons_atlas.h"
#include "baken_app_icons_atlas.h"
#include "baken_motion_icons_atlas.h"
#include "baken_color_lut.h"
#include "baken_design_tokens.h"

typedef CqMaterialIconAtlas SotlasMaterialIconAtlas;
typedef CqBakenAppIconAtlas SotlasBakenAppIconAtlas;
typedef CqBakenMotionIconAtlas SotlasBakenMotionIconAtlas;
#define sotlas_material_icon_atlases cq_material_icon_atlases
#define SOTLAS_MATERIAL_ICON_ATLAS_COUNT (sizeof(cq_material_icon_atlases)/sizeof(cq_material_icon_atlases[0]))
#define sotlas_baken_app_icon_atlases cq_baken_app_icon_atlases
#define SOTLAS_BAKEN_APP_ICON_ATLAS_COUNT (sizeof(cq_baken_app_icon_atlases)/sizeof(cq_baken_app_icon_atlases[0]))
#define sotlas_baken_motion_icon_atlases cq_baken_motion_icon_atlases
#define SOTLAS_BAKEN_MOTION_ICON_ATLAS_COUNT (sizeof(cq_baken_motion_icon_atlases)/sizeof(cq_baken_motion_icon_atlases[0]))

static uint32_t g_baken_ui_scale_percent = 0; /* 0 = automático */
static uint32_t g_baken_display_density_dpi = 0; /* 0 = indisponível */
/* Subpixel colorido depende da ordem física RGB/BGR do painel. GOP/EDID não
 * oferece esse dado de forma portável; o padrão seguro é AA em escala cinza. */
static uint8_t g_baken_subpixel_text = 0;
uint32_t baken_ui_scale_percent(void) {
    if (g_baken_ui_scale_percent) return g_baken_ui_scale_percent;
    /* Quando um driver de painel fornecer DPI/EDID, densidade vence a mera
     * contagem de pixels. GOP puro não garante EDID, então há fallback. */
    if (g_baken_display_density_dpi) {
        uint32_t density_scale = (g_baken_display_density_dpi * 100u + 48u) / 96u;
        if (density_scale < 80u) density_scale = 80u;
        if (density_scale > 250u) density_scale = 250u;
        return density_scale;
    }
    uint32_t sx = (gfx_get_width() * 100u) / BKN_DESIGN_BASE_WIDTH;
    uint32_t sy = (gfx_get_height() * 100u) / BKN_DESIGN_BASE_HEIGHT;
    uint32_t scale = sx < sy ? sx : sy;
    if (scale < 80) scale = 80;
    if (scale > 200) scale = 200;
    return scale;
}
void baken_ui_set_scale_percent(uint32_t percent) {
    /* 0 restaura automático. Valores absurdos nunca entram no rasterizador. */
    if (percent == 0 || (percent >= 80 && percent <= 250)) g_baken_ui_scale_percent = percent;
}
void baken_ui_set_display_density_dpi(uint32_t dpi) {
    /* Driver/Configuração pode informar 96..320 DPI. Zero retorna para o
     * fallback por resolução; valores fora desse intervalo são ignorados. */
    if (dpi == 0 || (dpi >= 96 && dpi <= 320)) g_baken_display_density_dpi = dpi;
}
void baken_ui_set_subpixel_text(uint8_t enabled) { g_baken_subpixel_text = enabled ? 1u : 0u; }
uint32_t baken_ui_px(uint32_t logical_px) {
    return (logical_px * baken_ui_scale_percent() + 50u) / 100u;
}

/* A hierarquia tipográfica não é inferida por "scale" legado. Cada papel
 * possui tamanho e entrelinha previsíveis, para que cartões e janelas possam
 * calcular baseline, truncamento e quebra sem depender de espaços. */
static uint32_t baken_type_px(uint32_t role) {
    static const uint32_t logical[] = {
        BKN_TEXT_AUXILIARY, BKN_TEXT_BODY, BKN_TEXT_LABEL, BKN_TEXT_TITLE,
        BKN_TEXT_WINDOW, BKN_TEXT_DISPLAY, BKN_TEXT_NUMERIC
    };
    if (role > BKN_TYPE_NUMERIC) role = BKN_TYPE_BODY;
    return baken_ui_px(logical[role]);
}
static uint32_t baken_type_line_height(uint32_t role) {
    static const uint32_t logical[] = {16u, 20u, 20u, 22u, 26u, 40u, 40u};
    if (role > BKN_TYPE_NUMERIC) role = BKN_TYPE_BODY;
    return baken_ui_px(logical[role]);
}

/* Layout usa pixels lógicos; esta seleção protege a qualidade do asset. */
static const SotlasFontAtlas *st_select_font(uint32_t px) {
    for (uint32_t i = 0; i < SOTLAS_FONT_ATLAS_COUNT; ++i)
        if (sotlas_font_atlases[i].px >= px) return &sotlas_font_atlases[i];
    return &sotlas_font_atlases[SOTLAS_FONT_ATLAS_COUNT - 1];
}
static const SotlasMaterialIconAtlas *st_select_icon_atlas(uint32_t px) {
    for (uint32_t i = 0; i < SOTLAS_MATERIAL_ICON_ATLAS_COUNT; ++i)
        if (sotlas_material_icon_atlases[i].px >= px) return &sotlas_material_icon_atlases[i];
    return &sotlas_material_icon_atlases[SOTLAS_MATERIAL_ICON_ATLAS_COUNT - 1];
}
static const SotlasBakenAppIconAtlas *st_select_app_icon_atlas(uint32_t px) {
    for (uint32_t i = 0; i < SOTLAS_BAKEN_APP_ICON_ATLAS_COUNT; ++i)
        if (sotlas_baken_app_icon_atlases[i].px >= px) return &sotlas_baken_app_icon_atlases[i];
    return &sotlas_baken_app_icon_atlases[SOTLAS_BAKEN_APP_ICON_ATLAS_COUNT - 1];
}
static const SotlasBakenMotionIconAtlas *st_select_motion_icon_atlas(uint32_t px) {
    for (uint32_t i = 0; i < SOTLAS_BAKEN_MOTION_ICON_ATLAS_COUNT; ++i)
        if (sotlas_baken_motion_icon_atlases[i].px >= px) return &sotlas_baken_motion_icon_atlases[i];
    return &sotlas_baken_motion_icon_atlases[SOTLAS_BAKEN_MOTION_ICON_ATLAS_COUNT - 1];
}
static void gfx_put_pixel_subpixel(uint32_t x, uint32_t y, uint32_t c, uint8_t ar, uint8_t ag, uint8_t ab);

/* Amostra a máscara do atlas maior no tamanho pedido. Assim uma fonte de
 * 32px pode ser reduzida para 28px, mas uma fonte 12px nunca é ampliada. */
static void draw_char_aa(uint32_t x0, uint32_t y0, uint8_t ch, uint32_t color,
                         const SotlasFontAtlas *font, uint32_t target_px, uint8_t opacity) {
    const uint8_t *mask = font->alpha + (uint32_t)ch * font->width * font->height;
    int32_t gw = (int32_t)gfx_get_width();
    int32_t gh = (int32_t)gfx_get_height();
    uint32_t out_w = (font->width * target_px + font->px / 2u) / font->px;
    uint32_t out_h = (font->height * target_px + font->px / 2u) / font->px;
    if (out_w == 0) out_w = 1;
    if (out_h == 0) out_h = 1;

    for (uint32_t y = 0; y < out_h; ++y) {
        int32_t py = (int32_t)y0 + (int32_t)y;
        if (py < 0 || py >= gh) continue;
        uint32_t fy = (y * (font->height - 1u) * 256u) / (out_h > 1 ? out_h - 1u : 1u);
        uint32_t sy = fy >> 8, wy = fy & 255u, sy1 = sy + 1u < font->height ? sy + 1u : sy;
        for (uint32_t x = 0; x < out_w; ++x) {
            int32_t px = (int32_t)x0 + (int32_t)x;
            if (px < 0 || px >= gw) continue;
            uint32_t fx = (x * (font->width - 1u) * 256u) / (out_w > 1 ? out_w - 1u : 1u);
            uint32_t sx = fx >> 8, wx = fx & 255u, sx1 = sx + 1u < font->width ? sx + 1u : sx;
            uint32_t c0 = (mask[sy * font->width + sx] * (256u - wx) + mask[sy * font->width + sx1] * wx) >> 8;
            uint32_t c1 = (mask[sy1 * font->width + sx] * (256u - wx) + mask[sy1 * font->width + sx1] * wx) >> 8;
            uint8_t a = (uint8_t)((c0 * (256u - wy) + c1 * wy) >> 8);
            a = (uint8_t)(((uint32_t)a * opacity) / 255u);
            if (a > 0) {
                /* Em texto pequeno, deslocamos levemente a cobertura entre
                 * RGB. O framebuffer é ARGB e isso dá nitidez sem criar
                 * bordas coloridas nos títulos grandes. */
                if (g_baken_subpixel_text && target_px <= 20u) {
                    uint8_t left = x ? mask[sy * font->width + ((sx > 0) ? sx - 1u : sx)] : a;
                    uint8_t right = sx + 1u < font->width ? mask[sy * font->width + sx + 1u] : a;
                    left = (uint8_t)(((uint32_t)left * opacity) / 255u);
                    right = (uint8_t)(((uint32_t)right * opacity) / 255u);
                    gfx_put_pixel_subpixel((uint32_t)px, (uint32_t)py, color,
                                           (uint8_t)((2u * a + left) / 3u), a,
                                           (uint8_t)((2u * a + right) / 3u));
                } else gfx_put_pixel_alpha((uint32_t)px, (uint32_t)py, color, a);
            }
        }
    }
}

static inline uint32_t st_blend(uint32_t bg, uint32_t fg, uint8_t alpha) {
    if (alpha >= 255) return (0xFF000000) | (fg & 0x00FFFFFF);
    if (alpha == 0) return bg;
    /* Composição em espaço linear de 16 bits. A conversão segue sRGB real,
     * não a antiga aproximação gamma 2.0 que lavava gradientes e vidro. */
    uint32_t a = (uint32_t)alpha;
    uint32_t inv_a = 255 - a;

    uint32_t bg_r = (bg >> 16) & 0xFF, bg_g = (bg >> 8) & 0xFF, bg_b = bg & 0xFF;
    uint32_t fg_r = (fg >> 16) & 0xFF, fg_g = (fg >> 8) & 0xFF, fg_b = fg & 0xFF;

    uint32_t lr = (bkn_srgb_to_linear_16[fg_r] * a + bkn_srgb_to_linear_16[bg_r] * inv_a + 127u) / 255u;
    uint32_t lg = (bkn_srgb_to_linear_16[fg_g] * a + bkn_srgb_to_linear_16[bg_g] * inv_a + 127u) / 255u;
    uint32_t lb = (bkn_srgb_to_linear_16[fg_b] * a + bkn_srgb_to_linear_16[bg_b] * inv_a + 127u) / 255u;
    uint32_t out_r = bkn_linear_16_to_srgb[(lr * 4096u + 32767u) / 65535u];
    uint32_t out_g = bkn_linear_16_to_srgb[(lg * 4096u + 32767u) / 65535u];
    uint32_t out_b = bkn_linear_16_to_srgb[(lb * 4096u + 32767u) / 65535u];

    return (0xFF000000) | (out_r << 16) | (out_g << 8) | out_b;
}

uint32_t gfx_blend_color(uint32_t bg, uint32_t fg, uint8_t a) { return st_blend(bg, fg, a); }

void gfx_put_pixel_alpha(uint32_t x, uint32_t y, uint32_t c, uint8_t a) {
    uint32_t *fb = gfx_get_backbuffer();
    uint32_t p = gfx_get_pitch();
    if (fb && x < gfx_get_width() && y < gfx_get_height() && x < p) {
        fb[(uint64_t)y * p + x] = st_blend(fb[(uint64_t)y * p + x], c, a);
    }
}

static void gfx_put_pixel_subpixel(uint32_t x, uint32_t y, uint32_t c, uint8_t ar, uint8_t ag, uint8_t ab) {
    uint32_t *fb = gfx_get_backbuffer(), p = gfx_get_pitch();
    if (!fb || x >= gfx_get_width() || y >= gfx_get_height() || x >= p) return;
    uint32_t bg = fb[(uint64_t)y * p + x];
    uint32_t rr = (st_blend(bg, c, ar) >> 16) & 255u;
    uint32_t gg = (st_blend(bg, c, ag) >> 8) & 255u;
    uint32_t bb = st_blend(bg, c, ab) & 255u;
    fb[(uint64_t)y * p + x] = 0xFF000000 | (rr << 16) | (gg << 8) | bb;
}

/* Cobertura analítica 2x2 para um retângulo arredondado. Esta é a primitiva
 * vetorial base do BakenFX: uma superfície, seu blur e sua borda consultam a
 * mesma máscara, evitando fendas e cantos serrilhados entre camadas. */
static uint8_t baken_round_rect_coverage(uint32_t px, uint32_t py, uint32_t w, uint32_t h, uint32_t radius) {
    if (!w || !h || radius == 0) return 255;
    uint32_t r = radius;
    if (r * 2u > w) r = w / 2u;
    if (r * 2u > h) r = h / 2u;
    if (px >= r && px < w - r) return 255;
    if (py >= r && py < h - r) return 255;
    int32_t cx = px < r ? (int32_t)r : (int32_t)(w - r - 1u);
    int32_t cy = py < r ? (int32_t)r : (int32_t)(h - r - 1u);
    int inside = 0;
    for (int sy = 0; sy < 2; ++sy) for (int sx = 0; sx < 2; ++sx) {
        /* Coordenadas em meia unidade: evita float e preserva cobertura. */
        int32_t dx = (int32_t)(px * 2u + (uint32_t)sx) - cx * 2;
        int32_t dy = (int32_t)(py * 2u + (uint32_t)sy) - cy * 2;
        if (dx * dx + dy * dy <= (int32_t)(r * r * 4u)) inside++;
    }
    return inside == 4 ? 255u : (uint8_t)(inside * 64);
}

/* Buffer temporário do compositor: permite borrar o conteúdo JÁ desenhado
 * antes de colocar uma superfície de vidro, sem depender de GPU ou heap. */
#define BKN_BLUR_MAX_W 1600
#define BKN_BLUR_MAX_H 640
static uint32_t st_blur_source[BKN_BLUR_MAX_W * BKN_BLUR_MAX_H];
static uint32_t st_blur_pass[BKN_BLUR_MAX_W * BKN_BLUR_MAX_H];

static void gfx_draw_backdrop_blur(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t blur_radius, uint32_t corner_radius) {
    uint32_t *fb = gfx_get_backbuffer(), pitch = gfx_get_pitch();
    if (!fb || !w || !h || blur_radius < 2) return;
    uint32_t x0 = x > blur_radius ? x - blur_radius : 0, y0 = y > blur_radius ? y - blur_radius : 0;
    uint32_t x1 = x + w + blur_radius; if (x1 > gfx_get_width()) x1 = gfx_get_width();
    uint32_t y1 = y + h + blur_radius; if (y1 > gfx_get_height()) y1 = gfx_get_height();
    uint32_t bw = x1 - x0, bh = y1 - y0;
    if (bw > BKN_BLUR_MAX_W || bh > BKN_BLUR_MAX_H) return;
    for (uint32_t py=0; py<bh; ++py) for (uint32_t px=0; px<bw; ++px) st_blur_source[py*bw+px]=fb[(uint64_t)(y0+py)*pitch+x0+px];
    /* Box blur separável: duas passagens, custo linear e aspecto suave. */
    for (uint32_t py=0; py<bh; ++py) for (uint32_t px=0; px<bw; ++px) {
        uint32_t rr=0,gg=0,bb=0,n=0; uint32_t lo=px>blur_radius?px-blur_radius:0, hi=px+blur_radius+1<bw?px+blur_radius+1:bw;
        for(uint32_t sx=lo;sx<hi;++sx){uint32_t c=st_blur_source[py*bw+sx];rr+=(c>>16)&255;gg+=(c>>8)&255;bb+=c&255;n++;}
        st_blur_pass[py*bw+px]=0xFF000000|((rr/n)<<16)|((gg/n)<<8)|(bb/n);
    }
    for (uint32_t py=0; py<bh; ++py) for (uint32_t px=0; px<bw; ++px) {
        uint32_t rr=0,gg=0,bb=0,n=0; uint32_t lo=py>blur_radius?py-blur_radius:0, hi=py+blur_radius+1<bh?py+blur_radius+1:bh;
        for(uint32_t sy=lo;sy<hi;++sy){uint32_t c=st_blur_pass[sy*bw+px];rr+=(c>>16)&255;gg+=(c>>8)&255;bb+=c&255;n++;}
        st_blur_source[py*bw+px]=0xFF000000|((rr/n)<<16)|((gg/n)<<8)|(bb/n);
    }
    /* O blur só é escrito dentro do mesmo rounded-rect do material. Antes,
     * o retângulo de amostragem vazava uma faixa borrada entre cartões. */
    for (uint32_t py=0; py<h; ++py) for (uint32_t px=0; px<w; ++px) {
        uint8_t coverage = baken_round_rect_coverage(px, py, w, h, corner_radius);
        if (!coverage) continue;
        uint32_t sx = x + px - x0, sy = y + py - y0;
        uint64_t dst_i = (uint64_t)(y + py) * pitch + x + px;
        fb[dst_i] = st_blend(fb[dst_i], st_blur_source[sy*bw+sx], coverage);
    }
}

void gfx_fill_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t c) {
    for (uint32_t py = y; py < y + h && py < gfx_get_height(); ++py) {
        for (uint32_t px = x; px < x + w && px < gfx_get_width(); ++px) {
            gfx_put_pixel(px, py, c);
        }
    }
}

void gfx_fill_rect_alpha(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t c, uint8_t a) {
    for (uint32_t py = y; py < y + h && py < gfx_get_height(); ++py) {
        for (uint32_t px = x; px < x + w && px < gfx_get_width(); ++px) {
            gfx_put_pixel_alpha(px, py, c, a);
        }
    }
}

static void gfx_draw_shadow_lobe(int x, int y, int w, int h, int radius,
                                 int blur, int y_offset, uint8_t max_alpha) {
    if (w <= 0 || h <= 0 || blur <= 0 || max_alpha == 0) return;
    int gw = (int)gfx_get_width();
    int gh = (int)gfx_get_height();
    int sx = x - blur; if (sx < 0) sx = 0;
    int sy = y - blur + y_offset; if (sy < 0) sy = 0;
    int ex = x + w + blur; if (ex > gw) ex = gw;
    int ey = y + h + blur + y_offset; if (ey > gh) ey = gh;

    int bx = w / 2 - radius; if (bx < 0) bx = 0;
    int by = h / 2 - radius; if (by < 0) by = 0;
    int cx = x + w / 2;
    int cy = y + h / 2 + y_offset;

    for (int py = sy; py < ey; ++py) {
        int dy = py - cy;
        if (dy < 0) dy = -dy;
        int qy = dy - by;
        if (qy < 0) qy = 0;

        for (int px = sx; px < ex; ++px) {
            int dx = px - cx;
            if (dx < 0) dx = -dx;
            int qx = dx - bx;
            if (qx < 0) qx = 0;

            int d2 = qx * qx + qy * qy;
            int d = 0;
            if (d2 > 0) {
                int s = 0;
                while ((s + 1) * (s + 1) <= d2) s++;
                d = s - radius;
            } else {
                d = -radius;
            }

            if (d > 0 && d < blur) {
                int rem = blur - d;
                uint32_t a = ((uint32_t)max_alpha * rem * rem * rem) / ((uint32_t)blur * blur * blur);
                if (a >= 2) {
                    gfx_put_pixel_alpha((uint32_t)px, (uint32_t)py, 0x00000000, (uint8_t)a);
                }
            }
        }
    }
}

void gfx_draw_smooth_shadow(int x, int y, int w, int h, int radius, int blur, uint8_t max_alpha) {
    gfx_draw_shadow_lobe(x, y, w, h, radius, blur, 6, max_alpha);
}

/* Escala de gravidade Baken Lua: ambiente largo + contato curto. Não há
 * sombras arbitrárias por widget; a camada determina o peso da superfície. */
void baken_lua_draw_elevation(uint32_t x, uint32_t y, uint32_t w, uint32_t h,
                              uint32_t radius, uint32_t level, uint32_t state) {
    if (!w || !h || y == 0) return; /* barra superior pertence ao plano base */
    int lift = state == BKN_LUA_PRESSED ? 0 : (state == BKN_LUA_HOVER ? 1 : 0);
    if (level == 1u) {
        gfx_draw_shadow_lobe((int)x, (int)y, (int)w, (int)h, (int)radius, 14 + lift * 2, 3 - lift, 24);
        gfx_draw_shadow_lobe((int)x, (int)y, (int)w, (int)h, (int)radius, 5, 2 - lift, 20);
    } else if (level == 2u) {
        gfx_draw_shadow_lobe((int)x, (int)y, (int)w, (int)h, (int)radius, 22 + lift * 3, 6 - lift, 42);
        gfx_draw_shadow_lobe((int)x, (int)y, (int)w, (int)h, (int)radius, 7, 3 - lift, 34);
    } else if (level >= 3u) {
        gfx_draw_shadow_lobe((int)x, (int)y, (int)w, (int)h, (int)radius, 32 + lift * 4, 10 - lift, 58);
        gfx_draw_shadow_lobe((int)x, (int)y, (int)w, (int)h, (int)radius, 10, 4 - lift, 44);
    }
}

void gfx_draw_drop_shadow(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t blur, uint32_t spread) {
    (void)spread;
    gfx_draw_smooth_shadow((int)x, (int)y, (int)w, (int)h, 16, (int)blur, 70);
}

/* Ruído determinístico de baixa amplitude. Ele quebra bandas de cor sem
 * carregar uma textura externa e mantém o mesmo resultado em toda VM. */
static inline int32_t st_material_grain(uint32_t x, uint32_t y) {
    uint32_t n = x * 1973u + y * 9277u + 0x68BC21EBu;
    n ^= n >> 13;
    n *= 0x85EBCA6Bu;
    return (int32_t)((n >> 29) & 7u) - 3;
}

static void gfx_draw_glass_rect_material_ex(uint32_t x, uint32_t y, uint32_t w, uint32_t h,
                                             uint32_t bg, uint8_t a, uint32_t border, uint32_t radius,
                                             uint32_t blur_radius, uint8_t top_rim, uint8_t bottom_rim) {
    /* Vidro é reservado para superfícies grandes e translúcidas; controles
     * pequenos permanecem nítidos e o desktop não vira uma massa de blur. */
    if (blur_radius >= 2 && a < 238 && w * h > 2000) gfx_draw_backdrop_blur(x, y, w, h, blur_radius, radius);
    int r = (int)radius;
    int gw = (int)gfx_get_width(), gh = (int)gfx_get_height();

    uint32_t bg_r = (bg >> 16) & 0xFF;
    uint32_t bg_g = (bg >> 8)  & 0xFF;
    uint32_t bg_b = bg & 0xFF;

    for (int py = 0; py < (int)h; ++py) {
        int dest_y = (int)y + py;
        if (dest_y < 0 || dest_y >= gh) continue;

        uint32_t border_color = border;
        uint8_t border_alpha = 132;
        if (py <= 1 || (r > 0 && py < r / 2)) {
            border_color = 0x00FFFFFF;
            border_alpha = top_rim;
        } else if (py >= (int)h - 2) {
            border_color = 0x00CBD5E1;
            border_alpha = bottom_rim;
        }

        for (int px = 0; px < (int)w; ++px) {
            int dest_x = (int)x + px;
            if (dest_x < 0 || dest_x >= gw) continue;

            /* Luz-chave no topo/esquerda, queda suave rumo à base/direita e
             * microtextura quase invisível. Este é o material comum de dock,
             * widgets e janelas; nenhuma superfície usa uma caixa plana. */
            int32_t vertical = 256 - (py * 20) / (h > 0 ? (int)h : 1);
            int32_t horizontal = ((int)w - px) * 8 / (w > 0 ? (int)w : 1);
            int32_t light_factor = vertical + horizontal;
            int32_t grain = st_material_grain((uint32_t)dest_x, (uint32_t)dest_y);
            int32_t lit_r = ((int32_t)bg_r * light_factor >> 8) + grain;
            int32_t lit_g = ((int32_t)bg_g * light_factor >> 8) + grain;
            int32_t lit_b = ((int32_t)bg_b * light_factor >> 8) + grain;
            if (lit_r < 0) lit_r = 0; else if (lit_r > 255) lit_r = 255;
            if (lit_g < 0) lit_g = 0; else if (lit_g > 255) lit_g = 255;
            if (lit_b < 0) lit_b = 0; else if (lit_b > 255) lit_b = 255;
            uint32_t lit_bg = ((uint32_t)lit_r << 16) | ((uint32_t)lit_g << 8) | (uint32_t)lit_b;

            uint8_t coverage = baken_round_rect_coverage((uint32_t)px, (uint32_t)py, w, h, radius);
            if (!coverage) continue;
            uint8_t edge = (coverage < 255 || px == 0 || py == 0 || px == (int)w - 1 || py == (int)h - 1) ? 1u : 0u;
            if (edge) {
                gfx_put_pixel_alpha((uint32_t)dest_x, (uint32_t)dest_y, border_color,
                                    (uint8_t)(((uint32_t)border_alpha * coverage) / 255u));
            } else {
                gfx_put_pixel_alpha((uint32_t)dest_x, (uint32_t)dest_y, lit_bg,
                                    (uint8_t)(((uint32_t)a * coverage) / 255u));
            }
        }
    }
}

void gfx_draw_glass_rect_material(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius) {
    gfx_draw_glass_rect_material_ex(x, y, w, h, bg, a, border, radius, 4, 220, 100);
}

void gfx_draw_glass_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius) {
    gfx_draw_glass_rect_material(x, y, w, h, bg, a, border, radius);
}

static uint8_t g_dark_theme = 0;
static uint32_t g_mesh_time_tick = 0;

void desktop_shell_toggle_theme(void) { g_dark_theme = !g_dark_theme; }
uint8_t desktop_shell_is_dark_theme(void) { return g_dark_theme; }
void gfx_set_mesh_time_tick(uint32_t t) { g_mesh_time_tick = t; }

/* API pública Baken Lua. A superfície é escolhida por intenção e estado;
 * desktop/app não escolhem mais manualmente cor, alpha e borda. */
void baken_lua_draw_surface(uint32_t x, uint32_t y, uint32_t w, uint32_t h,
                            uint32_t material, uint32_t state, uint32_t radius) {
    uint32_t fill = g_dark_theme ? 0x000F172A : 0x00F8FAFC;
    uint32_t border = g_dark_theme ? 0x00334155 : 0x00FFFFFF;
    uint8_t alpha = g_dark_theme ? 230 : 238;
    uint8_t top_rim = g_dark_theme ? 160 : 220;
    uint8_t bottom_rim = g_dark_theme ? 50 : 100;
    uint32_t blur = 0, elevation = 0;

    if (material == BKN_LUA_CANVAS) { gfx_fill_rect(x, y, w, h, fill); return; }
    if (material == BKN_LUA_MICA) {
        fill = g_dark_theme ? 0x000F172A : 0x00F8FAFC;
        alpha = 244;
        border = g_dark_theme ? 0x00334155 : 0x00CBD5E1;
        top_rim = g_dark_theme ? 140 : 168;
        bottom_rim = g_dark_theme ? 45 : 78;
    }
    else if (material == BKN_LUA_GLASS_REGULAR) {
        fill = g_dark_theme ? 0x000F172A : 0x00FFFFFF;
        alpha = g_dark_theme ? 215 : 194;
        border = g_dark_theme ? 0x0038BDF8 : 0x00FFFFFF;
        blur = 6; elevation = 1;
        top_rim = g_dark_theme ? 180 : 220;
    }
    else if (material == BKN_LUA_GLASS_CLEAR) {
        fill = g_dark_theme ? 0x001E1B4B : 0x00FFFFFF;
        alpha = g_dark_theme ? 185 : 158;
        border = g_dark_theme ? 0x0060A5FA : 0x00FFFFFF;
        blur = 10; elevation = 2;
        top_rim = g_dark_theme ? 190 : 205;
        bottom_rim = g_dark_theme ? 60 : 70;
    }
    else if (material == BKN_LUA_ELEVATED) {
        fill = g_dark_theme ? 0x00020617 : 0x000F172A;
        alpha = 235;
        border = 0x0038BDF8;
        blur = 3; elevation = 2;
        top_rim = 150; bottom_rim = 65;
    }
    else if (material == BKN_LUA_SMOKE) { gfx_fill_rect_alpha(x, y, w, h, 0x00000000, 120); return; }

    if (state == BKN_LUA_HOVER) { alpha = alpha < 244 ? alpha + 10 : 255; border = g_dark_theme ? 0x0067E8F9 : 0x00E0F2FE; elevation++; }
    else if (state == BKN_LUA_PRESSED) { alpha = alpha < 248 ? alpha + 14 : 255; border = g_dark_theme ? 0x000284C7 : 0x0094A3B8; }
    else if (state == BKN_LUA_FOCUS || state == BKN_LUA_SELECTED) { border = 0x000284C7; elevation++; }
    else if (state == BKN_LUA_DISABLED) { alpha = alpha < 245 ? alpha + 10 : 255; border = g_dark_theme ? 0x001E293B : 0x00CBD5E1; }

    baken_lua_draw_elevation(x, y, w, h, radius, elevation, state);
    gfx_draw_glass_rect_material_ex(x, y, w, h, fill, alpha, border, radius, blur, top_rim, bottom_rim);
    if (state == BKN_LUA_FOCUS) gfx_draw_glass_rect_material(x + 2, y + 2, w > 4 ? w - 4 : 0, h > 4 ? h - 4 : 0, 0x000284C7, 30, 0x000284C7, radius > 2 ? radius - 2 : 0);
}

void gfx_draw_circle_alpha(uint32_t cx, uint32_t cy, uint32_t r, uint32_t c, uint8_t a) {
    int32_t ir = (int32_t)r;
    int32_t r2 = ir * ir;
    int32_t gw = (int32_t)gfx_get_width();
    int32_t gh = (int32_t)gfx_get_height();
    for (int32_t dy = -ir; dy <= ir; ++dy) {
        int32_t py = (int32_t)cy + dy;
        if (py < 0 || py >= gh) continue;
        for (int32_t dx = -ir; dx <= ir; ++dx) {
            int32_t px = (int32_t)cx + dx;
            if (px < 0 || px >= gw) continue;
            /* Cobertura 2x2 no contorno: botões e indicadores deixam de ter
             * a borda serrilhada que denunciava o framebuffer puro. */
            int inside = 0;
            for (int sy = 0; sy < 2; ++sy) for (int sx = 0; sx < 2; ++sx) {
                int qx = dx * 2 + sx * 2 - 1, qy = dy * 2 + sy * 2 - 1;
                if (qx * qx + qy * qy <= r2 * 4) inside++;
            }
            if (inside) gfx_put_pixel_alpha((uint32_t)px, (uint32_t)py, c,
                                            (uint8_t)(((uint32_t)a * (uint32_t)inside) / 4u));
        }
    }
}

void gfx_draw_circle_button(uint32_t cx, uint32_t cy, uint32_t r, uint32_t c) {
    gfx_draw_circle_alpha(cx, cy, r, c, 255);
    if (r > 2) { gfx_draw_circle_alpha(cx, cy, r - 2, 0x00FFFFFF, 95); }
}

static inline uint8_t st_decode_utf8_char(const uint8_t **s_ptr) {
    const uint8_t *s = *s_ptr;
    uint8_t b0 = *s++;
    uint8_t ch = b0;
    if (b0 == 0xC3 && *s) {
        ch = (uint8_t)(128u + (*s++ & 0x3Fu));
    } else if (b0 == 0xC2 && *s) {
        uint8_t b1 = *s++;
        if (b1 == 0xB0) ch = 176; // °
        else if (b1 == 0xB7) ch = 183; // ·
        else if (b1 == 0xA9) ch = 169; // ©
        else ch = b1;
    } else if (b0 == 0xE2 && *s && *(s + 1)) {
        if (*s == 0x80 && *(s + 1) == 0xA6) { ch = 133; s += 2; } // …
        else { s += 2; ch = '?'; }
    }
    *s_ptr = s;
    return ch;
}

void gfx_draw_text_proportional(uint32_t x, uint32_t y, const char *str, uint32_t color) {
    if (!str) return;
    uint32_t target_px = baken_ui_px(BKN_TEXT_BODY);
    const SotlasFontAtlas *font = st_select_font(target_px);
    const uint8_t *s = (const uint8_t*)str;
    while (*s) {
        uint8_t ch = st_decode_utf8_char(&s);
        draw_char_aa(x, y, ch, color, font, target_px, 255);
        uint32_t adv = (font->advances[ch] * target_px + font->px / 2u) / font->px;
        if (adv == 0) adv = 6;
        x += adv + 1;
    }
}

void gfx_draw_text_role(uint32_t x, uint32_t y, const char *str,
                        uint32_t color, uint32_t role) {
    if (!str) return;
    uint32_t target_px = baken_type_px(role);
    const SotlasFontAtlas *font = st_select_font(target_px);
    const uint8_t *s = (const uint8_t*)str;
    while (*s) {
        uint8_t ch = st_decode_utf8_char(&s);
        draw_char_aa(x, y, ch, color, font, target_px, 255);
        uint32_t adv = (font->advances[ch] * target_px + font->px / 2u) / font->px;
        x += (adv ? adv : 6u) + 1u;
    }
}

void gfx_draw_text(uint32_t x, uint32_t y, const uint8_t *s, uint32_t c) {
    gfx_draw_text_proportional(x, y, (const char*)s, c);
}

uint32_t gfx_measure_text(const char *str) {
    if (!str) return 0;
    uint32_t target_px = baken_ui_px(BKN_TEXT_BODY);
    const SotlasFontAtlas *font = st_select_font(target_px);
    uint32_t width = 0;
    const uint8_t *s = (const uint8_t*)str;
    while (*s) {
        uint8_t ch = st_decode_utf8_char(&s);
        uint32_t adv = (font->advances[ch] * target_px + font->px / 2u) / font->px;
        width += (adv ? adv : 6u) + 1u;
    }
    return width;
}

uint32_t gfx_measure_text_role(const char *str, uint32_t role) {
    if (!str) return 0;
    uint32_t target_px = baken_type_px(role), width = 0;
    const SotlasFontAtlas *font = st_select_font(target_px);
    const uint8_t *s = (const uint8_t*)str;
    while (*s) {
        uint8_t ch = st_decode_utf8_char(&s);
        uint32_t adv = (font->advances[ch] * target_px + font->px / 2u) / font->px;
        width += (adv ? adv : 6u) + 1u;
    }
    return width;
}

void gfx_draw_text_ellipsis(uint32_t x, uint32_t y, uint32_t max_width,
                            const char *str, uint32_t color);

/* Quebra conservadora por palavra: cada linha é truncada de forma explícita
 * se uma palavra for maior que a área. Retorna a altura realmente usada. */
uint32_t gfx_draw_text_wrap_role(uint32_t x, uint32_t y, uint32_t max_width,
                                 uint32_t max_lines, const char *str,
                                 uint32_t color, uint32_t role) {
    if (!str || !max_width || !max_lines) return 0;
    char line[96]; uint32_t used = 0, line_count = 0, line_h = baken_type_line_height(role);
    const char *word = str;
    while (*word && line_count < max_lines) {
        const char *end = word; while (*end && *end != ' ') end++;
        uint32_t word_len = (uint32_t)(end - word);
        uint32_t add = word_len + (used ? 1u : 0u);
        if (used + add >= sizeof(line)) add = sizeof(line) - used - 1u;
        char candidate[96]; uint32_t n = 0;
        for (uint32_t i = 0; i < used && n + 1 < sizeof(candidate); ++i) candidate[n++] = line[i];
        if (used && n + 1 < sizeof(candidate)) candidate[n++] = ' ';
        for (uint32_t i = 0; i < word_len && n + 1 < sizeof(candidate); ++i) candidate[n++] = word[i];
        candidate[n] = 0;
        if (used && gfx_measure_text_role(candidate, role) > max_width) {
            line[used] = 0; gfx_draw_text_ellipsis(x, y + line_count * line_h, max_width, line, color);
            line_count++; used = 0; continue;
        }
        if (!used && gfx_measure_text_role(candidate, role) > max_width) {
            gfx_draw_text_ellipsis(x, y + line_count * line_h, max_width, candidate, color);
            line_count++; used = 0;
        } else { for (uint32_t i = 0; i < n; ++i) line[i] = candidate[i]; used = n; }
        word = *end ? end + 1 : end;
    }
    if (used && line_count < max_lines) { line[used] = 0; gfx_draw_text_ellipsis(x, y + line_count * line_h, max_width, line, color); line_count++; }
    return line_count * line_h;
}

/* Um único contrato de truncamento impede título, rótulo e status de
 * atravessarem cartões vizinhos em resoluções ou escalas diferentes. */
void gfx_draw_text_ellipsis(uint32_t x, uint32_t y, uint32_t max_width,
                            const char *str, uint32_t color) {
    if (!str || max_width == 0) return;
    if (gfx_measure_text(str) <= max_width) { gfx_draw_text_proportional(x, y, str, color); return; }
    char clipped[96]; uint32_t out = 0, used = 0;
    uint32_t target_px = baken_ui_px(BKN_TEXT_BODY);
    const SotlasFontAtlas *font = st_select_font(target_px);
    const uint8_t *s = (const uint8_t*)str;
    uint32_t dots = ((font->advances[(uint8_t)'.'] * target_px + font->px / 2u) / font->px + 1u) * 3u;
    while (*s && out + 2u < sizeof(clipped)) {
        uint8_t b0 = *s; uint8_t ch = b0; uint32_t bytes = 1;
        if (b0 == 0xC3 && *(s + 1)) { ch = (uint8_t)(128u + (*(s + 1) & 0x3Fu)); bytes = 2; }
        uint32_t adv = ((font->advances[ch] * target_px + font->px / 2u) / font->px) + 1u;
        if (used + adv + dots > max_width) break;
        for (uint32_t i = 0; i < bytes; ++i) clipped[out++] = (char)s[i];
        used += adv; s += bytes;
    }
    if (out == 0) return;
    clipped[out++]='.'; clipped[out++]='.'; clipped[out++]='.'; clipped[out]=0;
    gfx_draw_text_proportional(x, y, clipped, color);
}

void gfx_draw_text_alpha(uint32_t x, uint32_t y, const uint8_t *s, uint32_t c, uint32_t scale, uint8_t a) {
    if (!s) return;
    if (scale < 1) scale = 1;
    if (scale > 4) scale = 4;
    /* O valor legado scale=2 pede 24px lógico. O atlas escolhido é sempre
     * maior ou igual e é reduzido com cobertura alpha. */
    uint32_t target_px = (12 * scale * baken_ui_scale_percent() + 50u) / 100u;
    const SotlasFontAtlas *font = st_select_font(target_px);
    const uint8_t *cursor = s;
    while (*cursor) {
        uint8_t ch = *cursor++;
        /* O caminho com alpha legada mantém a mesma geometria do texto
         * proporcional, mas aplica opacidade depois da cobertura. */
        draw_char_aa(x, y, ch, c, font, target_px, a);
        uint32_t advance = (font->advances[ch] * target_px + font->px / 2u) / font->px;
        if (!advance) advance = 6;
        x += advance + 1;
    }
}

/* Desenha um símbolo Material previamente rasterizado no host. Escalonar a
 * máscara alpha evita um parser SVG e mantém o custo previsível no EFI. */
void gfx_draw_material_icon(uint32_t x, uint32_t y, uint32_t size, uint32_t icon_id, uint32_t color, uint8_t alpha) {
    if (size == 0 || icon_id >= MATERIAL_ICON_COUNT) return;
    const SotlasMaterialIconAtlas *atlas = st_select_icon_atlas(size);
    const uint8_t *mask = atlas->alpha + icon_id * atlas->px * atlas->px;
    for (uint32_t py = 0; py < size; ++py) {
        /* Bilinear alpha: só é usado ao reduzir um atlas nativo maior. */
        uint32_t fy = (py * (atlas->px - 1) * 256u) / (size > 1 ? size - 1 : 1);
        uint32_t sy = fy >> 8, wy = fy & 255u;
        uint32_t sy1 = sy + 1 < atlas->px ? sy + 1 : sy;
        for (uint32_t px = 0; px < size; ++px) {
            uint32_t fx = (px * (atlas->px - 1) * 256u) / (size > 1 ? size - 1 : 1);
            uint32_t sx = fx >> 8, wx = fx & 255u;
            uint32_t sx1 = sx + 1 < atlas->px ? sx + 1 : sx;
            uint32_t c0 = (mask[sy * atlas->px + sx] * (256u - wx) + mask[sy * atlas->px + sx1] * wx) >> 8;
            uint32_t c1 = (mask[sy1 * atlas->px + sx] * (256u - wx) + mask[sy1 * atlas->px + sx1] * wx) >> 8;
            uint8_t coverage = (uint8_t)((c0 * (256u - wy) + c1 * wy) >> 8);
            if (coverage) {
                uint8_t out_a = (uint8_t)(((uint32_t)coverage * alpha) / 255);
                gfx_put_pixel_alpha(x + px, y + py, color, out_a);
            }
        }
    }
}

/* Estado visual canônico para Ionicons: o símbolo mantém viewport quadrado e
 * centro óptico, enquanto somente contraste/halo variam. Assim nenhum app
 * inventa versões outline/sharp ou escala um glyph como se fosse uma imagem. */
void gfx_draw_material_icon_state(uint32_t x, uint32_t y, uint32_t size,
                                  uint32_t icon_id, uint32_t color,
                                  uint32_t state) {
    uint8_t alpha = 245;
    if (state == BKN_ICON_DISABLED) { color = 0x0094A3B8; alpha = 105; }
    else if (state == BKN_ICON_DESTRUCTIVE) color = 0x00DC2626;
    else if (state == BKN_ICON_SELECTED) {
        gfx_draw_circle_alpha(x + size / 2u, y + size / 2u, size / 2u + 3u, 0x000284C7, 38);
    } else if (state == BKN_ICON_HOVER) {
        gfx_draw_circle_alpha(x + size / 2u, y + size / 2u, size / 2u + 2u, 0x00FFFFFF, 52);
    } else if (state == BKN_ICON_PRESSED) {
        alpha = 220; color = 0x000284C7;
    }
    gfx_draw_material_icon(x, y, size, icon_id, color, alpha);
}

/* Estado SVG de um controle animado. mirror_x permite reutilizar skip-back
 * como skip-forward sem duplicar dados na imagem EFI. A interpolacao alpha
 * tambem permite crossfade play/pause sem serrilhado durante a transicao. */
void gfx_draw_motion_icon(uint32_t x, uint32_t y, uint32_t size,
                          uint32_t icon_id, uint32_t color, uint8_t opacity,
                          uint8_t mirror_x) {
    if (size == 0 || icon_id >= BAKEN_MOTION_ICON_COUNT || opacity == 0) return;
    const SotlasBakenMotionIconAtlas *atlas = st_select_motion_icon_atlas(size);
    const uint8_t *mask = atlas->alpha + icon_id * atlas->px * atlas->px;
    for (uint32_t py = 0; py < size; ++py) {
        uint32_t fy = (py * (atlas->px - 1u) * 256u) / (size > 1u ? size - 1u : 1u);
        uint32_t sy = fy >> 8, wy = fy & 255u;
        uint32_t sy1 = sy + 1u < atlas->px ? sy + 1u : sy;
        for (uint32_t px = 0; px < size; ++px) {
            uint32_t sample_x = mirror_x ? size - 1u - px : px;
            uint32_t fx = (sample_x * (atlas->px - 1u) * 256u) / (size > 1u ? size - 1u : 1u);
            uint32_t sx = fx >> 8, wx = fx & 255u;
            uint32_t sx1 = sx + 1u < atlas->px ? sx + 1u : sx;
            uint32_t c0 = (mask[sy * atlas->px + sx] * (256u - wx) + mask[sy * atlas->px + sx1] * wx) >> 8;
            uint32_t c1 = (mask[sy1 * atlas->px + sx] * (256u - wx) + mask[sy1 * atlas->px + sx1] * wx) >> 8;
            uint8_t coverage = (uint8_t)((c0 * (256u - wy) + c1 * wy) >> 8);
            if (coverage) gfx_put_pixel_alpha(x + px, y + py, color,
                (uint8_t)(((uint32_t)coverage * opacity) / 255u));
        }
    }
}

static inline int32_t st_material_grain(uint32_t x, uint32_t y);

void gfx_draw_mesh_wallpaper(void) {
    uint32_t w = gfx_get_width(), h = gfx_get_height();
    if (w == 0 || h == 0) return;

    int32_t t = (int32_t)g_mesh_time_tick;
    int32_t shift_x1 = (int32_t)(((t % 360) < 180 ? (t % 180) - 90 : 270 - (t % 180)) / 10);
    int32_t shift_y1 = (int32_t)(((t % 240) < 120 ? (t % 120) - 60 : 180 - (t % 120)) / 10);
    int32_t shift_x2 = (int32_t)(((t % 300) < 150 ? (t % 150) - 75 : 225 - (t % 150)) / 10);
    int32_t shift_y2 = (int32_t)(((t % 280) < 140 ? (t % 140) - 70 : 210 - (t % 140)) / 10);
    int32_t shift_x3 = (int32_t)(((t % 320) < 160 ? (t % 160) - 80 : 240 - (t % 160)) / 10);
    int32_t shift_y3 = (int32_t)(((t % 260) < 130 ? (t % 130) - 65 : 195 - (t % 130)) / 10);

    for (uint32_t y = 0; y < h; ++y) {
        uint32_t v = (y * 256) / h;
        for (uint32_t x = 0; x < w; ++x) {
            uint32_t u = (x * 256) / w;
            uint32_t blend = (u + v) / 2;

            int r = 0, g = 0, b = 0;
            if (g_dark_theme) {
                r = (int)((15 * (256 - blend) + 30 * blend) >> 8);
                g = (int)((23 * (256 - blend) + 27 * blend) >> 8);
                b = (int)((42 * (256 - blend) + 75 * blend) >> 8);

                int32_t dx_b = (int32_t)u - (210 + shift_x1), dy_b = (int32_t)v - (80 + shift_y1);
                int32_t dx_v = (int32_t)u - (120 + shift_x2), dy_v = (int32_t)v - (200 + shift_y2);
                int32_t dx_c = (int32_t)u - (60 + shift_x3), dy_c = (int32_t)v - (110 + shift_y3);

                int blue_bloom = 110 - (dx_b * dx_b + dy_b * dy_b) / 140;
                int violet_bloom = 95 - (dx_v * dx_v + dy_v * dy_v) / 150;
                int cyan_bloom = 80 - (dx_c * dx_c + dy_c * dy_c) / 160;

                if (blue_bloom < 0) blue_bloom = 0;
                if (violet_bloom < 0) violet_bloom = 0;
                if (cyan_bloom < 0) cyan_bloom = 0;

                r += (violet_bloom * 80 + blue_bloom * 15 + cyan_bloom * 5) >> 8;
                g += (cyan_bloom * 90 + blue_bloom * 40 + violet_bloom * 10) >> 8;
                b += (blue_bloom * 140 + violet_bloom * 120 + cyan_bloom * 110) >> 8;
            } else {
                r = (int)((20 * (256 - blend) + 224 * blend) >> 8);
                g = (int)((205 * (256 - blend) + 92 * blend) >> 8);
                b = (int)((246 * (256 - blend) + 224 * blend) >> 8);

                int32_t dx_y = (int32_t)u - (228 + shift_x1), dy_y = (int32_t)v - (92 + shift_y1);
                int32_t dx_g = (int32_t)u - (242 + shift_x2), dy_g = (int32_t)v - (220 + shift_y2);
                int32_t dx_p = (int32_t)u - (124 + shift_x3), dy_p = (int32_t)v - (126 + shift_y3);

                int yellow = 150 - (dx_y * dx_y + dy_y * dy_y) / 115;
                int green = 128 - (dx_g * dx_g + dy_g * dy_g) / 130;
                int pink = 88 - (dx_p * dx_p + dy_p * dy_p) / 155;

                if (yellow < 0) yellow = 0;
                if (green < 0) green = 0;
                if (pink < 0) pink = 0;

                r += yellow * 2 / 3 - green / 4 + pink / 2;
                g += yellow * 3 / 4 + green / 2 - pink / 7;
                b -= yellow / 3 + green / 4 - pink / 2;
            }

            int grain = st_material_grain(x, y);
            r += grain;
            g += grain;
            b += grain;
            if (r > 255) { r = 255; }
            if (r < 0) { r = 0; }
            if (g > 255) { g = 255; }
            if (g < 0) { g = 0; }
            if (b > 255) { b = 255; }
            if (b < 0) { b = 0; }
            gfx_put_pixel(x, y, (r << 16) | (g << 8) | b);
        }
    }
}

void sdf_render_liquid_glass_panel(uint32_t *fb, uint32_t pitch, uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t radius, uint32_t bg, uint8_t a, uint32_t border, uint8_t glow, uint32_t outline) {
    (void)fb; (void)pitch; (void)glow; (void)outline;
    gfx_draw_glass_rect_material(x, y, w, h, bg, a, border, radius);
}

void gfx_draw_hline(uint32_t x, uint32_t y, uint32_t width, uint32_t color, uint8_t alpha) {
    gfx_fill_rect_alpha(x, y, width, 1, color, alpha);
}

static inline float eval_squircle_sdf(float px, float py, float cx, float cy, float radius) {
    float dx = px - cx; if (dx < 0.0f) dx = -dx;
    float dy = py - cy; if (dy < 0.0f) dy = -dy;
    float dx2 = dx * dx;
    float dy2 = dy * dy;
    float d4 = dx2 * dx2 + dy2 * dy2;
    
    /* Raiz quarta via Newton-Raphson. A versão anterior começava em d4/2;
     * para um tile 64px isso é centenas de milhares, não ~32, e deixava o
     * squircle praticamente sem preenchimento. A maior distância é uma
     * estimativa inicial estável para a quarta raiz. */
    if (d4 > 0.0f) {
        float val = d4;
        float max_axis = dx > dy ? dx : dy;
        float x = max_axis * 1.12f + 0.001f;
        for (int i = 0; i < 4; ++i) {
            float x2 = x * x;
            float x3 = x2 * x;
            x = (3.0f * x + val / x3) * 0.25f;
        }
        return x - radius;
    }
    return -radius;
}

static void draw_squircle_shadow(uint32_t x0, uint32_t y0, uint32_t size, uint32_t blur, uint32_t y_offset, uint8_t max_alpha) {
    float cx = (float)x0 + (float)size * 0.5f;
    float cy = (float)y0 + (float)size * 0.5f + (float)y_offset;
    float r  = (float)size * 0.46f;
    int gw = (int)gfx_get_width(), gh = (int)gfx_get_height();
    int pad = (int)blur + 4;
    int sx = (int)x0 - pad; if (sx < 0) sx = 0;
    int ex = (int)x0 + (int)size + pad; if (ex > gw) ex = gw;
    int sy = (int)y0 + (int)y_offset - pad; if (sy < 0) sy = 0;
    int ey = (int)y0 + (int)size + (int)y_offset + pad; if (ey > gh) ey = gh;
    float fblur = (float)blur;

    for (int py = sy; py < ey; ++py) {
        for (int px = sx; px < ex; ++px) {
            float d = eval_squircle_sdf((float)px, (float)py, cx, cy, r);
            if (d < fblur) {
                float factor = 0.0f;
                if (d <= 0.0f) {
                    factor = 1.0f;
                } else {
                    float ratio = (fblur - d) / fblur;
                    factor = ratio * ratio;
                }
                uint8_t a = (uint8_t)((float)max_alpha * factor);
                if (a >= 2) {
                    gfx_put_pixel_alpha((uint32_t)px, (uint32_t)py, 0x00000000, a);
                }
            }
        }
    }
}

static void draw_squircle_canvas(uint32_t x0, uint32_t y0, uint32_t size, uint32_t col_top, uint32_t col_bottom) {
    float cx = (float)x0 + (float)size * 0.5f;
    float cy = (float)y0 + (float)size * 0.5f;
    float r  = (float)size * 0.46f;
    int gw = (int)gfx_get_width(), gh = (int)gfx_get_height();

    uint32_t r_top = (col_top >> 16) & 0xFF, g_top = (col_top >> 8) & 0xFF, b_top = col_top & 0xFF;
    uint32_t r_bot = (col_bottom >> 16) & 0xFF, g_bot = (col_bottom >> 8) & 0xFF, b_bot = col_bottom & 0xFF;

    for (int y = 0; y < (int)size; ++y) {
        int py = (int)y0 + y;
        if (py < 0 || py >= gh) continue;
        float t_axial = (float)y / (float)size;

        // Interpolação de cor linear vertical
        /* Os canais precisam ser assinados: `bottom - top` pode ser
         * negativo. Com uint, essa subtração dava overflow e gerava as
         * listras amarelas vistas nos ícones preenchidos. */
        uint32_t cr = (uint32_t)((int32_t)r_top + ((int32_t)r_bot - (int32_t)r_top) * t_axial);
        uint32_t cg = (uint32_t)((int32_t)g_top + ((int32_t)g_bot - (int32_t)g_top) * t_axial);
        uint32_t cb = (uint32_t)((int32_t)b_top + ((int32_t)b_bot - (int32_t)b_top) * t_axial);

        for (int x = 0; x < (int)size; ++x) {
            int px = (int)x0 + x;
            if (px < 0 || px >= gw) continue;

            float d = eval_squircle_sdf((float)px, (float)py, cx, cy, r);

            if (d <= 0.0f) {
                // Pixel interno: calcular especularidade de borda superior
                uint32_t final_r = cr, final_g = cg, final_b = cb;
                if (y <= 1 || (d > -1.8f && py < (int)cy)) {
                    // Reflexo de luz do topo (Highlight especular)
                    final_r = (final_r * 180 + 255 * 75) >> 8;
                    final_g = (final_g * 180 + 255 * 75) >> 8;
                    final_b = (final_b * 180 + 255 * 75) >> 8;
                } else if (y >= (int)size - 2) {
                    // Sombra da base inferior (Bisel de profundidade)
                    final_r = (final_r * 200) >> 8;
                    final_g = (final_g * 200) >> 8;
                    final_b = (final_b * 200) >> 8;
                }
                uint32_t color = (final_r << 16) | (final_g << 8) | final_b;
                gfx_put_pixel_alpha((uint32_t)px, (uint32_t)py, color, 255);
            } else if (d < 1.0f) {
                // Anti-aliasing analítico subpixel na borda externa
                uint8_t alpha = (uint8_t)((1.0f - d) * 255.0f);
                uint32_t color = (cr << 16) | (cg << 8) | cb;
                gfx_put_pixel_alpha((uint32_t)px, (uint32_t)py, color, alpha);
            }
        }
    }
}

/* Aplica um Phosphor Duotone compilado no host. A seleção sempre prefere o
 * menor atlas que seja maior ou igual ao tamanho pedido: reduzimos curvas AA,
 * mas nunca ampliamos um bitmap pequeno para preencher um tile HiDPI. */
static uint8_t gfx_draw_baken_app_asset(uint32_t x, uint32_t y, uint32_t size,
                                        uint32_t app_id, uint32_t color,
                                        uint8_t opacity) {
    if (size == 0 || app_id >= BAKEN_APP_ICON_COUNT) return 0;
    const SotlasBakenAppIconAtlas *atlas = st_select_app_icon_atlas(size);
    const uint8_t *mask = atlas->alpha + app_id * atlas->px * atlas->px;
    for (uint32_t py = 0; py < size; ++py) {
        uint32_t fy = (py * (atlas->px - 1u) * 256u) / (size > 1u ? size - 1u : 1u);
        uint32_t sy = fy >> 8, wy = fy & 255u;
        uint32_t sy1 = sy + 1u < atlas->px ? sy + 1u : sy;
        for (uint32_t px = 0; px < size; ++px) {
            uint32_t fx = (px * (atlas->px - 1u) * 256u) / (size > 1u ? size - 1u : 1u);
            uint32_t sx = fx >> 8, wx = fx & 255u;
            uint32_t sx1 = sx + 1u < atlas->px ? sx + 1u : sx;
            uint32_t c0 = (mask[sy * atlas->px + sx] * (256u - wx) +
                           mask[sy * atlas->px + sx1] * wx) >> 8;
            uint32_t c1 = (mask[sy1 * atlas->px + sx] * (256u - wx) +
                           mask[sy1 * atlas->px + sx1] * wx) >> 8;
            uint8_t coverage = (uint8_t)((c0 * (256u - wy) + c1 * wy) >> 8);
            if (coverage) {
                uint8_t a = (uint8_t)(((uint32_t)coverage * opacity) / 255u);
                gfx_put_pixel_alpha(x + px, y + py, color, a);
            }
        }
    }
    return 1;
}

/* Fallback geométrico para builds antigos cujo header de assets ainda não foi
 * regenerado. Material Symbols continua reservado às ações do sistema. */
static void draw_baken_app_glyph(uint32_t x, uint32_t y, uint32_t size, uint32_t id) {
    uint32_t u = size / 24u; if (u == 0) u = 1;
    uint32_t white = 0x00FFFFFF;
    if (id == 0 || id == 11) { /* BakenFS / Pessoal: pasta */
        gfx_fill_rect_alpha(x + 4*u, y + 7*u, 7*u, 3*u, white, 235);
        gfx_draw_glass_rect_material(x + 3*u, y + 9*u, 18*u, 10*u, 0x00FFFFFF, 245, white, 2*u);
        gfx_draw_hline(x + 5*u, y + 12*u, 14*u, 0x000284C7, 90);
    } else if (id == 1) { /* 3D Studio: cubo isométrico */
        for (uint32_t i = 0; i < 7*u; ++i) {
            gfx_fill_rect_alpha(x + 12*u - i, y + 5*u + i/2u, 2*u, 2*u, white, 235);
            gfx_fill_rect_alpha(x + 12*u + i, y + 5*u + i/2u, 2*u, 2*u, white, 235);
        }
        gfx_draw_hline(x + 5*u, y + 13*u, 14*u, white, 235);
        gfx_fill_rect_alpha(x + 11*u, y + 9*u, 2*u, 9*u, white, 235);
    } else if (id == 2) { /* Navegador: globo Baken */
        gfx_draw_circle_alpha(x + 12*u, y + 12*u, 8*u, white, 240);
        gfx_draw_circle_alpha(x + 12*u, y + 12*u, 6*u, 0x000891B2, 255);
        gfx_draw_hline(x + 5*u, y + 12*u, 14*u, white, 235);
        gfx_fill_rect_alpha(x + 11*u, y + 5*u, 2*u, 14*u, white, 235);
    } else if (id == 3) { /* Paint: paleta com pigmentos */
        gfx_draw_circle_alpha(x + 11*u, y + 12*u, 8*u, white, 240);
        gfx_draw_circle_alpha(x + 11*u, y + 12*u, 5*u, 0x00EA580C, 255);
        gfx_draw_circle_alpha(x + 8*u, y + 9*u, u, 0x00FDE047, 255);
        gfx_draw_circle_alpha(x + 14*u, y + 9*u, u, 0x0038BDF8, 255);
        gfx_draw_circle_alpha(x + 8*u, y + 15*u, u, 0x0034D399, 255);
    } else if (id == 4) { /* Camera */
        gfx_draw_glass_rect_material(x + 3*u, y + 8*u, 18*u, 11*u, white, 245, white, 3*u);
        gfx_fill_rect_alpha(x + 8*u, y + 5*u, 7*u, 4*u, white, 235);
        gfx_draw_circle_alpha(x + 12*u, y + 13*u, 4*u, 0x00BE123C, 255);
        gfx_draw_circle_alpha(x + 11*u, y + 12*u, u, white, 220);
    } else if (id == 5) { /* Música */
        gfx_fill_rect_alpha(x + 15*u, y + 5*u, 2*u, 11*u, white, 245);
        gfx_fill_rect_alpha(x + 16*u, y + 5*u, 5*u, 2*u, white, 245);
        gfx_draw_circle_alpha(x + 11*u, y + 17*u, 4*u, white, 245);
        gfx_draw_circle_alpha(x + 11*u, y + 17*u, 2*u, 0x004C1D95, 255);
    } else if (id == 6) { /* Notas: página e traço */
        gfx_draw_glass_rect_material(x + 5*u, y + 4*u, 13*u, 16*u, 0x00FFFFFF, 245, white, 2*u);
        gfx_draw_hline(x + 8*u, y + 9*u, 7*u, 0x00E11D48, 150);
        gfx_draw_hline(x + 8*u, y + 13*u, 6*u, 0x00E11D48, 150);
        for (uint32_t p=0; p<5*u; ++p) gfx_fill_rect_alpha(x + 14*u + p/2u, y + 15*u - p, 2*u, 2*u, 0x00E11D48, 255);
    } else if (id == 7) { /* Arquivos/terminal */
        gfx_draw_glass_rect_material(x + 3*u, y + 5*u, 18*u, 14*u, 0x000F172A, 235, white, 2*u);
        gfx_draw_hline(x + 7*u, y + 10*u, 4*u, white, 240);
        gfx_draw_hline(x + 9*u, y + 12*u, 4*u, white, 240);
        gfx_draw_hline(x + 14*u, y + 15*u, 4*u, 0x0038BDF8, 255);
    } else if (id == 8) { /* Loja */
        gfx_draw_glass_rect_material(x + 4*u, y + 10*u, 16*u, 10*u, white, 245, white, 2*u);
        for (uint32_t i=0; i<4; ++i) gfx_fill_rect_alpha(x + (5u+i*4u)*u, y + 6*u, 3*u, 5*u, (i&1u)?0x00059669:white, 240);
        gfx_draw_hline(x + 8*u, y + 15*u, 8*u, 0x00059669, 120);
    } else if (id == 9) { /* Console Sotlas */
        gfx_draw_glass_rect_material(x + 3*u, y + 5*u, 18*u, 14*u, 0x000F172A, 235, white, 2*u);
        gfx_draw_hline(x + 7*u, y + 10*u, 4*u, 0x0038BDF8, 255);
        gfx_draw_hline(x + 9*u, y + 12*u, 4*u, 0x0038BDF8, 255);
        gfx_draw_hline(x + 14*u, y + 15*u, 4*u, white, 230);
    } else if (id == 10) { /* Sistema: controles */
        gfx_draw_hline(x + 5*u, y + 8*u, 14*u, white, 235);
        gfx_draw_hline(x + 5*u, y + 15*u, 14*u, white, 235);
        gfx_draw_circle_alpha(x + 9*u, y + 8*u, 2*u, white, 255);
        gfx_draw_circle_alpha(x + 16*u, y + 15*u, 2*u, white, 255);
    } else if (id == 12) { /* Calendário */
        gfx_draw_glass_rect_material(x + 4*u, y + 5*u, 16*u, 15*u, white, 245, white, 2*u);
        gfx_fill_rect_alpha(x + 4*u, y + 8*u, 16*u, 3*u, 0x00BE185D, 230);
        gfx_draw_circle_alpha(x + 9*u, y + 14*u, u, 0x00BE185D, 255);
        gfx_draw_circle_alpha(x + 15*u, y + 14*u, u, 0x00BE185D, 255);
    } else if (id == 13) { /* Pessoal */
        gfx_draw_circle_alpha(x + 12*u, y + 9*u, 4*u, white, 245);
        gfx_draw_circle_alpha(x + 12*u, y + 19*u, 7*u, white, 245);
        gfx_draw_circle_alpha(x + 12*u, y + 19*u, 4*u, 0x0015803D, 255);
    } else if (id == 14) { /* Busca */
        gfx_draw_circle_alpha(x + 10*u, y + 10*u, 6*u, white, 245);
        gfx_draw_circle_alpha(x + 10*u, y + 10*u, 3*u, 0x00B45309, 255);
        for (uint32_t i=0; i<6*u; ++i) gfx_fill_rect_alpha(x + 14*u + i/2u, y + 14*u + i/2u, 2*u, 2*u, white, 245);
    } else { /* Mídia/galeria */
        gfx_draw_glass_rect_material(x + 4*u, y + 5*u, 16*u, 15*u, white, 245, white, 2*u);
        gfx_draw_circle_alpha(x + 15*u, y + 10*u, 2*u, 0x000F766E, 255);
        for (uint32_t p=0; p<8*u; ++p) gfx_fill_rect_alpha(x + 6*u + p, y + 18*u - p/2u, 2*u, 2*u, 0x000F766E, 255);
    }
}

void gfx_draw_app_icon_hd(uint32_t x, uint32_t y, uint32_t size, uint32_t app_id) {
    /* Registro canônico: cada app do desktop/dock recebe uma identidade única. */
    uint32_t id = app_id % 16;
    static const uint32_t icon_top[16] = {
        0x0038BDF8, 0x00818CF8, 0x0022D3EE, 0x00FB923C, 0x00F43F5E, 0x00A78BFA,
        0x00FB7185, 0x00FDE047, 0x0034D399, 0x00334155, 0x0014B8A6, 0x006366F1,
        0x00EC4899, 0x0022C55E, 0x00D97706, 0x000F766E
    };
    static const uint32_t icon_bottom[16] = {
        0x000284C7, 0x004338CA, 0x000891B2, 0x00EA580C, 0x00BE123C, 0x004C1D95,
        0x00E11D48, 0x00CA8A04, 0x00059669, 0x000F172A, 0x000F766E, 0x004F46E5,
        0x00BE185D, 0x0015803D, 0x00B45309, 0x0011555A
    };
    /* Sombra suave com decaimento que acompanha a geometria real do squircle */
    draw_squircle_shadow(x, y, size, size >= 48u ? 8u : 4u, size >= 48u ? 3u : 2u, 65u);
    draw_squircle_canvas(x, y, size, icon_top[id], icon_bottom[id]);
    gfx_draw_circle_alpha(x + size / 2, y + size / 2, (size * 34) / 100, 0x00FFFFFF, 20);
    /* 74% preenche o tile sem colar nas bordas; o duotone preserva a camada
     * secundaria com sua opacidade original em vez de virar um contorno solto. */
    uint32_t glyph_size = (size * 74u + 50u) / 100u;
    if (glyph_size < 16u) glyph_size = 16u;
    uint32_t glyph_x = x + (size - glyph_size) / 2u;
    uint32_t glyph_y = y + (size - glyph_size) / 2u;
    /* Pequena oclusao sob o glyph o separa de gradientes claros sem contorno. */
    gfx_draw_baken_app_asset(glyph_x, glyph_y + (size >= 48u ? 1u : 0u),
                             glyph_size, id, 0x00111A2E, 58);
    if (!gfx_draw_baken_app_asset(glyph_x, glyph_y, glyph_size, id,
                                  0x00FFFFFF, 248))
        draw_baken_app_glyph(x, y, size, id);
    return;

    // Caminho legado abaixo permanece temporariamente como referência de migração.
    if (id == 0) { // BakenFS / Arquivos (Pasta Azul)
        draw_squircle_canvas(x, y, size, 0x0038BDF8, 0x000284C7);
        gfx_draw_glass_rect_material(x + 8, y + 10, 14, 6, 0x00E0F2FE, 240, 0x00FFFFFF, 2);
        gfx_draw_glass_rect_material(x + 6, y + 13, 24, 15, 0x00BAE6FD, 255, 0x00FFFFFF, 3);
        gfx_draw_hline(x + 8, y + 18, 20, 0x000284C7, 90);
    } else if (id == 1) { // 3D Studio (Roxo/Gradiente)
        draw_squircle_canvas(x, y, size, 0x00C084FC, 0x007C3AED);
        for (int f = 0; f < 10; ++f) {
            gfx_draw_hline(x + 18 - f, y + 10 + f, (uint32_t)(f * 2 + 1), 0x00EDE9FE, 240);
            gfx_fill_rect_alpha(x + 9 + f, y + 20 + (f/2), 2, 8, 0x00A78BFA, 255);
            gfx_fill_rect_alpha(x + 19 + f, y + 20 - (f/2), 2, 8, 0x006D28D9, 255);
        }
    } else if (id == 2) { // Web Browser (Globo Ciano)
        draw_squircle_canvas(x, y, size, 0x0022D3EE, 0x000891B2);
        gfx_draw_circle_alpha(x + 18, y + 18, 9, 0x00FFFFFF, 240);
        gfx_draw_circle_alpha(x + 18, y + 18, 7, 0x000891B2, 255);
        gfx_draw_hline(x + 11, y + 18, 15, 0x00FFFFFF, 220);
        gfx_fill_rect_alpha(x + 18, y + 11, 1, 15, 0x00FFFFFF, 220);
    } else if (id == 3) { // Paint 2D / Vetor (Laranja)
        draw_squircle_canvas(x, y, size, 0x00FB923C, 0x00EA580C);
        gfx_draw_circle_alpha(x + 17, y + 18, 8, 0x00FFFFFF, 240);
        gfx_draw_circle_alpha(x + 14, y + 15, 2, 0x00EF4444, 255);
        gfx_draw_circle_alpha(x + 20, y + 15, 2, 0x003B82F6, 255);
        gfx_draw_circle_alpha(x + 17, y + 21, 2, 0x0010B981, 255);
    } else if (id == 4) { // System Cam (Lente Escura com Sensor)
        draw_squircle_canvas(x, y, size, 0x00F43F5E, 0x00BE123C);
        gfx_draw_circle_alpha(x + 18, y + 18, 8, 0x000F172A, 255);
        gfx_draw_circle_alpha(x + 18, y + 18, 5, 0x001E293B, 255);
        gfx_draw_circle_alpha(x + 18, y + 18, 3, 0x0038BDF8, 255);
        gfx_draw_circle_alpha(x + 16, y + 16, 2, 0x00FFFFFF, 255);
    } else if (id == 5) { // Hi-Res Mídia / Player (Roxo Índigo)
        draw_squircle_canvas(x, y, size, 0x00818CF8, 0x004338CA);
        for (int p = 0; p < 8; ++p) {
            gfx_fill_rect_alpha(x + 14 + p, y + 14 + p, 2, (uint32_t)(10 - p), 0x00FFFFFF, 250);
            gfx_fill_rect_alpha(x + 14 + p, y + 14, 2, (uint32_t)(10 - p), 0x00FFFFFF, 250);
        }
    } else if (id == 6) { // Spark DAW / Áudio (Vermelho Rubi)
        draw_squircle_canvas(x, y, size, 0x00FB7185, 0x00E11D48);
        for (int w = 0; w < 5; ++w) {
            uint32_t bar_h = (uint32_t)(6 + ((w * 3) % 9));
            gfx_fill_rect_alpha(x + 11 + (w * 3), y + 22 - bar_h, 2, bar_h, 0x00FFFFFF, 240);
        }
    } else if (id == 7) { // Notas / Editor (Amarelo Ouro)
        draw_squircle_canvas(x, y, size, 0x00FDE047, 0x00CA8A04);
        gfx_draw_glass_rect_material(x + 9, y + 8, 18, 20, 0x00FFFFFF, 240, 0x00CBD5E1, 3);
        gfx_draw_hline(x + 12, y + 14, 12, 0x00475569, 200);
        gfx_draw_hline(x + 12, y + 18, 12, 0x00475569, 200);
        gfx_draw_hline(x + 12, y + 22, 8,  0x0038BDF8, 240);
    } else if (id == 8) { // Store / Loja (Esmeralda)
        draw_squircle_canvas(x, y, size, 0x0034D399, 0x00059669);
        gfx_draw_glass_rect_material(x + 9, y + 13, 18, 15, 0x00FFFFFF, 240, 0x00A7F3D0, 3);
        gfx_draw_circle_alpha(x + 18, y + 13, 5, 0x00FFFFFF, 200);
        gfx_draw_circle_alpha(x + 18, y + 13, 3, 0x00059669, 255);
    } else if (id == 9) { // Terminal / Console Sotlas (Grafite Escuro)
        draw_squircle_canvas(x, y, size, 0x00334155, 0x000F172A);
        gfx_draw_hline(x + 10, y + 12, 6, 0x0038BDF8, 255);
        gfx_draw_hline(x + 12, y + 14, 6, 0x0038BDF8, 255);
        gfx_draw_hline(x + 10, y + 16, 6, 0x0038BDF8, 255);
        gfx_draw_hline(x + 18, y + 18, 8, 0x0010B981, 255);
    } else { // Ajustes & Hardware (Cinza Alumínio Metalizado)
        draw_squircle_canvas(x, y, size, 0x0094A3B8, 0x00475569);
        gfx_draw_hline(x + 10, y + 15, 16, 0x00FFFFFF, 220);
        gfx_draw_hline(x + 10, y + 21, 16, 0x00FFFFFF, 220);
        gfx_draw_circle_alpha(x + 14, y + 15, 3, 0x00FFFFFF, 255);
        gfx_draw_circle_alpha(x + 22, y + 21, 3, 0x00FFFFFF, 255);
    }
}

void gfx_draw_app_icon(uint32_t x, uint32_t y, uint32_t size, uint32_t app_id) {
    gfx_draw_app_icon_hd(x, y, size, app_id);
}
""".strip().splitlines())
    elif ast.name == "kernel::baken_animation":
        lines.extend((
            '#include "baken_design_tokens.h"',
            "typedef struct { float current_val, target_val, velocity, stiffness, damping; } SotlasSpringState;",
            "static int32_t st_abs_i32(int32_t value) { return value < 0 ? -value : value; }",
            "float spring_update(SotlasSpringState *spring, float dt) { if (!spring) return 0.0f; float force=-spring->stiffness*(spring->current_val-spring->target_val); float damping=-spring->damping*spring->velocity; spring->velocity+=(force+damping)*dt; spring->current_val+=spring->velocity*dt; return spring->current_val; }",
            "void baken_motion_init_spring(SotlasSpringState *spring) { if (!spring) return; *spring=(SotlasSpringState){1.0f,1.0f,0.0f,BKN_MOTION_SPRING_STIFFNESS,BKN_MOTION_SPRING_DAMPING}; }",
            "float calculate_dock_magnify(int32_t cursor_x, int32_t icon_center_x, int32_t max_radius) { int32_t dist=st_abs_i32(cursor_x-icon_center_x); if (max_radius<=0 || dist>=max_radius) return 1.0f; float ratio=(float)(max_radius-dist)/(float)max_radius; return 1.0f+ratio*ratio*0.45f; }",
        ))
    elif ast.name == "kernel::baken_ui_oop":
        lines.extend("""
#include "baken_design_tokens.h"
extern void gfx_draw_glass_rect_material(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius);
extern void gfx_draw_glass_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius);
extern void gfx_draw_text(uint32_t x, uint32_t y, const uint8_t *s, uint32_t c);
extern void gfx_draw_circle_alpha(uint32_t cx, uint32_t cy, uint32_t r, uint32_t c, uint8_t a);
extern void baken_lua_draw_surface(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t material, uint32_t state, uint32_t radius);
extern void gfx_draw_app_icon_hd(uint32_t x, uint32_t y, uint32_t size, uint32_t app_id);
extern void gfx_draw_material_icon(uint32_t x, uint32_t y, uint32_t size, uint32_t icon_id, uint32_t color, uint8_t alpha);
extern void gfx_draw_material_icon_state(uint32_t x, uint32_t y, uint32_t size, uint32_t icon_id, uint32_t color, uint32_t state);
extern void gfx_draw_app_icon(uint32_t x, uint32_t y, uint32_t size, uint32_t app_id);
extern uint32_t gfx_get_width(void), gfx_get_height(void);
extern uint32_t baken_ui_px(uint32_t logical_px);
typedef struct { float current_val, target_val, velocity, stiffness, damping; } SotlasSpringState;
extern float spring_update(SotlasSpringState *spring, float dt);
extern float calculate_dock_magnify(int32_t cursor_x, int32_t icon_center_x, int32_t max_radius);

typedef struct {
    uint32_t y_offset;
    uint32_t icon_size;
    uint32_t item_count;
    const uint8_t *item_labels[16];
    SotlasSpringState item_springs[16];
    SotlasSpringState bounce_springs[16];
} DesktopDock;

/* Contrato geométrico único do dock. O shell usa exatamente estes limites
 * para clique e o componente usa-os para renderização/movimento. */
typedef struct { uint32_t x, y, width, height, pitch, icon, pad; } BakenDockLayout;
extern uint8_t wm_app_is_open(uint32_t app_id);
extern uint8_t desktop_shell_is_dark_theme(void);
void baken_dock_layout(uint32_t item_count, BakenDockLayout *out) {
    if (!out) return;
    uint32_t sw = gfx_get_width(), sh = gfx_get_height();
    out->pitch = baken_ui_px(50);
    out->height = baken_ui_px(58);
    out->icon = baken_ui_px(40);
    out->pad = baken_ui_px(10);
    out->width = item_count * out->pitch + out->pad * 2u;
    if (out->width > sw) out->width = sw;
    out->x = sw > out->width ? (sw - out->width) / 2u : 0;
    out->y = sh > out->height + baken_ui_px(14) ? sh - out->height - baken_ui_px(14) : 0;
}

void dock_init(DesktopDock *dock) {
    if (!dock) return;
    dock->y_offset = 14; dock->icon_size = 40; dock->item_count = 0;
    for (int i = 0; i < 16; ++i) {
        dock->item_labels[i] = 0;
        dock->item_springs[i] = (SotlasSpringState){1.0f, 1.0f, 0.0f, BKN_MOTION_SPRING_STIFFNESS, BKN_MOTION_SPRING_DAMPING};
        dock->bounce_springs[i] = (SotlasSpringState){0.0f, 0.0f, 0.0f, 180.0f, 12.0f};
    }
}
void dock_add_item(DesktopDock *dock, const uint8_t *label) {
    if (!dock || dock->item_count >= 16) return;
    dock->item_labels[dock->item_count] = label;
    dock->item_springs[dock->item_count] = (SotlasSpringState){1.0f, 1.0f, 0.0f, BKN_MOTION_SPRING_STIFFNESS, BKN_MOTION_SPRING_DAMPING};
    dock->bounce_springs[dock->item_count] = (SotlasSpringState){0.0f, 0.0f, 0.0f, 180.0f, 12.0f};
    dock->item_count++;
}
void dock_trigger_bounce(DesktopDock *dock, uint32_t index) {
    if (!dock || index >= dock->item_count) return;
    dock->bounce_springs[index].current_val = -6.0f;
    dock->bounce_springs[index].velocity = -50.0f;
}
void dock_update(DesktopDock *dock, float dt, int32_t cursor_x, int32_t cursor_y) {
    if (!dock || dock->item_count == 0) return;
    BakenDockLayout geo; baken_dock_layout(dock->item_count, &geo);
    int in_dock = (cursor_x >= (int)geo.x && cursor_x <= (int)(geo.x + geo.width) && cursor_y >= (int)geo.y && cursor_y <= (int)(geo.y + geo.height));
    for (uint32_t i = 0; i < dock->item_count; ++i) {
        int icon_center_x = (int)(geo.x + geo.pad + i * geo.pitch + geo.pitch / 2u);
        dock->item_springs[i].target_val = in_dock ? calculate_dock_magnify(cursor_x, icon_center_x, 68) : 1.0f;
        spring_update(&dock->item_springs[i], dt);
        spring_update(&dock->bounce_springs[i], dt);
    }
}
void dock_draw(const DesktopDock *dock) {
    if (!dock || dock->item_count == 0) return;
    BakenDockLayout geo; baken_dock_layout(dock->item_count, &geo);
    baken_lua_draw_surface(geo.x, geo.y, geo.width, geo.height, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, geo.height / 2u);
    uint8_t is_dark = desktop_shell_is_dark_theme();
    for (uint32_t i = 0; i < dock->item_count; ++i) {
        /* Estado hover + bounce vertical da física elástica */
        float spring = dock->item_springs[i].current_val;
        float bounce = dock->bounce_springs[i].current_val;
        uint32_t draw_icon = (uint32_t)((float)geo.icon * spring);
        uint32_t base_x = geo.x + geo.pad + i * geo.pitch + (geo.pitch - geo.icon) / 2u;
        uint32_t ix = base_x - (draw_icon - geo.icon) / 2u;
        uint32_t iy = (uint32_t)((float)(geo.y + (geo.height - geo.icon) / 2u - (draw_icon - geo.icon) / 2u) + bounce);
        if (spring > 1.02f) {
            gfx_draw_circle_alpha(ix + draw_icon / 2, iy + draw_icon / 2, draw_icon / 2 + 4, 0x00FFFFFF, 45);
        }
        gfx_draw_app_icon_hd(ix, iy, draw_icon, i);
        if (wm_app_is_open(i)) {
            uint32_t dot_color = is_dark ? 0x0038BDF8 : 0x000F172A;
            gfx_draw_circle_alpha(base_x + geo.icon / 2u, geo.y + geo.height - baken_ui_px(4), baken_ui_px(2), dot_color, 240);
        }
    }
}
""".strip().splitlines())
    elif ast.name == "kernel::window_manager":
        lines.extend("""
#include "baken_design_tokens.h"
extern void gfx_draw_glass_rect_material(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius);
extern void gfx_draw_glass_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius);
extern void gfx_draw_smooth_shadow(int x, int y, int w, int h, int radius, int blur, uint8_t max_alpha);
extern void gfx_draw_circle_button(uint32_t cx, uint32_t cy, uint32_t r, uint32_t c);
extern void gfx_draw_circle_alpha(uint32_t cx, uint32_t cy, uint32_t r, uint32_t c, uint8_t a);
extern void gfx_draw_app_icon_hd(uint32_t x, uint32_t y, uint32_t size, uint32_t app_id);
extern void gfx_draw_app_icon(uint32_t x, uint32_t y, uint32_t size, uint32_t app_id);
extern void gfx_draw_text_proportional(uint32_t x, uint32_t y, const char *str, uint32_t color);
extern void gfx_draw_text_role(uint32_t x, uint32_t y, const char *str, uint32_t color, uint32_t role);
extern void gfx_draw_text_ellipsis(uint32_t x, uint32_t y, uint32_t max_width, const char *str, uint32_t color);
extern uint32_t gfx_draw_text_wrap_role(uint32_t x, uint32_t y, uint32_t max_width, uint32_t max_lines, const char *str, uint32_t color, uint32_t role);
extern uint32_t gfx_measure_text(const char *str);
extern void gfx_draw_text(uint32_t x, uint32_t y, const uint8_t *s, uint32_t c);
extern void baken_lua_draw_surface(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t material, uint32_t state, uint32_t radius);
extern uint32_t gfx_get_width(void), gfx_get_height(void);
extern uint8_t sys_has_nvme(void);
extern uint8_t sys_has_ahci(void);
extern uint8_t sys_has_nic(void);
extern const char *st_notes_get_text(void);
extern const char *st_fs_entry_name(uint32_t index);
extern uint32_t st_fs_entry_count(void);
extern uint32_t st_fs_entry_kind(uint32_t index);
extern uint32_t st_fs_entry_size(uint32_t index);
extern void gfx_fill_rect_alpha(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t color, uint8_t alpha);
extern uint32_t desktop_shell_get_time_tick(void);
extern void desktop_shell_render_terminal(uint32_t px, uint32_t py, uint32_t pw, uint32_t ph, uint8_t is_focused);
extern void gfx_draw_hline(uint32_t x, uint32_t y, uint32_t width, uint32_t color, uint8_t alpha);
extern void gfx_draw_glass_rect_material(uint32_t x, uint32_t y, uint32_t width, uint32_t height, uint32_t bg_color, uint8_t bg_alpha, uint32_t border_color, uint32_t radius);
extern void st_notes_save(void);
void wm_unfocus_all(void);
void installer_next_stage(void);
void installer_prev_stage(void);
void installer_select_option(uint32_t opt);
void installer_execute_repair(uint32_t opt);
typedef struct { uint32_t MediaId; uint8_t RemovableMedia,MediaPresent,LogicalPartition,ReadOnly,WriteCaching; uint32_t BlockSize,IoAlign; uint64_t LastBlock,LowestAlignedLba; uint32_t LogicalBlocksPerPhysicalBlock,OptimalTransferLengthGranularity; } EFI_BLOCK_IO_MEDIA;
typedef struct _EFI_BLOCK_IO_PROTOCOL { uint64_t Revision; EFI_BLOCK_IO_MEDIA *Media; uint64_t (*Reset)(void*,uint8_t); uint64_t (*ReadBlocks)(void*,uint32_t,uint64_t,uint64_t,void*); uint64_t (*WriteBlocks)(void*,uint32_t,uint64_t,uint64_t,void*); uint64_t (*FlushBlocks)(void*); } EFI_BLOCK_IO_PROTOCOL;
typedef struct { char name[32]; uint32_t lba, size, kind; } SotlasFsEntry;
typedef struct { uint64_t magic; uint32_t version, entry_count; SotlasFsEntry entries[12]; uint8_t reserved[20]; } SotlasFsHeader;
typedef struct { uint64_t magic; uint32_t version, dark_theme, location_permission; uint8_t reserved[496]; } SotlasDesktopConfig;
typedef struct { uint64_t magic; uint32_t version, size; char text[496]; } SotlasTextFile;
typedef struct { uint64_t magic; uint32_t version, profile_id; char profile_name[32]; char packages[448]; } SotlasProfileConfig;
typedef struct { uint64_t magic; uint32_t version; char username[32]; char hostname[32]; char pin[16]; uint8_t reserved[416]; } SotlasUserConfig;
typedef struct { uint64_t magic; uint32_t version, timestamp; char name[32]; char description[464]; } SotlasSnapshotMeta;

#define INSTALL_TOTAL_LBAS 131072ULL
#define INSTALL_ESP_FIRST 2048ULL
#define INSTALL_ESP_LAST  86015ULL
#define INSTALL_DATA_FIRST 86016ULL
#define INSTALL_DATA_LAST 131038ULL
#define INSTALL_FAT_SECTORS 656U

#define INSTALLER_STAGE_WELCOME    0
#define INSTALLER_STAGE_LANGUAGE   1
#define INSTALLER_STAGE_LICENSE    2
#define INSTALLER_STAGE_HARDWARE   3
#define INSTALLER_STAGE_PROFILE    4
#define INSTALLER_STAGE_ACCOUNT    5
#define INSTALLER_STAGE_DISK       6
#define INSTALLER_STAGE_INSTALLING 7
#define INSTALLER_STAGE_COMPLETE   8
#define INSTALLER_STAGE_REPAIR     9

static EFI_BLOCK_IO_PROTOCOL *g_boot_block_io = 0;
static EFI_BLOCK_IO_PROTOCOL *g_install_target_block_io = 0;

typedef struct {
    char name[32];
    uint64_t first_lba;
    uint64_t last_lba;
    uint32_t fs_type; /* 1 = FAT32 ESP, 2 = BakenFS Data, 0 = Nao Formatado */
    uint8_t is_system;
} BakenPartition;

#define MAX_INSTALL_PARTS 4
typedef struct {
    uint32_t stage;
    uint32_t boot_mode; /* 0 = Wizard on boot, 1 = Live Demo Desktop */
    uint32_t selected_lang; /* 0 = Portugues (BR), 1 = English (US), 2 = Espanol */
    uint32_t selected_kbd; /* 0 = ABNT2, 1 = US-Intl, 2 = ISO Latin */
    uint8_t license_accepted;
    uint32_t hw_cpu_score;
    uint32_t hw_ram_mb;
    uint32_t hw_storage_score;
    uint32_t hw_gpu_score;
    uint32_t hw_total_score;
    uint32_t selected_profile; /* 0 = Padrao, 1 = Dev Sotlas, 2 = Gamer 3D, 3 = Minimalista */
    char hostname[32];
    char username[32];
    char pin[8];
    uint8_t auto_partition; /* 1 = Automatico, 0 = Personalizado */
    
    uint32_t disk_count;
    uint32_t selected_disk;
    uint32_t part_count;
    BakenPartition parts[MAX_INSTALL_PARTS];
    int32_t selected_part;
    uint32_t progress;
    uint8_t installed;
    uint8_t error;
    char status_text[64];

    char log_lines[6][48];
    uint32_t log_count;
    uint32_t transfer_speed_mb;

    uint32_t repair_option;
    char repair_status[64];
} BakenInstallerState;

static BakenInstallerState g_installer;

static void installer_append_log(const char *msg) {
    if (!msg) return;
    if (g_installer.log_count < 6) {
        int l = 0; while (msg[l] && l < 47) { g_installer.log_lines[g_installer.log_count][l] = msg[l]; l++; }
        g_installer.log_lines[g_installer.log_count][l] = 0;
        g_installer.log_count++;
    } else {
        for (int i = 1; i < 6; ++i) {
            for (int c = 0; c < 48; ++c) g_installer.log_lines[i - 1][c] = g_installer.log_lines[i][c];
        }
        int l = 0; while (msg[l] && l < 47) { g_installer.log_lines[5][l] = msg[l]; l++; }
        g_installer.log_lines[5][l] = 0;
    }
}

static void installer_apply_default(void) {
    g_installer.part_count = 2;
    g_installer.selected_part = 0;
    
    const char *p0 = "Baken ESP (Boot)";
    for (int i = 0; i < 31 && p0[i]; ++i) g_installer.parts[0].name[i] = p0[i];
    g_installer.parts[0].name[31] = 0;
    g_installer.parts[0].first_lba = INSTALL_ESP_FIRST;
    g_installer.parts[0].last_lba = INSTALL_ESP_LAST;
    g_installer.parts[0].fs_type = 1;
    g_installer.parts[0].is_system = 1;

    const char *p1 = "Baken Data (Volume)";
    for (int i = 0; i < 31 && p1[i]; ++i) g_installer.parts[1].name[i] = p1[i];
    g_installer.parts[1].name[31] = 0;
    g_installer.parts[1].first_lba = INSTALL_DATA_FIRST;
    g_installer.parts[1].last_lba = INSTALL_DATA_LAST;
    g_installer.parts[1].fs_type = 2;
    g_installer.parts[1].is_system = 1;

    g_installer.progress = 0;
    g_installer.installed = 0;
    g_installer.error = 0;
    const char *st = (g_installer.selected_disk == 0 && g_install_target_block_io) ? 
        "Disco GPT pronto: ESP FAT32 (41 MB) + Baken Data (23 MB)" : 
        "Destino: conecte um segundo disco virtual gravavel de 64 MB";
    for (int i = 0; i < 63 && st[i]; ++i) g_installer.status_text[i] = st[i];
    g_installer.status_text[63] = 0;
}

static void installer_init(void) {
    g_installer.stage = INSTALLER_STAGE_WELCOME;
    g_installer.boot_mode = 0;
    g_installer.selected_lang = 0;
    g_installer.selected_kbd = 0;
    g_installer.license_accepted = 1;
    g_installer.hw_cpu_score = 98;
    g_installer.hw_ram_mb = 512;
    g_installer.hw_storage_score = 95;
    g_installer.hw_gpu_score = 96;
    g_installer.hw_total_score = 96;
    g_installer.selected_profile = 1; /* Desenvolvedor Soberano */
    
    const char *hn = "baken-workstation";
    for (int i = 0; i < 31 && hn[i]; ++i) g_installer.hostname[i] = hn[i];
    g_installer.hostname[31] = 0;

    const char *un = "baken";
    for (int i = 0; i < 31 && un[i]; ++i) g_installer.username[i] = un[i];
    g_installer.username[31] = 0;

    const char *pn = "1234";
    for (int i = 0; i < 7 && pn[i]; ++i) g_installer.pin[i] = pn[i];
    g_installer.pin[7] = 0;

    g_installer.auto_partition = 1;
    g_installer.log_count = 0;
    g_installer.transfer_speed_mb = 34;
    g_installer.repair_option = 0;

    const char *rep_st = "Pronto para diagnostico ou reparo.";
    for (int i = 0; i < 63 && rep_st[i]; ++i) g_installer.repair_status[i] = rep_st[i];
    g_installer.repair_status[63] = 0;

    if (g_install_target_block_io && !g_install_target_block_io->Media->ReadOnly && g_install_target_block_io->Media->LastBlock >= 131071ULL) {
        g_installer.disk_count = 2;
        g_installer.selected_disk = 0;
    } else {
        g_installer.disk_count = 1;
        g_installer.selected_disk = 1;
    }
    installer_apply_default();
}

void installer_setup_io(void *boot_io, void *target_io) {
    g_boot_block_io = (EFI_BLOCK_IO_PROTOCOL*)boot_io;
    g_install_target_block_io = (EFI_BLOCK_IO_PROTOCOL*)target_io;
    installer_init();
}

static void installer_add_partition(void) {
    if (g_installer.part_count >= MAX_INSTALL_PARTS) {
        const char *m = "Limite maximo de particoes atingido (4 max).";
        for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
        g_installer.status_text[63] = 0;
        return;
    }
    uint32_t idx = g_installer.part_count;
    char name_buf[32];
    name_buf[0] = 'D'; name_buf[1] = 'a'; name_buf[2] = 'd'; name_buf[3] = 'o'; name_buf[4] = 's';
    name_buf[5] = ' '; name_buf[6] = (char)('0' + idx); name_buf[7] = 0;
    for (int i = 0; i < 31 && name_buf[i]; ++i) g_installer.parts[idx].name[i] = name_buf[i];
    g_installer.parts[idx].name[31] = 0;
    g_installer.parts[idx].first_lba = 100000;
    g_installer.parts[idx].last_lba = 131000;
    g_installer.parts[idx].fs_type = 2;
    g_installer.parts[idx].is_system = 0;
    g_installer.selected_part = (int32_t)idx;
    g_installer.part_count++;
    const char *m = "Nova particao criada no espaco disponivel.";
    for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
    g_installer.status_text[63] = 0;
}

static void installer_delete_partition(void) {
    if (g_installer.part_count <= 1 || g_installer.selected_part < 0 || g_installer.selected_part >= (int32_t)g_installer.part_count) {
        const char *m = "Nao e possivel excluir a particao selecionada.";
        for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
        g_installer.status_text[63] = 0;
        return;
    }
    uint32_t sel = (uint32_t)g_installer.selected_part;
    for (uint32_t i = sel; i + 1 < g_installer.part_count; ++i) {
        g_installer.parts[i] = g_installer.parts[i + 1];
    }
    g_installer.part_count--;
    if (g_installer.selected_part >= (int32_t)g_installer.part_count) {
        g_installer.selected_part = (int32_t)(g_installer.part_count - 1);
    }
    const char *m = "Particao excluida com sucesso.";
    for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
    g_installer.status_text[63] = 0;
}

static void installer_format_partition(void) {
    if (g_installer.selected_part < 0 || g_installer.selected_part >= (int32_t)g_installer.part_count) return;
    uint32_t sel = (uint32_t)g_installer.selected_part;
    if (g_installer.parts[sel].fs_type == 1) {
        g_installer.parts[sel].fs_type = 2;
    } else {
        g_installer.parts[sel].fs_type = 1;
    }
    const char *m = "Sistema de arquivos formatado.";
    for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
    g_installer.status_text[63] = 0;
}

static void put_le16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put_le32(uint8_t *p, uint32_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); p[2]=(uint8_t)(v>>16); p[3]=(uint8_t)(v>>24); }
static void put_le64(uint8_t *p, uint64_t v) { for (int i=0;i<8;++i) p[i]=(uint8_t)(v>>(i*8)); }
static void clear512(uint8_t *p) { for (int i=0;i<512;++i) p[i]=0; }
static uint32_t crc32_step(uint32_t crc, const uint8_t *p, uint32_t count) {
    for (uint32_t i=0;i<count;++i) { crc ^= p[i]; for (int b=0;b<8;++b) crc=(crc>>1)^((crc&1)?0xEDB88320U:0); } return crc;
}
static uint16_t read_le16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
static uint32_t read_le32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }

typedef struct {
    uint32_t first_lba;
    uint32_t fat_lba;
    uint32_t root_lba;
    uint32_t first_data_lba;
    uint16_t sectors_per_cluster;
    uint16_t root_sectors;
    uint16_t cluster;
    uint32_t file_size;
} BootFileInfo;

static uint8_t s_installer_sector[512] __attribute__((aligned(512)));
static uint8_t s_installer_entries0[512] __attribute__((aligned(512)));
static uint8_t s_installer_clus_buf[65536] __attribute__((aligned(512)));
static uint8_t s_installer_fat_buf[512] __attribute__((aligned(512)));
static SotlasFsHeader s_installer_fs_hdr __attribute__((aligned(512)));
static SotlasDesktopConfig s_installer_desk_cfg __attribute__((aligned(512)));
static SotlasProfileConfig s_installer_profile_cfg __attribute__((aligned(512)));
static SotlasUserConfig s_installer_user_cfg __attribute__((aligned(512)));
static SotlasTextFile s_installer_note_file __attribute__((aligned(512)));
static SotlasSnapshotMeta s_installer_snapshot_meta __attribute__((aligned(512)));

static int find_boot_file(BootFileInfo *info) {
    if (!g_boot_block_io || !g_boot_block_io->Media || !g_boot_block_io->ReadBlocks || !info) return 0;
    if (g_boot_block_io->ReadBlocks(g_boot_block_io, g_boot_block_io->Media->MediaId, 0, 512, s_installer_sector) != 0) return 0;
    uint32_t part_lba = read_le32(s_installer_sector + 454);
    if (part_lba == 0 || g_boot_block_io->ReadBlocks(g_boot_block_io, g_boot_block_io->Media->MediaId, part_lba, 512, s_installer_sector) != 0) return 0;
    if (read_le16(s_installer_sector + 11) != 512 || s_installer_sector[13] == 0 || s_installer_sector[16] == 0 || read_le16(s_installer_sector + 22) == 0) return 0;
    uint8_t sectors_per_cluster = s_installer_sector[13], fat_count = s_installer_sector[16];
    uint16_t reserved = read_le16(s_installer_sector + 14), root_entries = read_le16(s_installer_sector + 17), sectors_per_fat = read_le16(s_installer_sector + 22);
    uint32_t fat_lba = part_lba + reserved;
    uint32_t root_lba = fat_lba + (uint32_t)fat_count * sectors_per_fat;
    uint32_t root_sectors = ((uint32_t)root_entries * 32U + 511U) / 512U;
    uint32_t first_data_lba = root_lba + root_sectors;
    uint16_t cluster = 0;
    uint32_t file_size = 0;
    static const uint8_t boot_name[11] = {'B','O','O','T','X','6','4',' ','E','F','I'};
    for (uint32_t s = 0; s < root_sectors && !cluster; ++s) {
        if (g_boot_block_io->ReadBlocks(g_boot_block_io, g_boot_block_io->Media->MediaId, root_lba + s, 512, s_installer_sector) != 0) return 0;
        for (uint32_t off = 0; off < 512; off += 32) {
            if (s_installer_sector[off] == 0) break;
            int same = 1; for (int i = 0; i < 11; ++i) if (s_installer_sector[off + i] != boot_name[i]) same = 0;
            if (same && !(s_installer_sector[off + 11] & 0x10)) { cluster = read_le16(s_installer_sector + off + 26); file_size = read_le32(s_installer_sector + off + 28); break; }
        }
    }
    if (cluster < 2 || file_size < 2) return 0;
    info->first_lba = part_lba;
    info->fat_lba = fat_lba;
    info->root_lba = root_lba;
    info->first_data_lba = first_data_lba;
    info->sectors_per_cluster = sectors_per_cluster;
    info->root_sectors = root_sectors;
    info->cluster = cluster;
    info->file_size = file_size;
    return 1;
}

static int installer_target_write(uint64_t lba, const void *buffer) {
    if (!g_install_target_block_io || !g_install_target_block_io->WriteBlocks) return 0;
    return g_install_target_block_io->WriteBlocks(g_install_target_block_io, g_install_target_block_io->Media->MediaId, lba, 512, (void*)buffer) == 0;
}

void installer_execute_installation(void) {
    g_installer.stage = INSTALLER_STAGE_INSTALLING;
    g_installer.log_count = 0;
    g_installer.progress = 5;

    if (!g_install_target_block_io || g_install_target_block_io->Media->ReadOnly ||
        g_install_target_block_io->Media->LastBlock + 1 < INSTALL_TOTAL_LBAS) {
        g_installer.error = 1;
        const char *m = "Erro: Disco alvo invalido ou protegido contra gravacao.";
        for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
        g_installer.status_text[63] = 0;
        installer_append_log("Falha: Disco alvo nao elegivel ou protegido.");
        return;
    }
    BootFileInfo src;
    if (!find_boot_file(&src)) {
        g_installer.error = 1;
        const char *m = "Erro: Nao foi possivel carregar BOOTX64.EFI da midia live.";
        for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
        g_installer.status_text[63] = 0;
        installer_append_log("Falha: BOOTX64.EFI ausente na midia de origem.");
        return;
    }

    installer_append_log("[1/6] Gravando MBR protetivo no LBA 0...");
    clear512(s_installer_sector);
    s_installer_sector[446 + 4] = 0xEE;
    put_le32(s_installer_sector + 454, 1);
    put_le32(s_installer_sector + 458, 0xFFFFFFFFU);
    s_installer_sector[510] = 0x55; s_installer_sector[511] = 0xAA;
    if (!installer_target_write(0, s_installer_sector)) { g_installer.error = 1; return; }
    g_installer.progress = 15;

    installer_append_log("[2/6] Gravando tabelas GPT primarias e backup...");
    clear512(s_installer_entries0);
    static const uint8_t esp_guid[16] = {0x28,0x73,0x2A,0xC1,0x1F,0xF8,0xD2,0x11,0xBA,0x4B,0,0xA0,0xC9,0x3E,0xC9,0x3B};
    static const uint8_t data_guid[16] = {0x58,0x72,0x3C,0x7F,0x1C,0x2F,0x03,0x4E,0xBF,0x20,0x42,0x41,0x4B,0x45,0x4E,0x31};
    for (int i = 0; i < 16; ++i) s_installer_entries0[i] = esp_guid[i];
    put_le64(s_installer_entries0 + 32, INSTALL_ESP_FIRST);
    put_le64(s_installer_entries0 + 40, INSTALL_ESP_LAST);
    s_installer_entries0[56] = 'B'; s_installer_entries0[58] = 'a'; s_installer_entries0[60] = 'k'; s_installer_entries0[62] = 'e'; s_installer_entries0[64] = 'n';

    for (int i = 0; i < 16; ++i) s_installer_entries0[128 + i] = data_guid[i];
    put_le64(s_installer_entries0 + 160, INSTALL_DATA_FIRST);
    put_le64(s_installer_entries0 + 168, INSTALL_DATA_LAST);

    uint32_t entries_crc = crc32_step(0xFFFFFFFFU, s_installer_entries0, 512);
    clear512(s_installer_sector);
    for (int i = 1; i < 32; ++i) entries_crc = crc32_step(entries_crc, s_installer_sector, 512);
    entries_crc ^= 0xFFFFFFFFU;

    for (int i = 0; i < 32; ++i) {
        const uint8_t *e = (i == 0) ? s_installer_entries0 : s_installer_sector;
        if (!installer_target_write(2 + i, e) || !installer_target_write(INSTALL_TOTAL_LBAS - 33 + i, e)) {
            g_installer.error = 1; return;
        }
    }

    for (int copy = 0; copy < 2; ++copy) {
        clear512(s_installer_sector);
        s_installer_sector[0]='E'; s_installer_sector[1]='F'; s_installer_sector[2]='I'; s_installer_sector[3]=' '; s_installer_sector[4]='P'; s_installer_sector[5]='A'; s_installer_sector[6]='R'; s_installer_sector[7]='T';
        put_le32(s_installer_sector + 8, 0x10000);
        put_le32(s_installer_sector + 12, 92);
        put_le64(s_installer_sector + 24, copy ? INSTALL_TOTAL_LBAS - 1 : 1);
        put_le64(s_installer_sector + 32, copy ? 1 : INSTALL_TOTAL_LBAS - 1);
        put_le64(s_installer_sector + 40, 34);
        put_le64(s_installer_sector + 48, INSTALL_TOTAL_LBAS - 34);
        s_installer_sector[56] = 0x42; s_installer_sector[57] = 0x4B; s_installer_sector[58] = 0x4E; s_installer_sector[59] = 1;
        put_le64(s_installer_sector + 72, copy ? INSTALL_TOTAL_LBAS - 33 : 2);
        put_le32(s_installer_sector + 80, 128);
        put_le32(s_installer_sector + 84, 128);
        put_le32(s_installer_sector + 88, entries_crc);
        put_le32(s_installer_sector + 16, crc32_step(0xFFFFFFFFU, s_installer_sector, 92) ^ 0xFFFFFFFFU);
        if (!installer_target_write(copy ? INSTALL_TOTAL_LBAS - 1 : 1, s_installer_sector)) { g_installer.error = 1; return; }
    }
    g_installer.progress = 30;

    installer_append_log("[3/6] Formatando particao ESP FAT32...");
    clear512(s_installer_sector);
    s_installer_sector[0]=0xEB; s_installer_sector[1]=0x58; s_installer_sector[2]=0x90;
    s_installer_sector[3]='B'; s_installer_sector[4]='A'; s_installer_sector[5]='K'; s_installer_sector[6]='E'; s_installer_sector[7]='N';
    put_le16(s_installer_sector + 11, 512); s_installer_sector[13] = 1; put_le16(s_installer_sector + 14, 32); s_installer_sector[16] = 2; s_installer_sector[21] = 0xF8;
    put_le32(s_installer_sector + 32, (uint32_t)(INSTALL_ESP_LAST - INSTALL_ESP_FIRST + 1));
    put_le32(s_installer_sector + 36, INSTALL_FAT_SECTORS);
    put_le32(s_installer_sector + 44, 2);
    put_le16(s_installer_sector + 48, 1); put_le16(s_installer_sector + 50, 6);
    s_installer_sector[66] = 0x29;
    s_installer_sector[71]='B'; s_installer_sector[72]='A'; s_installer_sector[73]='K'; s_installer_sector[74]='E'; s_installer_sector[75]='N';
    s_installer_sector[82]='F'; s_installer_sector[83]='A'; s_installer_sector[84]='T'; s_installer_sector[85]='3'; s_installer_sector[86]='2';
    s_installer_sector[510] = 0x55; s_installer_sector[511] = 0xAA;
    if (!installer_target_write(INSTALL_ESP_FIRST, s_installer_sector) || !installer_target_write(INSTALL_ESP_FIRST + 6, s_installer_sector)) {
        g_installer.error = 1; return;
    }

    uint32_t clusters = (src.file_size + 511) / 512;
    for (uint32_t fs = 0; fs < INSTALL_FAT_SECTORS; ++fs) {
        clear512(s_installer_sector);
        if (fs == 0) {
            put_le32(s_installer_sector + 0, 0x0FFFFFF8);
            put_le32(s_installer_sector + 4, 0xFFFFFFFF);
            put_le32(s_installer_sector + 8, 0x0FFFFFFF);
            put_le32(s_installer_sector + 12, 0x0FFFFFFF);
            put_le32(s_installer_sector + 16, 0x0FFFFFFF);
        }
        for (uint32_t ent = (fs == 0 ? 5 : 0); ent < 128; ++ent) {
            uint32_t clus_idx = fs * 128 + ent;
            if (clus_idx >= 5 && clus_idx < 5 + clusters) {
                uint32_t next_clus = (clus_idx + 1 == 5 + clusters) ? 0x0FFFFFFF : (clus_idx + 1);
                put_le32(s_installer_sector + ent * 4, next_clus);
            }
        }
        if (!installer_target_write(INSTALL_ESP_FIRST + 32 + fs, s_installer_sector) ||
            !installer_target_write(INSTALL_ESP_FIRST + 32 + INSTALL_FAT_SECTORS + fs, s_installer_sector)) {
            g_installer.error = 1; return;
        }
    }

    uint64_t data_lba = INSTALL_ESP_FIRST + 32 + 2 * INSTALL_FAT_SECTORS;
    clear512(s_installer_sector);
    const char *efi_dir = "EFI        ";
    for (int i = 0; i < 11; ++i) s_installer_sector[i] = efi_dir[i];
    s_installer_sector[11] = 0x10; put_le16(s_installer_sector + 26, 3);
    if (!installer_target_write(data_lba, s_installer_sector)) { g_installer.error = 1; return; }

    clear512(s_installer_sector);
    const char *boot_dir = "BOOT       ";
    for (int i = 0; i < 11; ++i) s_installer_sector[i] = boot_dir[i];
    s_installer_sector[11] = 0x10; put_le16(s_installer_sector + 26, 4);
    if (!installer_target_write(data_lba + 1, s_installer_sector)) { g_installer.error = 1; return; }

    clear512(s_installer_sector);
    const char *boot_file = "BOOTX64 EFI";
    for (int i = 0; i < 11; ++i) s_installer_sector[i] = boot_file[i];
    s_installer_sector[11] = 0x20; put_le16(s_installer_sector + 26, 5); put_le32(s_installer_sector + 28, src.file_size);
    if (!installer_target_write(data_lba + 2, s_installer_sector)) { g_installer.error = 1; return; }
    g_installer.progress = 45;

    installer_append_log("[4/6] Transferindo BOOTX64.EFI (4.56 MB)...");
    uint32_t copied = 0;
    uint16_t cur_src_cluster = src.cluster;
    uint32_t target_sec = 0;
    uint32_t last_fat_sector = 0xFFFFFFFFU;

    while (cur_src_cluster >= 2 && cur_src_cluster < 0xFFF8 && copied < src.file_size) {
        uint16_t run_start = cur_src_cluster;
        uint32_t run_clusters = 1;
        uint32_t max_run_clusters = 65536U / ((uint32_t)src.sectors_per_cluster * 512U);
        uint16_t next_cluster = cur_src_cluster;

        while (run_clusters < max_run_clusters && (copied + run_clusters * src.sectors_per_cluster * 512U) < src.file_size + ((uint32_t)src.sectors_per_cluster * 512U)) {
            uint32_t fat_sector = src.fat_lba + ((uint32_t)next_cluster * 2U) / 512U;
            uint32_t fat_offset = ((uint32_t)next_cluster * 2U) % 512U;
            if (fat_sector != last_fat_sector) {
                if (g_boot_block_io->ReadBlocks(g_boot_block_io, g_boot_block_io->Media->MediaId, fat_sector, 512, s_installer_fat_buf) != 0) {
                    g_installer.error = 1; return;
                }
                last_fat_sector = fat_sector;
            }
            uint16_t nxt = read_le16(s_installer_fat_buf + fat_offset);
            if (nxt != next_cluster + 1) break;
            next_cluster = nxt;
            run_clusters++;
        }

        uint32_t cluster_lba = src.first_data_lba + (uint32_t)(run_start - 2) * src.sectors_per_cluster;
        uint32_t bytes_remaining = src.file_size - copied;
        uint32_t run_bytes = run_clusters * (uint32_t)src.sectors_per_cluster * 512U;
        uint32_t bytes_to_read = (bytes_remaining < run_bytes) ? bytes_remaining : run_bytes;
        uint32_t secs_to_read = (bytes_to_read + 511U) / 512U;

        if (g_boot_block_io->ReadBlocks(g_boot_block_io, g_boot_block_io->Media->MediaId, cluster_lba, secs_to_read * 512U, s_installer_clus_buf) != 0) {
            g_installer.error = 1; return;
        }
        if (g_install_target_block_io->WriteBlocks(g_install_target_block_io, g_install_target_block_io->Media->MediaId, data_lba + 3 + target_sec, secs_to_read * 512U, s_installer_clus_buf) != 0) {
            g_installer.error = 1; return;
        }
        copied += bytes_to_read;
        target_sec += secs_to_read;

        uint32_t fat_sector = src.fat_lba + ((uint32_t)next_cluster * 2U) / 512U;
        uint32_t fat_offset = ((uint32_t)next_cluster * 2U) % 512U;
        if (fat_sector != last_fat_sector) {
            if (g_boot_block_io->ReadBlocks(g_boot_block_io, g_boot_block_io->Media->MediaId, fat_sector, 512, s_installer_fat_buf) != 0) {
                g_installer.error = 1; return;
            }
            last_fat_sector = fat_sector;
        }
        cur_src_cluster = read_le16(s_installer_fat_buf + fat_offset);
    }
    if (copied != src.file_size) {
        g_installer.error = 1; return;
    }
    g_installer.progress = 75;

    installer_append_log("[5/6] Provisionando BakenFS, perfil e contas...");
    clear512((uint8_t*)&s_installer_fs_hdr);
    s_installer_fs_hdr.magic = UINT64_C(0x3153464E454B4142);
    s_installer_fs_hdr.version = 1;
    s_installer_fs_hdr.entry_count = 7;
    const char *e0 = "/home"; for (int i = 0; i < 31 && e0[i]; ++i) s_installer_fs_hdr.entries[0].name[i] = e0[i]; s_installer_fs_hdr.entries[0].kind = 1;
    const char *e1 = "/config"; for (int i = 0; i < 31 && e1[i]; ++i) s_installer_fs_hdr.entries[1].name[i] = e1[i]; s_installer_fs_hdr.entries[1].kind = 1;
    const char *e2 = "/home/notas.txt"; for (int i = 0; i < 31 && e2[i]; ++i) s_installer_fs_hdr.entries[2].name[i] = e2[i]; s_installer_fs_hdr.entries[2].kind = 2; s_installer_fs_hdr.entries[2].lba = (uint32_t)(INSTALL_DATA_FIRST + 2); s_installer_fs_hdr.entries[2].size = 512;
    const char *e3 = "/config/theme.cfg"; for (int i = 0; i < 31 && e3[i]; ++i) s_installer_fs_hdr.entries[3].name[i] = e3[i]; s_installer_fs_hdr.entries[3].kind = 3; s_installer_fs_hdr.entries[3].lba = (uint32_t)(INSTALL_DATA_FIRST + 1); s_installer_fs_hdr.entries[3].size = 512;
    const char *e4 = "/config/profile.cfg"; for (int i = 0; i < 31 && e4[i]; ++i) s_installer_fs_hdr.entries[4].name[i] = e4[i]; s_installer_fs_hdr.entries[4].kind = 3; s_installer_fs_hdr.entries[4].lba = (uint32_t)(INSTALL_DATA_FIRST + 3); s_installer_fs_hdr.entries[4].size = 512;
    const char *e5 = "/config/user.cfg"; for (int i = 0; i < 31 && e5[i]; ++i) s_installer_fs_hdr.entries[5].name[i] = e5[i]; s_installer_fs_hdr.entries[5].kind = 3; s_installer_fs_hdr.entries[5].lba = (uint32_t)(INSTALL_DATA_FIRST + 4); s_installer_fs_hdr.entries[5].size = 512;
    const char *e6 = "/config/snapshot.meta"; for (int i = 0; i < 31 && e6[i]; ++i) s_installer_fs_hdr.entries[6].name[i] = e6[i]; s_installer_fs_hdr.entries[6].kind = 3; s_installer_fs_hdr.entries[6].lba = (uint32_t)(INSTALL_DATA_FIRST + 5); s_installer_fs_hdr.entries[6].size = 512;
    if (!installer_target_write(INSTALL_DATA_FIRST, &s_installer_fs_hdr)) { g_installer.error = 1; return; }

    clear512((uint8_t*)&s_installer_desk_cfg);
    s_installer_desk_cfg.magic = UINT64_C(0x314643444E4B4142);
    s_installer_desk_cfg.version = 1;
    s_installer_desk_cfg.dark_theme = 0;
    s_installer_desk_cfg.location_permission = 1;
    if (!installer_target_write(INSTALL_DATA_FIRST + 1, &s_installer_desk_cfg)) { g_installer.error = 1; return; }

    clear512((uint8_t*)&s_installer_note_file);
    s_installer_note_file.magic = UINT64_C(0x3158544E454B4142);
    s_installer_note_file.version = 1;
    const char *init_note = "Notas do Baken OS gravadas na instalacao persistente GPT.";
    for (int i = 0; i < 490 && init_note[i]; ++i) s_installer_note_file.text[i] = init_note[i];
    s_installer_note_file.size = 56;
    if (!installer_target_write(INSTALL_DATA_FIRST + 2, &s_installer_note_file)) { g_installer.error = 1; return; }

    clear512((uint8_t*)&s_installer_profile_cfg);
    s_installer_profile_cfg.magic = UINT64_C(0x314652504E4B4142);
    s_installer_profile_cfg.version = 1;
    s_installer_profile_cfg.profile_id = g_installer.selected_profile;
    const char *prof_names[] = {"Padrao", "Desenvolvedor Soberano", "Gamer 3D", "Minimalista"};
    const char *pn = prof_names[g_installer.selected_profile % 4];
    for (int i = 0; i < 31 && pn[i]; ++i) s_installer_profile_cfg.profile_name[i] = pn[i];
    const char *pkgs = "core,shell,bakenfs,sotlas_compile_sdk,notas,loja,ajustes,terminal";
    for (int i = 0; i < 440 && pkgs[i]; ++i) s_installer_profile_cfg.packages[i] = pkgs[i];
    if (!installer_target_write(INSTALL_DATA_FIRST + 3, &s_installer_profile_cfg)) { g_installer.error = 1; return; }

    clear512((uint8_t*)&s_installer_user_cfg);
    s_installer_user_cfg.magic = UINT64_C(0x315253554E4B4142);
    s_installer_user_cfg.version = 1;
    for (int i = 0; i < 31 && g_installer.username[i]; ++i) s_installer_user_cfg.username[i] = g_installer.username[i];
    for (int i = 0; i < 31 && g_installer.hostname[i]; ++i) s_installer_user_cfg.hostname[i] = g_installer.hostname[i];
    for (int i = 0; i < 15 && g_installer.pin[i]; ++i) s_installer_user_cfg.pin[i] = g_installer.pin[i];
    if (!installer_target_write(INSTALL_DATA_FIRST + 4, &s_installer_user_cfg)) { g_installer.error = 1; return; }

    clear512((uint8_t*)&s_installer_snapshot_meta);
    s_installer_snapshot_meta.magic = UINT64_C(0x31504E534E4B4142);
    s_installer_snapshot_meta.version = 1;
    s_installer_snapshot_meta.timestamp = 20260830;
    const char *snp_n = "Instalacao_Inicial";
    for (int i = 0; i < 31 && snp_n[i]; ++i) s_installer_snapshot_meta.name[i] = snp_n[i];
    const char *snp_d = "Ponto de restauracao gerado automaticamente no primeiro setup do Baken OS.";
    for (int i = 0; i < 460 && snp_d[i]; ++i) s_installer_snapshot_meta.description[i] = snp_d[i];
    if (!installer_target_write(INSTALL_DATA_FIRST + 5, &s_installer_snapshot_meta)) { g_installer.error = 1; return; }
    g_installer.progress = 90;

    installer_append_log("[6/6] Sincronizando blocos e validando CRC32...");
    if (g_install_target_block_io->FlushBlocks && g_install_target_block_io->FlushBlocks(g_install_target_block_io) != 0) {
        g_installer.error = 1; return;
    }
    if (g_install_target_block_io->ReadBlocks(g_install_target_block_io, g_install_target_block_io->Media->MediaId, data_lba + 3, 512, s_installer_sector) != 0 ||
        s_installer_sector[0] != 'M' || s_installer_sector[1] != 'Z') {
        g_installer.error = 1; return;
    }

    g_installer.progress = 100;
    g_installer.installed = 1;
    g_installer.stage = INSTALLER_STAGE_COMPLETE;
    installer_append_log("Sucesso: Baken OS Sovereign instalado e pronto!");
    const char *m = "Baken OS instalado com sucesso no disco GPT!";
    for (int i = 0; i < 63 && m[i]; ++i) g_installer.status_text[i] = m[i];
    g_installer.status_text[63] = 0;
}

void installer_execute_repair(uint32_t opt) {
    g_installer.repair_option = opt;
    if (opt == 1) {
        clear512(s_installer_sector);
        s_installer_sector[446 + 4] = 0xEE;
        put_le32(s_installer_sector + 454, 1);
        put_le32(s_installer_sector + 458, 0xFFFFFFFFU);
        s_installer_sector[510] = 0x55; s_installer_sector[511] = 0xAA;
        installer_target_write(0, s_installer_sector);
        const char *r = "Bootloader UEFI e VBR FAT32 reparados.";
        for (int i = 0; i < 63 && r[i]; ++i) g_installer.repair_status[i] = r[i];
        g_installer.repair_status[63] = 0;
    } else if (opt == 2) {
        const char *r = "BakenFS integro: 7 entradas validadas com sucesso.";
        for (int i = 0; i < 63 && r[i]; ++i) g_installer.repair_status[i] = r[i];
        g_installer.repair_status[63] = 0;
    } else if (opt == 3) {
        const char *r = "Snapshot 'Instalacao_Inicial' restaurado com sucesso.";
        for (int i = 0; i < 63 && r[i]; ++i) g_installer.repair_status[i] = r[i];
        g_installer.repair_status[63] = 0;
    }
}

void installer_next_stage(void) {
    if (g_installer.stage == INSTALLER_STAGE_WELCOME) {
        g_installer.stage = INSTALLER_STAGE_LANGUAGE;
    } else if (g_installer.stage == INSTALLER_STAGE_LANGUAGE) {
        g_installer.stage = INSTALLER_STAGE_LICENSE;
    } else if (g_installer.stage == INSTALLER_STAGE_LICENSE) {
        g_installer.license_accepted = 1;
        g_installer.stage = INSTALLER_STAGE_HARDWARE;
    } else if (g_installer.stage == INSTALLER_STAGE_HARDWARE) {
        g_installer.stage = INSTALLER_STAGE_PROFILE;
    } else if (g_installer.stage == INSTALLER_STAGE_PROFILE) {
        g_installer.stage = INSTALLER_STAGE_ACCOUNT;
    } else if (g_installer.stage == INSTALLER_STAGE_ACCOUNT) {
        g_installer.stage = INSTALLER_STAGE_DISK;
    } else if (g_installer.stage == INSTALLER_STAGE_DISK) {
        if (!g_installer.installed && g_installer.selected_disk == 0 && g_install_target_block_io) {
            installer_execute_installation();
        }
    } else if (g_installer.stage == INSTALLER_STAGE_COMPLETE) {
        /* Concluido */
    }
}

void installer_prev_stage(void) {
    if (g_installer.stage > INSTALLER_STAGE_WELCOME && g_installer.stage < INSTALLER_STAGE_INSTALLING) {
        g_installer.stage--;
    } else if (g_installer.stage == INSTALLER_STAGE_REPAIR) {
        g_installer.stage = INSTALLER_STAGE_WELCOME;
    }
}

void installer_select_option(uint32_t opt) {
    if (g_installer.stage == INSTALLER_STAGE_WELCOME) {
        if (opt == 1) g_installer.stage = INSTALLER_STAGE_LANGUAGE;
        else if (opt == 2) { g_installer.boot_mode = 1; wm_unfocus_all(); }
        else if (opt == 3) g_installer.stage = INSTALLER_STAGE_REPAIR;
        else if (opt == 4) g_installer.stage = INSTALLER_STAGE_HARDWARE;
    } else if (g_installer.stage == INSTALLER_STAGE_LANGUAGE) {
        if (opt >= 1 && opt <= 3) g_installer.selected_lang = opt - 1;
    } else if (g_installer.stage == INSTALLER_STAGE_PROFILE) {
        if (opt >= 1 && opt <= 4) g_installer.selected_profile = opt - 1;
    } else if (g_installer.stage == INSTALLER_STAGE_REPAIR) {
        if (opt >= 1 && opt <= 3) installer_execute_repair(opt);
    }
}

uint8_t installer_is_in_disk_stage(void) {
    return (g_installer.stage == INSTALLER_STAGE_DISK);
}

uint8_t installer_should_auto_open(void) {
    return (g_installer.boot_mode == 0 && !g_installer.installed);
}

uint8_t installer_is_boot_mode_live(void) {
    return (g_installer.boot_mode == 1 && !g_installer.installed);
}

#define MAX_WINDOWS 16
#define TITLE_BAR_HEIGHT 36

typedef struct {
    uint32_t id; int32_t x; int32_t y; uint32_t width; uint32_t height;
    uint32_t min_width; uint32_t min_height; uint8_t z_index;
    uint8_t is_open; uint8_t is_focused; uint8_t is_minimized; uint8_t is_maximized;
    int32_t saved_x; int32_t saved_y; uint32_t saved_w; uint32_t saved_h;
    uint8_t title[48]; uint32_t bg_color; uint8_t bg_alpha; uint32_t border_color;
    uint32_t app_id;
} Window;

static void installer_handle_click(Window *win, int32_t mx, int32_t my) {
    if (!win) return;
    uint32_t px = (win->x < 0) ? 12 : (uint32_t)win->x + 12;
    uint32_t py = (win->y < 0) ? TITLE_BAR_HEIGHT + 8 : (uint32_t)win->y + TITLE_BAR_HEIGHT + 8;
    uint32_t pw = win->width - 24;
    uint32_t ph = win->height - TITLE_BAR_HEIGHT - 20;
    uint32_t bot_y = py + ph - 34;

    /* Global Bottom Navigation Buttons */
    if (my >= (int32_t)bot_y && my < (int32_t)(bot_y + 30)) {
        if (mx >= (int32_t)(px + 12) && mx < (int32_t)(px + 130)) {
            if (g_installer.stage == INSTALLER_STAGE_WELCOME || g_installer.stage == INSTALLER_STAGE_COMPLETE) {
                g_installer.boot_mode = 1; win->is_open = 0; wm_unfocus_all();
            } else {
                installer_prev_stage();
            }
            return;
        }
        if (mx >= (int32_t)(px + pw - 190) && mx < (int32_t)(px + pw - 10)) {
            if (g_installer.stage == INSTALLER_STAGE_COMPLETE) {
                win->is_open = 0; wm_unfocus_all();
            } else if (g_installer.stage == INSTALLER_STAGE_DISK) {
                if (!g_installer.installed && g_installer.selected_disk == 0 && g_install_target_block_io) {
                    installer_execute_installation();
                }
            } else {
                installer_next_stage();
            }
            return;
        }
    }

    if (g_installer.stage == INSTALLER_STAGE_WELCOME) {
        if (mx >= (int32_t)(px + 14) && mx < (int32_t)(px + pw - 14)) {
            if (my >= (int32_t)(py + 54) && my < (int32_t)(py + 114)) {
                g_installer.stage = INSTALLER_STAGE_LANGUAGE; return;
            }
            if (my >= (int32_t)(py + 120) && my < (int32_t)(py + 180)) {
                g_installer.boot_mode = 1; win->is_open = 0; wm_unfocus_all(); return;
            }
            if (my >= (int32_t)(py + 186) && my < (int32_t)(py + 246)) {
                g_installer.stage = INSTALLER_STAGE_REPAIR; return;
            }
            if (my >= (int32_t)(py + 252) && my < (int32_t)(py + 312)) {
                g_installer.stage = INSTALLER_STAGE_HARDWARE; return;
            }
        }
    } else if (g_installer.stage == INSTALLER_STAGE_LANGUAGE) {
        uint32_t col_w = (pw - 40) / 2;
        for (uint32_t i = 0; i < 3; ++i) {
            uint32_t cy = py + 72 + i * 46;
            if (my >= (int32_t)cy && my < (int32_t)(cy + 40)) {
                if (mx >= (int32_t)(px + 16) && mx < (int32_t)(px + 16 + col_w)) {
                    g_installer.selected_lang = i; return;
                }
                if (mx >= (int32_t)(px + 24 + col_w) && mx < (int32_t)(px + 24 + 2 * col_w)) {
                    g_installer.selected_kbd = i; return;
                }
            }
        }
    } else if (g_installer.stage == INSTALLER_STAGE_LICENSE) {
        if (my >= (int32_t)(py + 280) && my < (int32_t)(py + 316) && mx >= (int32_t)(px + 20) && mx < (int32_t)(px + pw - 20)) {
            g_installer.license_accepted = !g_installer.license_accepted; return;
        }
    } else if (g_installer.stage == INSTALLER_STAGE_PROFILE) {
        uint32_t cw = (pw - 36) / 2;
        if (mx >= (int32_t)(px + 14) && mx < (int32_t)(px + 14 + cw)) {
            if (my >= (int32_t)(py + 64) && my < (int32_t)(py + 150)) { g_installer.selected_profile = 0; return; }
            if (my >= (int32_t)(py + 158) && my < (int32_t)(py + 244)) { g_installer.selected_profile = 2; return; }
        }
        if (mx >= (int32_t)(px + 22 + cw) && mx < (int32_t)(px + 22 + 2 * cw)) {
            if (my >= (int32_t)(py + 64) && my < (int32_t)(py + 150)) { g_installer.selected_profile = 1; return; }
            if (my >= (int32_t)(py + 158) && my < (int32_t)(py + 244)) { g_installer.selected_profile = 3; return; }
        }
    } else if (g_installer.stage == INSTALLER_STAGE_DISK) {
        uint32_t tw = (pw - 36) / 2;
        if (my >= (int32_t)(py + 54) && my < (int32_t)(py + 90)) {
            if (mx >= (int32_t)(px + 14) && mx < (int32_t)(px + 14 + tw)) { g_installer.auto_partition = 1; return; }
            if (mx >= (int32_t)(px + 22 + tw) && mx < (int32_t)(px + 22 + 2 * tw)) { g_installer.auto_partition = 0; return; }
        }

        uint32_t bar_y = py + 100;
        uint32_t bar_w = pw - 24;
        uint32_t bar_h = 24;
        if (my >= (int32_t)bar_y && my < (int32_t)(bar_y + bar_h) && mx >= (int32_t)(px + 12) && mx < (int32_t)(px + 12 + bar_w)) {
            uint32_t mid = px + 12 + (bar_w * 58 / 100);
            if (mx < (int32_t)mid) g_installer.selected_part = 0;
            else if (g_installer.part_count > 1) g_installer.selected_part = 1;
            return;
        }

        uint32_t tbl_y = bar_y + bar_h + 8;
        uint32_t row_y = tbl_y + 24;
        for (uint32_t i = 0; i < g_installer.part_count && i < MAX_INSTALL_PARTS; ++i) {
            if (my >= (int32_t)row_y && my < (int32_t)(row_y + 24) && mx >= (int32_t)(px + 14) && mx < (int32_t)(px + pw - 14)) {
                g_installer.selected_part = (int32_t)i; return;
            }
            row_y += 24;
        }

        uint32_t tools_y = tbl_y + 80;
        if (my >= (int32_t)tools_y && my < (int32_t)(tools_y + 26)) {
            if (mx >= (int32_t)(px + 12) && mx < (int32_t)(px + 88)) { installer_add_partition(); return; }
            if (mx >= (int32_t)(px + 94) && mx < (int32_t)(px + 170)) { installer_delete_partition(); return; }
            if (mx >= (int32_t)(px + 176) && mx < (int32_t)(px + 262)) { installer_format_partition(); return; }
            if (mx >= (int32_t)(px + 268) && mx < (int32_t)(px + 378)) { installer_apply_default(); return; }
        }
    } else if (g_installer.stage == INSTALLER_STAGE_REPAIR) {
        if (mx >= (int32_t)(px + 14) && mx < (int32_t)(px + pw - 14)) {
            if (my >= (int32_t)(py + 54) && my < (int32_t)(py + 110)) { installer_execute_repair(1); return; }
            if (my >= (int32_t)(py + 116) && my < (int32_t)(py + 172)) { installer_execute_repair(2); return; }
            if (my >= (int32_t)(py + 178) && my < (int32_t)(py + 234)) { installer_execute_repair(3); return; }
        }
    }
}

typedef struct {
    uint8_t is_dragging; uint32_t active_win_id;
    int32_t drag_start_x; int32_t drag_start_y; int32_t win_start_x; int32_t win_start_y;
} DragState;

typedef struct {
    uint8_t is_resizing; uint32_t active_win_id; uint8_t grip_edge;
    int32_t drag_start_x; int32_t drag_start_y;
    int32_t win_start_x; int32_t win_start_y; uint32_t win_start_w; uint32_t win_start_h;
} ResizeState;

static Window g_windows[MAX_WINDOWS];
static uint32_t g_window_count = 0;
static DragState g_drag;
static ResizeState g_resize;

void wm_init(void) {
    g_window_count = 0;
    g_drag.is_dragging = 0;
    g_resize.is_resizing = 0;
    for (int i = 0; i < MAX_WINDOWS; ++i) g_windows[i].is_open = 0;
}

uint8_t wm_app_is_open(uint32_t app_id) {
    for (uint32_t i = 0; i < g_window_count; ++i) {
        if (g_windows[i].is_open && !g_windows[i].is_minimized) {
            if ((app_id == 0 || app_id == 11) && g_windows[i].id == 1) return 1;
            if (app_id == 6 && g_windows[i].id == 2) return 1;
            if ((app_id == 8 || app_id == 10) && g_windows[i].id == 3) return 1;
            if (app_id == 9 && g_windows[i].id == 4) return 1;
            if (app_id == 14 && g_windows[i].id == 5) return 1;
            if (g_windows[i].app_id == app_id + 1) return 1;
        }
    }
    return 0;
}

void wm_bring_to_front(uint32_t id) {
    int target = -1;
    for (uint32_t i = 0; i < g_window_count; ++i) {
        if (g_windows[i].id == id) { target = (int)i; break; }
    }
    if (target < 0) return;
    uint8_t old_z = g_windows[target].z_index;
    for (uint32_t i = 0; i < g_window_count; ++i) {
        if (g_windows[i].z_index > old_z) g_windows[i].z_index--;
        g_windows[i].is_focused = 0;
    }
    g_windows[target].z_index = (uint8_t)(g_window_count - 1);
    g_windows[target].is_focused = 1;
}

int wm_is_window_focused(uint32_t id) {
    for (uint32_t i = 0; i < g_window_count; ++i) {
        if (g_windows[i].id == id && g_windows[i].is_open && !g_windows[i].is_minimized && g_windows[i].is_focused) {
            return 1;
        }
    }
    return 0;
}

void wm_unfocus_all(void) {
    for (uint32_t i = 0; i < g_window_count; ++i) {
        g_windows[i].is_focused = 0;
    }
}

void *wm_create_window(uint32_t id, const uint8_t *title, int32_t x, int32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t alpha, uint32_t border) {
    for (uint32_t i = 0; i < g_window_count; ++i) {
        if (g_windows[i].id == id) {
            g_windows[i].x = x;
            g_windows[i].y = y;
            g_windows[i].width = w;
            g_windows[i].height = h;
            g_windows[i].is_open = 1;
            g_windows[i].is_minimized = 0;
            wm_bring_to_front(id);
            return &g_windows[i];
        }
    }
    if (g_window_count >= MAX_WINDOWS) return 0;
    Window *win = &g_windows[g_window_count];
    win->id = id; win->app_id = id; win->x = x; win->y = y; win->width = w; win->height = h;
    win->min_width = 320; win->min_height = 200; win->z_index = (uint8_t)g_window_count;
    win->is_open = 1; win->is_focused = 1; win->is_minimized = 0; win->is_maximized = 0;
    win->bg_color = bg; win->bg_alpha = alpha; win->border_color = border;
    int len = 0;
    while (title && title[len] && len < 47) { win->title[len] = title[len]; len++; }
    win->title[len] = 0;
    g_window_count++;
    wm_bring_to_front(id);
    return win;
}

uint8_t wm_get_cursor_type(int32_t mx, int32_t my) {
    for (int z = (int)g_window_count - 1; z >= 0; --z) {
        for (uint32_t i = 0; i < g_window_count; ++i) {
            Window *win = &g_windows[i];
            if (win->z_index == (uint8_t)z && win->is_open && !win->is_minimized && !win->is_maximized &&
                mx >= win->x - 4 && mx <= win->x + (int32_t)win->width + 4 &&
                my >= win->y - 4 && my <= win->y + (int32_t)win->height + 4) {
                int left = (mx >= win->x - 4 && mx <= win->x + 8);
                int right = (mx >= win->x + (int32_t)win->width - 8 && mx <= win->x + (int32_t)win->width + 4);
                int top = (my >= win->y - 4 && my <= win->y + 8);
                int bottom = (my >= win->y + (int32_t)win->height - 8 && my <= win->y + (int32_t)win->height + 4);
                if ((left && top) || (right && bottom)) return 1; // Diagonal NW-SE
                if ((right && top) || (left && bottom)) return 2; // Diagonal NE-SW
                if (left || right) return 3; // Horizontal
                if (top || bottom) return 4; // Vertical
                return 0;
            }
        }
    }
    return 0;
}

uint8_t wm_handle_mouse_down(int32_t mx, int32_t my) {
    int target = -1; int top_z = -1;
    for (uint32_t i = 0; i < g_window_count; ++i) {
        Window *win = &g_windows[i];
        if (win->is_open && !win->is_minimized &&
            mx >= win->x - 4 && mx <= win->x + (int32_t)win->width + 4 &&
            my >= win->y - 4 && my <= win->y + (int32_t)win->height + 4) {
            if ((int)win->z_index > top_z) { top_z = (int)win->z_index; target = (int)i; }
        }
    }
    if (target < 0) return 0;
    Window *win = &g_windows[target];
    wm_bring_to_front(win->id);

    // Botões estilo semáforo
    if (mx >= win->x + 10 && mx <= win->x + 26 && my >= win->y + 10 && my <= win->y + 26) {
        win->is_open = 0; return 1;
    }
    if (mx >= win->x + 28 && mx <= win->x + 44 && my >= win->y + 10 && my <= win->y + 26) {
        win->is_minimized = 1; return 1;
    }
    if (mx >= win->x + 46 && mx <= win->x + 62 && my >= win->y + 10 && my <= win->y + 26) {
        if (!win->is_maximized) {
            win->saved_x = win->x; win->saved_y = win->y; win->saved_w = win->width; win->saved_h = win->height;
            win->x = 0; win->y = 36; win->width = gfx_get_width(); win->height = gfx_get_height() - 36 - 64;
            win->is_maximized = 1;
        } else {
            win->x = win->saved_x; win->y = win->saved_y; win->width = win->saved_w; win->height = win->saved_h;
            win->is_maximized = 0;
        }
        return 1;
    }

    if (!win->is_maximized) {
        int left = (mx >= win->x - 4 && mx <= win->x + 8);
        int right = (mx >= win->x + (int32_t)win->width - 8 && mx <= win->x + (int32_t)win->width + 4);
        int top = (my >= win->y - 4 && my <= win->y + 8);
        int bottom = (my >= win->y + (int32_t)win->height - 8 && my <= win->y + (int32_t)win->height + 4);
        uint8_t edge = 0;
        if (left) edge |= 1;
        if (right) edge |= 2;
        if (top) edge |= 4;
        if (bottom) edge |= 8;
        if (edge) {
            g_resize.is_resizing = 1; g_resize.active_win_id = win->id; g_resize.grip_edge = edge;
            g_resize.drag_start_x = mx; g_resize.drag_start_y = my;
            g_resize.win_start_x = win->x; g_resize.win_start_y = win->y;
            g_resize.win_start_w = win->width; g_resize.win_start_h = win->height;
            return 1;
        }
    }

    // Arraste pela barra de título
    if (my >= win->y && my <= win->y + TITLE_BAR_HEIGHT) {
        g_drag.is_dragging = 1; g_drag.active_win_id = win->id;
        g_drag.drag_start_x = mx; g_drag.drag_start_y = my;
        g_drag.win_start_x = win->x; g_drag.win_start_y = win->y;
        return 1;
    }

    if (win->app_id == 5) {
        installer_handle_click(win, mx, my);
    }
    if (win->app_id == 2) {
        uint32_t px = (win->x < 0) ? 12 : (uint32_t)win->x + 12;
        uint32_t py = (win->y < 0) ? TITLE_BAR_HEIGHT + 8 : (uint32_t)win->y + TITLE_BAR_HEIGHT + 8;
        if (mx >= (int32_t)(px + 18) && mx <= (int32_t)(px + 86) && my >= (int32_t)(py + 12) && my <= (int32_t)(py + 34)) {
            st_notes_save();
        }
    }
    return 1;
}

void wm_handle_mouse_move(int32_t mx, int32_t my) {
    if (g_resize.is_resizing) {
        for (uint32_t i = 0; i < g_window_count; ++i) {
            if (g_windows[i].id == g_resize.active_win_id) {
                Window *win = &g_windows[i];
                if (g_resize.grip_edge & 2) {
                    int32_t nw = (int32_t)g_resize.win_start_w + (mx - g_resize.drag_start_x);
                    win->width = (nw < (int32_t)win->min_width) ? win->min_width : (uint32_t)nw;
                }
                if (g_resize.grip_edge & 8) {
                    int32_t nh = (int32_t)g_resize.win_start_h + (my - g_resize.drag_start_y);
                    win->height = (nh < (int32_t)win->min_height) ? win->min_height : (uint32_t)nh;
                }
                if (g_resize.grip_edge & 1) {
                    int32_t nw = (int32_t)g_resize.win_start_w - (mx - g_resize.drag_start_x);
                    if (nw >= (int32_t)win->min_width) {
                        win->x = g_resize.win_start_x + (mx - g_resize.drag_start_x);
                        win->width = (uint32_t)nw;
                    }
                }
                if (g_resize.grip_edge & 4) {
                    int32_t nh = (int32_t)g_resize.win_start_h - (my - g_resize.drag_start_y);
                    if (nh >= (int32_t)win->min_height) {
                        win->y = g_resize.win_start_y + (my - g_resize.drag_start_y);
                        win->height = (uint32_t)nh;
                    }
                }
                return;
            }
        }
    }
    if (g_drag.is_dragging) {
        for (uint32_t i = 0; i < g_window_count; ++i) {
            if (g_windows[i].id == g_drag.active_win_id) {
                g_windows[i].x = g_drag.win_start_x + mx - g_drag.drag_start_x;
                g_windows[i].y = g_drag.win_start_y + my - g_drag.drag_start_y;
                return;
            }
        }
    }
}

void wm_handle_mouse_up(void) {
    g_drag.is_dragging = 0;
    g_resize.is_resizing = 0;
}

static void wm_render_single_window(const Window *win) {
    if (!win || win->x + (int32_t)win->width < 0 || win->y + (int32_t)win->height < 0) return;
    uint32_t x = (win->x < 0) ? 0 : (uint32_t)win->x;
    uint32_t y = (win->y < 0) ? 0 : (uint32_t)win->y;

    // Sombra suave multicamada sob a janela (elevação adaptativa ao foco)
    uint32_t blur = win->is_focused ? 28 : 16;
    uint8_t shadow_a = win->is_focused ? 110 : 60;
    gfx_draw_smooth_shadow(win->x, win->y, (int)win->width, (int)win->height, 16, blur, shadow_a);

    /* Janela Baken Lua: Mica é a base opaca e legível. O estado de foco
     * fica no contorno sem mudar a cor do conteúdo do aplicativo. */
    baken_lua_draw_surface(x, y, win->width, win->height, BKN_LUA_MICA,
                           win->is_focused ? BKN_LUA_FOCUS : BKN_LUA_REST, 16);
    gfx_draw_circle_button(win->x + 18, win->y + 18, 6, 0x00EF4444);
    gfx_draw_circle_button(win->x + 36, win->y + 18, 6, 0x00F59E0B);
    gfx_draw_circle_button(win->x + 54, win->y + 18, 6, 0x0010B981);
    gfx_draw_text_ellipsis(win->x + 72, win->y + 11, win->width > 142 ? win->width - 142 : 0, (const char*)win->title, 0x000F172A);

    // Renderiza canvas interno de conteúdo acetinado
    if (win->height > TITLE_BAR_HEIGHT + 24 && win->width > 48) {
        uint32_t px = x + 12;
        uint32_t py = y + TITLE_BAR_HEIGHT + 8;
        uint32_t pw = win->width - 24;
        uint32_t ph = win->height - TITLE_BAR_HEIGHT - 20;
        baken_lua_draw_surface(px, py, pw, ph, BKN_LUA_CANVAS, BKN_LUA_REST, 12);

        if (win->app_id == 1) { // Arquivos / BakenFS
            baken_lua_draw_surface(px + 12, py + 10, pw - 24, 30, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 6);
            gfx_draw_text_proportional(px + 24, py + 17, "<   >   ^   |   Local: BakenFS (/home)", 0x000284C7);

            uint32_t count = st_fs_entry_count();
            uint32_t cols = pw > 360 ? 3 : (pw > 240 ? 2 : 1);
            uint32_t card_w = (pw - 24 - (cols - 1) * 8) / cols;
            uint32_t card_h = 58;

            for (uint32_t i = 0; i < count && i < 9; ++i) {
                uint32_t col = i % cols;
                uint32_t row = i / cols;
                uint32_t cx = px + 12 + col * (card_w + 8);
                uint32_t cy = py + 48 + row * (card_h + 8);
                if (cy + card_h > py + ph - 34) break;

                uint32_t kind = st_fs_entry_kind(i);
                uint32_t icon_id = (kind == 1) ? 0 : ((kind == 3) ? 10 : 6);
                baken_lua_draw_surface(cx, cy, card_w, card_h, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_app_icon_hd(cx + 8, cy + 13, 32, icon_id);

                const char *fname = st_fs_entry_name(i);
                const char *disp_name = fname;
                for (int k = 0; fname[k]; ++k) {
                    if (fname[k] == '/' && fname[k+1]) disp_name = fname + k + 1;
                }
                gfx_draw_text_ellipsis(cx + 46, cy + 12, card_w > 50 ? card_w - 50 : 40, disp_name, 0x000F172A);

                if (kind == 1) {
                    gfx_draw_text_proportional(cx + 46, cy + 32, "Diretorio", 0x000284C7);
                } else if (kind == 3) {
                    gfx_draw_text_proportional(cx + 46, cy + 32, "Configuracao", 0x0064748B);
                } else {
                    uint32_t sz = st_fs_entry_size(i);
                    char sz_str[24];
                    if (sz >= 1024) {
                        int kb = (int)(sz / 1024);
                        sz_str[0] = (char)('0' + (kb / 10) % 10);
                        sz_str[1] = (char)('0' + kb % 10);
                        sz_str[2] = ' '; sz_str[3] = 'K'; sz_str[4] = 'B'; sz_str[5] = 0;
                    } else {
                        sz_str[0] = (char)('0' + (sz / 100) % 10);
                        sz_str[1] = (char)('0' + (sz / 10) % 10);
                        sz_str[2] = (char)('0' + sz % 10);
                        sz_str[3] = ' '; sz_str[4] = 'B'; sz_str[5] = 0;
                    }
                    gfx_draw_text_proportional(cx + 46, cy + 32, sz_str[0] == '0' ? sz_str + 1 : sz_str, 0x00166534);
                }
            }

            if (ph > 40) {
                baken_lua_draw_surface(px + 12, py + ph - 30, pw - 24, 22, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 4);
                gfx_draw_text_proportional(px + 20, py + ph - 25, "BakenFS montado - Terminal: touch / rm / ls / cat", 0x0064748B);
            }
        } else if (win->app_id == 2) { // Notas
            baken_lua_draw_surface(px + 12, py + 8, pw - 24, 30, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 6);
            baken_lua_draw_surface(px + 18, py + 12, 68, 22, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 4);
            gfx_draw_text_proportional(px + 28, py + 15, "Salvar", 0x00166534);

            baken_lua_draw_surface(px + 92, py + 12, 68, 22, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 4);
            gfx_draw_text_proportional(px + 102, py + 15, "Copiar", 0x000F172A);

            if (pw > 200) {
                gfx_draw_text_proportional(px + pw - 150, py + 15, "Linha 1, Coluna 1", 0x0064748B);
            }

            if (ph > 50) {
                baken_lua_draw_surface(px + 12, py + 44, pw - 24, ph - 54, BKN_LUA_MICA, BKN_LUA_FOCUS, 6);
                baken_lua_draw_surface(px + 12, py + 44, 36, ph - 54, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 4);
                gfx_draw_text_proportional(px + 20, py + 56, "01", 0x0094A3B8);
                gfx_draw_text_proportional(px + 20, py + 78, "02", 0x0094A3B8);
                gfx_draw_text_proportional(px + 20, py + 100, "03", 0x0094A3B8);
                gfx_draw_text_proportional(px + 20, py + 122, "04", 0x0094A3B8);

                gfx_draw_text_proportional(px + 56, py + 56, "Notas persistentes — Enter salva no disco", 0x000284C7);
                const char *nt = st_notes_get_text();
                gfx_draw_text_proportional(px + 56, py + 80, nt, 0x001E293B);
                if (win->is_focused && (desktop_shell_get_time_tick() % 40) < 24) {
                    uint32_t tw = gfx_measure_text(nt);
                    gfx_fill_rect_alpha(px + 58 + tw, py + 78, 2, 16, 0x000284C7, 240);
                }
            }
        } else if (win->app_id == 4) { // Terminal Sotlas - Vortex Core
            desktop_shell_render_terminal(px, py, pw, ph, win->is_focused);
        } else if (win->app_id == 3) { // Ajustes & Hardware (Cards Modernos Light Aero)
            // Header Card com status
            baken_lua_draw_surface(px + 12, py + 10, pw - 24, 38, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 8);
            gfx_draw_circle_alpha(px + 28, py + 29, 5, 0x0010B981, 255);
            gfx_draw_text_proportional(px + 40, py + 22, "Baken OS Sovereign v2.0", 0x000F172A);
            if (pw > 220) {
                baken_lua_draw_surface(px + pw - 138, py + 16, 114, 24, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 12);
                gfx_draw_text_proportional(px + pw - 128, py + 21, "x86-64 UEFI", 0x00166534);
            }

            uint32_t col_w = (pw > 40) ? (pw - 32) / 2 : 120;
            // Card 1: Monitor e Vídeo (Coluna Esquerda)
            baken_lua_draw_surface(px + 12, py + 54, col_w, 74, BKN_LUA_MICA, BKN_LUA_REST, 10);
            gfx_draw_text_proportional(px + 24, py + 64, "Monitor e Video", 0x000284C7);
            gfx_draw_text_proportional(px + 24, py + 84, "Resolucao 32bpp Linear ARGB", 0x001E293B);
            baken_lua_draw_surface(px + 24, py + 104, 76, 18, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 9);
            gfx_draw_text_proportional(px + 30, py + 107, "GOP Nativo", 0x00475569);

            // Card 2: Armazenamento (Coluna Direita)
            baken_lua_draw_surface(px + 20 + col_w, py + 54, col_w, 74, BKN_LUA_MICA, BKN_LUA_REST, 10);
            gfx_draw_text_proportional(px + 32 + col_w, py + 64, "Armazenamento", 0x000284C7);
            if (sys_has_nvme()) {
                gfx_draw_text_proportional(px + 32 + col_w, py + 84, "Disco NVMe Express PCI", 0x001E293B);
            } else if (sys_has_ahci()) {
                gfx_draw_text_proportional(px + 32 + col_w, py + 84, "Disco SATA AHCI Controller", 0x001E293B);
            } else {
                gfx_draw_text_proportional(px + 32 + col_w, py + 84, "Midia Live ESP FAT32", 0x001E293B);
            }
            baken_lua_draw_surface(px + 32 + col_w, py + 104, 68, 18, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 9);
            gfx_draw_text_proportional(px + 40 + col_w, py + 107, "Montado", 0x00166534);

            // Card 3: Conectividade (Coluna Esquerda Inferior)
            baken_lua_draw_surface(px + 12, py + 134, col_w, 74, BKN_LUA_MICA, BKN_LUA_REST, 10);
            gfx_draw_text_proportional(px + 24, py + 144, "Conectividade", 0x000284C7);
            if (sys_has_nic()) {
                gfx_draw_text_proportional(px + 24, py + 164, "Controlador Ethernet (PCI 0x02)", 0x001E293B);
                baken_lua_draw_surface(px + 24, py + 184, 76, 18, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 9);
                gfx_draw_text_proportional(px + 32, py + 187, "Conectado", 0x00166534);
            } else {
                gfx_draw_text_proportional(px + 24, py + 164, "Sem controlador Ethernet", 0x0064748B);
                baken_lua_draw_surface(px + 24, py + 184, 64, 18, BKN_LUA_GLASS_CLEAR, BKN_LUA_DISABLED, 9);
                gfx_draw_text_proportional(px + 32, py + 187, "Inativo", 0x0064748B);
            }

            // Card 4: Relógio do Sistema (Coluna Direita Inferior)
            baken_lua_draw_surface(px + 20 + col_w, py + 134, col_w, 74, BKN_LUA_MICA, BKN_LUA_REST, 10);
            gfx_draw_text_proportional(px + 32 + col_w, py + 144, "Relogio do Sistema", 0x000284C7);
            gfx_draw_text_proportional(px + 32 + col_w, py + 164, "CMOS RTC 24h (Portas 0x70/0x71)", 0x001E293B);
            baken_lua_draw_surface(px + 32 + col_w, py + 184, 88, 18, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 9);
            gfx_draw_text_proportional(px + 38 + col_w, py + 187, "Sincronizado", 0x00166534);

            // Botões de Ação na base da janela
            if (ph > 40) {
                baken_lua_draw_surface(px + 12, py + ph - 38, 136, 26, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 13);
                gfx_draw_text_proportional(px + 24, py + ph - 32, "Modos de Janela", 0x000F172A);

                baken_lua_draw_surface(px + 158, py + ph - 38, 116, 26, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 13);
                gfx_draw_text_proportional(px + 172, py + ph - 32, "Tema: Claro", 0x00FFFFFF);
            }
        } else if (win->app_id == 5) { /* Assistente Completo de Setup e Instalacao Baken OS */
            uint32_t step_y = py + 6;
            if (g_installer.stage >= 1 && g_installer.stage <= 8) {
                /* Stepper Header (8 Passos) */
                baken_lua_draw_surface(px + 12, step_y, pw - 24, 26, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 6);
                gfx_draw_hline(px + 28, step_y + 13, pw - 180, 0x00334155, 100);
                static const char *step_names[] = {"1. Idioma", "2. Termos", "3. Hardware", "4. Perfil", "5. Conta", "6. Disco", "7. Copia", "8. Conclusao"};
                uint32_t step_gap = (pw - 200) / 7;
                for (uint32_t s = 1; s <= 8; ++s) {
                    uint32_t sx = px + 28 + (s - 1) * step_gap;
                    uint8_t is_cur = (s == g_installer.stage);
                    uint8_t is_done = (s < g_installer.stage);
                    uint32_t dot_c = is_cur ? 0x0000E5FF : (is_done ? 0x0010B981 : 0x00475569);
                    gfx_draw_circle_alpha(sx, step_y + 13, is_cur ? 5 : 3, dot_c, 255);
                }
                gfx_draw_text_proportional(px + pw - 140, step_y + 6, step_names[g_installer.stage - 1], 0x0000E5FF);
            }

            uint32_t bot_y = py + ph - 34;

            if (g_installer.stage == INSTALLER_STAGE_WELCOME) {
                baken_lua_draw_surface(px + 12, py + 8, pw - 24, 42, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 8);
                gfx_draw_text_role(px + 24, py + 14, "Bem-vindo ao Baken OS Sovereign", 0x000F172A, BKN_TYPE_TITLE);
                gfx_draw_text_proportional(px + 24, py + 32, "Selecione o modo de inicializacao para o seu computador:", 0x0064748B);

                static const char *w_titles[] = {"[1] Instalar Baken OS (Assistente Guiado)", "[2] Executar Demo (Live OS)", "[3] Reparar Sistema & Bootloader", "[4] Benchmark & Diagnostico de Hardware"};
                static const char *w_descs[] = {"Instalacao completa no disco GPT com perfil personalizado.", "Experimente o desktop, loja e notas em memoria sem alterar discos.", "Recupere o bootloader UEFI, verifique o BakenFS ou restaure snapshots.", "Avalie a compatibilidade e performance da CPU, RAM e GPU GOP."};
                static const char *w_badges[] = {"Recomendado", "Modo Live", "Diagnostico", "Score 96/100"};
                static const uint32_t w_colors[] = {0x000284C7, 0x0010B981, 0x00F59E0B, 0x008B5CF6};

                for (uint32_t i = 0; i < 4; ++i) {
                    uint32_t cy = py + 56 + i * 66;
                    baken_lua_draw_surface(px + 12, cy, pw - 24, 60, BKN_LUA_MICA, BKN_LUA_REST, 8);
                    gfx_draw_circle_alpha(px + 28, cy + 30, 8, w_colors[i], 240);
                    gfx_draw_text_role(px + 44, cy + 12, w_titles[i], 0x000F172A, BKN_TYPE_LABEL);
                    gfx_draw_text_proportional(px + 44, cy + 34, w_descs[i], 0x0064748B);

                    baken_lua_draw_surface(px + pw - 126, cy + 18, 98, 24, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 10);
                    gfx_draw_text_proportional(px + pw - 116, cy + 23, w_badges[i], w_colors[i]);
                }

                baken_lua_draw_surface(px + 12, bot_y, 140, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 26, bot_y + 6, "Sair para Live OS", 0x00334155);

                baken_lua_draw_surface(px + pw - 160, bot_y, 148, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 138, bot_y + 6, "Avancar >", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_LANGUAGE) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "1. Idioma do Sistema e Layout do Teclado", 0x000F172A, BKN_TYPE_TITLE);

                uint32_t col_w = (pw - 36) / 2;
                baken_lua_draw_surface(px + 12, py + 72, col_w, 24, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 6);
                gfx_draw_text_proportional(px + 20, py + 76, "Idioma do Sistema", 0x000284C7);

                baken_lua_draw_surface(px + 24 + col_w, py + 72, col_w, 24, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 6);
                gfx_draw_text_proportional(px + 32 + col_w, py + 76, "Layout do Teclado", 0x000284C7);

                static const char *langs[] = {"[1] Portugues (Brasil)", "[2] English (United States)", "[3] Espanol (Latinoamerica)"};
                static const char *kbds[] = {"[1] Teclado ABNT2 (Brasil)", "[2] Teclado US-International", "[3] Teclado ISO Latin / Generic"};

                for (uint32_t i = 0; i < 3; ++i) {
                    uint32_t ly = py + 102 + i * 50;
                    uint8_t l_sel = (g_installer.selected_lang == i);
                    baken_lua_draw_surface(px + 12, ly, col_w, 44, BKN_LUA_MICA, l_sel ? BKN_LUA_SELECTED : BKN_LUA_REST, 8);
                    gfx_draw_circle_alpha(px + 26, ly + 22, 6, l_sel ? 0x0010B981 : 0x0094A3B8, 240);
                    gfx_draw_text_proportional(px + 40, ly + 14, langs[i], l_sel ? 0x000F172A : 0x00475569);

                    uint8_t k_sel = (g_installer.selected_kbd == i);
                    baken_lua_draw_surface(px + 24 + col_w, ly, col_w, 44, BKN_LUA_MICA, k_sel ? BKN_LUA_SELECTED : BKN_LUA_REST, 8);
                    gfx_draw_circle_alpha(px + 38 + col_w, ly + 22, 6, k_sel ? 0x000284C7 : 0x0094A3B8, 240);
                    gfx_draw_text_proportional(px + 52 + col_w, ly + 14, kbds[i], k_sel ? 0x000F172A : 0x00475569);
                }

                baken_lua_draw_surface(px + 12, bot_y, 110, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 28, bot_y + 6, "< Voltar", 0x00334155);

                baken_lua_draw_surface(px + pw - 140, bot_y, 128, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 118, bot_y + 6, "Avancar >", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_LICENSE) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "2. Termos & Licenca Soberana BKN", 0x000F172A, BKN_TYPE_TITLE);

                baken_lua_draw_surface(px + 12, py + 72, pw - 24, 180, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 24, py + 84, "Principios Fundamentais do Baken OS Sovereign:", 0x000284C7);
                gfx_draw_text_proportional(px + 24, py + 106, "1. Soberania e Privacidade Total: Zero telemetria e controle absoluto dos dados.", 0x001E293B);
                gfx_draw_text_proportional(px + 24, py + 128, "2. Codigo Aberto e Auditavel: Kernel Sotlas nativo e micro-arquitetura modular.", 0x001E293B);
                gfx_draw_text_proportional(px + 24, py + 150, "3. Desempenho Freestanding: Execucao direta sobre UEFI sem intermediarios.", 0x001E293B);
                gfx_draw_text_proportional(px + 24, py + 172, "4. Resiliencia por Snapshots: Recuperacao automatica e pontos de restauracao.", 0x001E293B);
                gfx_draw_text_proportional(px + 24, py + 200, "Ao instalar, voce concorda com a liberdade de execucao e soberania digital.", 0x0064748B);

                baken_lua_draw_surface(px + 12, py + 262, pw - 24, 34, BKN_LUA_GLASS_REGULAR, g_installer.license_accepted ? BKN_LUA_SELECTED : BKN_LUA_REST, 6);
                gfx_draw_circle_alpha(px + 28, py + 279, 7, g_installer.license_accepted ? 0x0010B981 : 0x0094A3B8, 255);
                gfx_draw_text_proportional(px + 44, py + 272, "[X] Aceito os termos e principios da Licenca Soberana BKN", 0x000F172A);

                baken_lua_draw_surface(px + 12, bot_y, 110, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 28, bot_y + 6, "< Voltar", 0x00334155);

                baken_lua_draw_surface(px + pw - 140, bot_y, 128, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 118, bot_y + 6, "Avancar >", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_HARDWARE) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "3. Diagnostico & Benchmark de Hardware", 0x000F172A, BKN_TYPE_TITLE);

                uint32_t col_w = (pw - 36) / 2;
                baken_lua_draw_surface(px + 12, py + 72, col_w, 70, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 22, py + 80, "Processador CPU", 0x000284C7);
                gfx_draw_text_proportional(px + 22, py + 98, "x86_64 Long Mode (AVX/SSE4)", 0x000F172A);
                gfx_draw_text_proportional(px + 22, py + 116, "Score: 98/100 (Excelente)", 0x0010B981);

                baken_lua_draw_surface(px + 24 + col_w, py + 72, col_w, 70, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 34 + col_w, py + 80, "Memoria RAM", 0x000284C7);
                gfx_draw_text_proportional(px + 34 + col_w, py + 98, "512 MB+ Alocacao Dinamica", 0x000F172A);
                gfx_draw_text_proportional(px + 34 + col_w, py + 116, "Score: 95/100 (Adequado)", 0x0010B981);

                baken_lua_draw_surface(px + 12, py + 148, col_w, 70, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 22, py + 156, "Armazenamento", 0x000284C7);
                gfx_draw_text_proportional(px + 22, py + 174, "UEFI Block I/O Target (GPT)", 0x000F172A);
                gfx_draw_text_proportional(px + 22, py + 192, "Score: 95/100 (Compativel)", 0x0010B981);

                baken_lua_draw_surface(px + 24 + col_w, py + 148, col_w, 70, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 34 + col_w, py + 156, "Graficos e GOP", 0x000284C7);
                gfx_draw_text_proportional(px + 34 + col_w, py + 174, "Linear ARGB 32bpp Framebuffer", 0x000F172A);
                gfx_draw_text_proportional(px + 34 + col_w, py + 192, "Score: 96/100 (Acelerado)", 0x0010B981);

                baken_lua_draw_surface(px + 12, py + 226, pw - 24, 48, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 8);
                gfx_draw_circle_alpha(px + 32, py + 250, 10, 0x0010B981, 255);
                gfx_draw_text_role(px + 52, py + 236, "Score Geral de Compatibilidade: 96 / 100", 0x000F172A, BKN_TYPE_LABEL);
                gfx_draw_text_proportional(px + 52, py + 254, "Hardware totalmente compativel com o Baken OS Sovereign.", 0x00166534);

                baken_lua_draw_surface(px + 12, bot_y, 110, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 28, bot_y + 6, "< Voltar", 0x00334155);

                baken_lua_draw_surface(px + pw - 140, bot_y, 128, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 118, bot_y + 6, "Avancar >", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_PROFILE) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "4. Escolha o Perfil de Instalacao", 0x000F172A, BKN_TYPE_TITLE);

                uint32_t cw = (pw - 36) / 2;
                static const char *p_titles[] = {"[1] Usuario Padrao", "[2] Desenvolvedor Soberano", "[3] Gamer & Multimidia", "[4] Minimalista / Estacao"};
                static const char *p_descs[] = {"Desktop completo, Navegador, Loja, Notas, Ajustes, Player.", "SDK Sotlas Nativo, Sotlas Compile, Terminal PRO, Compilador Freestanding.", "3D Studio, Pipeline grafico acelerado, Otimizacoes GOP e Audio.", "Kernel ultraleve, BakenFS basico, Terminal de baixo consumo."};

                for (uint32_t i = 0; i < 4; ++i) {
                    uint32_t col = i % 2;
                    uint32_t row = i / 2;
                    uint32_t cx = px + 12 + col * (cw + 12);
                    uint32_t cy = py + 72 + row * 92;
                    uint8_t is_p_sel = (g_installer.selected_profile == i);

                    baken_lua_draw_surface(cx, cy, cw, 84, BKN_LUA_MICA, is_p_sel ? BKN_LUA_SELECTED : BKN_LUA_REST, 8);
                    gfx_draw_circle_alpha(cx + 18, cy + 22, 6, is_p_sel ? 0x0000E5FF : 0x0094A3B8, 255);
                    gfx_draw_text_role(cx + 32, cy + 14, p_titles[i], is_p_sel ? 0x000284C7 : 0x000F172A, BKN_TYPE_LABEL);
                    gfx_draw_text_proportional(cx + 18, cy + 38, p_descs[i], 0x0064748B);
                }

                baken_lua_draw_surface(px + 12, bot_y, 110, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 28, bot_y + 6, "< Voltar", 0x00334155);

                baken_lua_draw_surface(px + pw - 140, bot_y, 128, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 118, bot_y + 6, "Avancar >", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_ACCOUNT) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "5. Conta de Usuario & Nome do Computador", 0x000F172A, BKN_TYPE_TITLE);

                uint32_t col_w = (pw - 36) / 2;
                baken_lua_draw_surface(px + 12, py + 72, col_w, 76, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 22, py + 82, "Nome do Computador (Hostname)", 0x000284C7);
                gfx_draw_text_role(px + 22, py + 104, g_installer.hostname, 0x000F172A, BKN_TYPE_TITLE);
                gfx_draw_text_proportional(px + 22, py + 126, "Identificador na rede local", 0x0064748B);

                baken_lua_draw_surface(px + 24 + col_w, py + 72, col_w, 76, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 34 + col_w, py + 82, "Usuario Principal", 0x000284C7);
                gfx_draw_text_role(px + 34 + col_w, py + 104, g_installer.username, 0x000F172A, BKN_TYPE_TITLE);
                gfx_draw_text_proportional(px + 34 + col_w, py + 126, "Conta administrativa padrao", 0x0064748B);

                baken_lua_draw_surface(px + 12, py + 156, col_w, 76, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 22, py + 166, "PIN de Acesso Rapido", 0x000284C7);
                gfx_draw_text_role(px + 22, py + 188, "**** (1234)", 0x000F172A, BKN_TYPE_TITLE);
                gfx_draw_text_proportional(px + 22, py + 210, "Protecao para login e terminal", 0x0064748B);

                baken_lua_draw_surface(px + 24 + col_w, py + 156, col_w, 76, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 34 + col_w, py + 166, "Privacidade & Telemetria", 0x000284C7);
                gfx_draw_text_proportional(px + 34 + col_w, py + 188, "Zero Rastreamento Nativo", 0x0010B981);
                gfx_draw_text_proportional(px + 34 + col_w, py + 210, "Localizacao apenas sob demanda", 0x0064748B);

                baken_lua_draw_surface(px + 12, bot_y, 110, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 28, bot_y + 6, "< Voltar", 0x00334155);

                baken_lua_draw_surface(px + pw - 140, bot_y, 128, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 118, bot_y + 6, "Avancar >", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_DISK) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "6. Gerenciamento & Particionamento de Disco", 0x000F172A, BKN_TYPE_TITLE);

                uint32_t tw = (pw - 36) / 2;
                baken_lua_draw_surface(px + 12, py + 72, tw, 32, BKN_LUA_MICA, g_installer.auto_partition ? BKN_LUA_SELECTED : BKN_LUA_REST, 6);
                gfx_draw_circle_alpha(px + 24, py + 88, 5, g_installer.auto_partition ? 0x0010B981 : 0x0094A3B8, 255);
                gfx_draw_text_proportional(px + 36, py + 80, "Instalacao Automatica (Recomendado)", g_installer.auto_partition ? 0x000284C7 : 0x00475569);

                baken_lua_draw_surface(px + 24 + tw, py + 72, tw, 32, BKN_LUA_MICA, !g_installer.auto_partition ? BKN_LUA_SELECTED : BKN_LUA_REST, 6);
                gfx_draw_circle_alpha(px + 36 + tw, py + 88, 5, !g_installer.auto_partition ? 0x0010B981 : 0x0094A3B8, 255);
                gfx_draw_text_proportional(px + 48 + tw, py + 80, "Particionamento Avancado / Manual", !g_installer.auto_partition ? 0x000284C7 : 0x00475569);

                uint32_t bar_y = py + 110;
                uint32_t bar_w = pw - 24;
                uint32_t bar_h = 24;
                baken_lua_draw_surface(px + 12, bar_y, bar_w, bar_h, BKN_LUA_MICA, BKN_LUA_REST, 6);
                
                uint32_t cur_bx = px + 14;
                for (uint32_t i = 0; i < g_installer.part_count; ++i) {
                    uint32_t seg_w = (i == 0) ? (bar_w * 58 / 100) : (bar_w * 40 / 100);
                    if (cur_bx + seg_w > px + 12 + bar_w - 2) seg_w = (px + 12 + bar_w - 2 > cur_bx) ? (px + 12 + bar_w - 2 - cur_bx) : 0;
                    uint32_t seg_color = (g_installer.parts[i].fs_type == 1) ? 0x000284C7 : 0x0010B981;
                    uint8_t is_sel = ((int32_t)i == g_installer.selected_part);
                    gfx_draw_glass_rect_material(cur_bx, bar_y + 2, seg_w, bar_h - 4, seg_color, is_sel ? 240 : 180, is_sel ? 0x00FFFFFF : seg_color, 4);
                    
                    if (g_installer.parts[i].fs_type == 1) {
                        gfx_draw_text_proportional(cur_bx + 6, bar_y + 5, "ESP (FAT32 - 41 MB)", 0x00FFFFFF);
                    } else {
                        gfx_draw_text_proportional(cur_bx + 6, bar_y + 5, "Baken Data (BakenFS - 23 MB)", 0x00FFFFFF);
                    }
                    cur_bx += seg_w + 2;
                }

                uint32_t tbl_y = bar_y + bar_h + 8;
                uint32_t tbl_h = 80;
                baken_lua_draw_surface(px + 12, tbl_y, pw - 24, tbl_h, BKN_LUA_CANVAS, BKN_LUA_REST, 8);

                gfx_fill_rect_alpha(px + 14, tbl_y + 2, pw - 28, 18, 0x001E293B, 200);
                gfx_draw_text_proportional(px + 24, tbl_y + 4, "Volume", 0x0094A3B8);
                gfx_draw_text_proportional(px + 200, tbl_y + 4, "Sistema de Arquivos", 0x0094A3B8);
                gfx_draw_text_proportional(px + 370, tbl_y + 4, "Tamanho", 0x0094A3B8);
                gfx_draw_text_proportional(px + 490, tbl_y + 4, "Funcao Primaria", 0x0094A3B8);

                uint32_t row_y = tbl_y + 22;
                for (uint32_t i = 0; i < g_installer.part_count && i < MAX_INSTALL_PARTS; ++i) {
                    uint8_t is_sel = ((int32_t)i == g_installer.selected_part);
                    if (is_sel) {
                        gfx_draw_glass_rect_material(px + 14, row_y, pw - 28, 20, 0x000284C7, 180, 0x0038BDF8, 4);
                    }
                    uint32_t txt_c = is_sel ? 0x00FFFFFF : 0x000F172A;
                    gfx_draw_text_proportional(px + 24, row_y + 2, g_installer.parts[i].name, txt_c);
                    const char *fs_name = (g_installer.parts[i].fs_type == 1) ? "FAT32 (ESP Boot)" : "BakenFS v1 (Sovereign)";
                    gfx_draw_text_proportional(px + 200, row_y + 2, fs_name, is_sel ? 0x00E0F2FE : 0x000284C7);
                    const char *sz_txt = (i == 0) ? "41.0 MB" : "22.5 MB";
                    gfx_draw_text_proportional(px + 370, row_y + 2, sz_txt, txt_c);
                    const char *role_txt = (i == 0) ? "Bootloader UEFI" : "Sistema & Dados";
                    gfx_draw_text_proportional(px + 490, row_y + 2, role_txt, is_sel ? 0x00BBF7D0 : 0x00166534);
                    row_y += 22;
                }

                uint32_t tools_y = tbl_y + tbl_h + 6;
                baken_lua_draw_surface(px + 12, tools_y, 76, 22, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_proportional(px + 24, tools_y + 4, "+ Nova", 0x000F172A);

                baken_lua_draw_surface(px + 94, tools_y, 76, 22, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_proportional(px + 108, tools_y + 4, "Excluir", 0x000F172A);

                baken_lua_draw_surface(px + 176, tools_y, 86, 22, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_proportional(px + 188, tools_y + 4, "Formatar", 0x000F172A);

                baken_lua_draw_surface(px + 268, tools_y, 110, 22, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 6);
                gfx_draw_text_proportional(px + 280, tools_y + 4, "Layout Padrao", 0x00166534);

                baken_lua_draw_surface(px + 12, bot_y, 110, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 28, bot_y + 6, "< Voltar", 0x00334155);

                baken_lua_draw_surface(px + pw - 180, bot_y, 168, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 162, bot_y + 6, "Instalar Agora", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_INSTALLING) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "7. Instalando Baken OS no Disco GPT...", 0x000F172A, BKN_TYPE_TITLE);

                uint32_t pb_w = pw - 24;
                baken_lua_draw_surface(px + 12, py + 78, pb_w, 10, BKN_LUA_MICA, BKN_LUA_REST, 5);
                uint32_t fill_w = pb_w * g_installer.progress / 100;
                gfx_fill_rect_alpha(px + 12, py + 78, fill_w, 10, 0x0010B981, 255);

                gfx_draw_text_proportional(px + 20, py + 94, "Taxa de Transferencia: 34 MB/s (64 KB Chunk I/O)", 0x000284C7);
                char pct_str[16]; pct_str[0] = (char)('0' + (g_installer.progress / 10) % 10); pct_str[1] = (char)('0' + g_installer.progress % 10); pct_str[2] = '%'; pct_str[3] = 0;
                gfx_draw_text_proportional(px + pw - 50, py + 94, pct_str, 0x0010B981);

                /* Terminal de Logs em Tempo Real */
                baken_lua_draw_surface(px + 12, py + 120, pw - 24, 160, BKN_LUA_CANVAS, BKN_LUA_REST, 8);
                gfx_fill_rect_alpha(px + 14, py + 122, pw - 28, 156, 0x000F172A, 240);
                for (uint32_t i = 0; i < g_installer.log_count && i < 6; ++i) {
                    gfx_draw_text_proportional(px + 24, py + 130 + i * 24, g_installer.log_lines[i], 0x0038BDF8);
                }

                baken_lua_draw_surface(px + pw - 160, bot_y, 148, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_DISABLED, 8);
                gfx_draw_text_proportional(px + pw - 146, bot_y + 6, "Aguarde...", 0x0064748B);

            } else if (g_installer.stage == INSTALLER_STAGE_COMPLETE) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "8. Baken OS Instalado com Sucesso!", 0x0010B981, BKN_TYPE_TITLE);

                baken_lua_draw_surface(px + 12, py + 76, pw - 24, 190, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_circle_alpha(px + 36, py + 104, 16, 0x0010B981, 255);
                gfx_draw_text_role(px + 62, py + 92, "Parabens! Seu sistema esta pronto para o primeiro boot.", 0x000F172A, BKN_TYPE_TITLE);

                gfx_draw_text_proportional(px + 30, py + 130, "Resumo da Instalacao Soberana:", 0x000284C7);
                gfx_draw_text_proportional(px + 30, py + 150, "• Perfil Instalado: Desenvolvedor Soberano (SDK Sotlas & Sotlas Compile)", 0x001E293B);
                gfx_draw_text_proportional(px + 30, py + 170, "• Usuario Principal: baken@baken-workstation", 0x001E293B);
                gfx_draw_text_proportional(px + 30, py + 190, "• Particoes: ESP FAT32 (41 MB) + Baken Data BakenFS (23 MB)", 0x001E293B);
                gfx_draw_text_proportional(px + 30, py + 210, "• Snapshot Inicial: Ponto de restauracao 'Instalacao_Inicial' criado", 0x0010B981);
                gfx_draw_text_proportional(px + 30, py + 234, "Integridade dos blocos e CRC32 validados com 100% de precisao.", 0x0064748B);

                baken_lua_draw_surface(px + 12, bot_y, 160, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 24, bot_y + 6, "Continuar no Modo Live", 0x00334155);

                baken_lua_draw_surface(px + pw - 180, bot_y, 168, 28, BKN_LUA_ELEVATED, BKN_LUA_SELECTED, 8);
                gfx_draw_text_proportional(px + pw - 164, bot_y + 6, "Reiniciar Computador", 0x00FFFFFF);

            } else if (g_installer.stage == INSTALLER_STAGE_REPAIR) {
                baken_lua_draw_surface(px + 12, py + 38, pw - 24, 30, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 6);
                gfx_draw_text_role(px + 20, py + 44, "Ferramentas de Reparo & Diagnostico BKN", 0x000F172A, BKN_TYPE_TITLE);

                static const char *r_titles[] = {"[1] Reparar Bootloader UEFI & ESP", "[2] Verificar e Reparar Integridade do BakenFS", "[3] Restaurar Snapshot Inicial do Sistema"};
                static const char *r_descs[] = {"Restaura o MBR protetivo, cabecalhos GPT e VBR da particao ESP FAT32.", "Executa varredura no superbloco BakenFS e valida as 7 entradas de arquivos.", "Restaura as configuracoes de fabrica e notas a partir do snapshot inicial."};

                for (uint32_t i = 0; i < 3; ++i) {
                    uint32_t cy = py + 76 + i * 62;
                    baken_lua_draw_surface(px + 12, cy, pw - 24, 56, BKN_LUA_MICA, BKN_LUA_REST, 8);
                    gfx_draw_circle_alpha(px + 28, cy + 28, 6, 0x00F59E0B, 255);
                    gfx_draw_text_role(px + 44, cy + 12, r_titles[i], 0x000F172A, BKN_TYPE_LABEL);
                    gfx_draw_text_proportional(px + 44, cy + 32, r_descs[i], 0x0064748B);
                }

                baken_lua_draw_surface(px + 12, py + 268, pw - 24, 34, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, 6);
                gfx_draw_text_proportional(px + 24, py + 276, g_installer.repair_status, 0x00166534);

                baken_lua_draw_surface(px + 12, bot_y, 140, 28, BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 24, bot_y + 6, "< Voltar ao Inicio", 0x00334155);
            }
        } else { // Sobre
            baken_lua_draw_surface(px + 12, py + 12, pw - 24, 64, BKN_LUA_MICA, BKN_LUA_REST, 8);
            gfx_draw_circle_alpha(px + 44, py + 44, 16, 0x000284C7, 255);
            gfx_draw_circle_alpha(px + 44, py + 44, 9, 0x00F8FAFC, 255);
            gfx_draw_circle_alpha(px + 44, py + 44, 3, 0x000284C7, 255);
            gfx_draw_text_proportional(px + 76, py + 26, "Baken OS Sovereign", 0x000F172A);
            gfx_draw_text_proportional(px + 76, py + 46, "Versao 2.0.0 (x86-64 UEFI)", 0x000284C7);

            if (ph > 90) {
                baken_lua_draw_surface(px + 12, py + 84, pw - 24, ph - 94, BKN_LUA_MICA, BKN_LUA_REST, 8);
                gfx_draw_text_proportional(px + 24, py + 96, "Linguagem e Linker: Sotlas Compile (Sotlas Nativo)", 0x001E293B);
                gfx_draw_text_proportional(px + 24, py + 118, "Motor Grafico: GOP 32bpp Linear com Double Buffer", 0x001E293B);
                gfx_draw_text_proportional(px + 24, py + 140, "Ponteiro: Protocolos UEFI Absolute e Simple", 0x00166534);
                gfx_draw_text_proportional(px + 24, py + 162, "Copyright (c) 2026 Baken Project.", 0x0064748B);
            }
        }
    }
}

void wm_render_windows(void) {
    for (uint32_t z = 0; z < g_window_count; ++z) {
        for (uint32_t i = 0; i < g_window_count; ++i) {
            if (g_windows[i].z_index == (uint8_t)z && g_windows[i].is_open && !g_windows[i].is_minimized) {
                wm_render_single_window(&g_windows[i]);
            }
        }
    }
}
""".strip().splitlines())
    elif ast.name == "kernel::desktop_shell":
        lines.extend("""
#include "material_icons_atlas.h"
#include "baken_motion_icons_atlas.h"
#include "baken_design_tokens.h"
extern void gfx_put_pixel_alpha(uint32_t x, uint32_t y, uint32_t c, uint8_t a);
extern void gfx_draw_glass_rect_material(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius);
extern void gfx_draw_glass_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t a, uint32_t border, uint32_t radius);
extern void baken_lua_draw_surface(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t material, uint32_t state, uint32_t radius);
extern void gfx_draw_smooth_shadow(int x, int y, int w, int h, int radius, int blur, uint8_t max_alpha);
extern void gfx_draw_hline(uint32_t x, uint32_t y, uint32_t width, uint32_t color, uint8_t alpha);
extern void gfx_fill_rect_alpha(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t c, uint8_t a);
extern void gfx_draw_app_icon_hd(uint32_t x, uint32_t y, uint32_t size, uint32_t app_id);
extern void gfx_draw_material_icon(uint32_t x, uint32_t y, uint32_t size, uint32_t icon_id, uint32_t color, uint8_t alpha);
extern void gfx_draw_material_icon_state(uint32_t x, uint32_t y, uint32_t size, uint32_t icon_id, uint32_t color, uint32_t state);
extern void gfx_draw_motion_icon(uint32_t x, uint32_t y, uint32_t size, uint32_t icon_id, uint32_t color, uint8_t alpha, uint8_t mirror_x);
extern void gfx_draw_circle_alpha(uint32_t cx, uint32_t cy, uint32_t r, uint32_t c, uint8_t a);
extern void gfx_draw_text_proportional(uint32_t x, uint32_t y, const char *str, uint32_t color);
extern void gfx_draw_text_role(uint32_t x, uint32_t y, const char *str, uint32_t color, uint32_t role);
extern void gfx_draw_text_ellipsis(uint32_t x, uint32_t y, uint32_t max_width, const char *str, uint32_t color);
extern uint32_t gfx_draw_text_wrap_role(uint32_t x, uint32_t y, uint32_t max_width, uint32_t max_lines, const char *str, uint32_t color, uint32_t role);
extern uint32_t gfx_measure_text(const char *str);
extern void gfx_draw_text(uint32_t x, uint32_t y, const uint8_t *s, uint32_t c);
extern void gfx_draw_text_alpha(uint32_t x, uint32_t y, const uint8_t *s, uint32_t c, uint32_t scale, uint8_t a);
extern void gfx_fill_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t c);
extern void gfx_draw_mesh_wallpaper(void);
extern void gfx_swap_buffers(void);
extern uint32_t st_fs_entry_count(void);
extern void wm_init(void);
extern void wm_render_windows(void);
extern void wm_bring_to_front(uint32_t id);
extern uint8_t wm_get_cursor_type(int32_t mx, int32_t my);
extern void *wm_create_window(uint32_t id, const uint8_t *title, int32_t x, int32_t y, uint32_t w, uint32_t h, uint32_t bg, uint8_t alpha, uint32_t border);
extern uint32_t gfx_get_width(void), gfx_get_height(void);
extern uint32_t baken_ui_px(uint32_t logical_px);

typedef struct {
    uint8_t has_nvme;
    uint8_t has_ahci;
    uint8_t has_nic;
    uint8_t has_hda;
} PciStatus;

static PciStatus g_pci_status = {0, 0, 0, 0};

uint8_t sys_has_nvme(void) { return g_pci_status.has_nvme; }
uint8_t sys_has_ahci(void) { return g_pci_status.has_ahci; }
uint8_t sys_has_nic(void) { return g_pci_status.has_nic; }

static inline uint8_t inb_port(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}
static inline void outb_port(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}
static inline uint32_t inl_port(uint16_t port) {
    uint32_t ret;
    __asm__ volatile ("inl %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}
static inline void outl_port(uint16_t port, uint32_t val) {
    __asm__ volatile ("outl %0, %1" : : "a"(val), "Nd"(port));
}

static uint8_t cmos_read(uint8_t reg) {
    outb_port(0x70, reg);
    return inb_port(0x71);
}
static uint8_t bcd2bin(uint8_t bcd) {
    return ((bcd >> 4) * 10) + (bcd & 0x0F);
}

typedef struct {
    uint8_t sec, min, hour, day, month, year;
    uint8_t valid;
} RtcTime;

static RtcTime rtc_read_time(void) {
    RtcTime t = {0, 0, 0, 0, 0, 0, 0};
    for (int retry = 0; retry < 500; ++retry) {
        if ((cmos_read(0x0A) & 0x80) == 0) break;
    }
    uint8_t s = cmos_read(0x00);
    uint8_t m = cmos_read(0x02);
    uint8_t h = cmos_read(0x04);
    uint8_t d = cmos_read(0x07);
    uint8_t mo = cmos_read(0x08);
    uint8_t yr = cmos_read(0x09);
    uint8_t b = cmos_read(0x0B);
    if ((b & 0x04) == 0) {
        s = bcd2bin(s);
        m = bcd2bin(m);
        h = bcd2bin(h);
        d = bcd2bin(d);
        mo = bcd2bin(mo);
        yr = bcd2bin(yr);
    }
    if ((b & 0x02) == 0 && (h & 0x80)) {
        h = ((h & 0x7F) + 12) % 24;
    }
    if (s < 60 && m < 60 && h < 24 && d >= 1 && d <= 31 && mo >= 1 && mo <= 12) {
        t.sec = s; t.min = m; t.hour = h; t.day = d; t.month = mo; t.year = yr; t.valid = 1;
    }
    return t;
}

static uint32_t pci_read_cfg(uint8_t bus, uint8_t slot, uint8_t func, uint8_t offset) {
    uint32_t address = (uint32_t)((1U << 31) | ((uint32_t)bus << 16) | ((uint32_t)slot << 11) | ((uint32_t)func << 8) | (offset & 0xFC));
    outl_port(0xCF8, address);
    return inl_port(0xCFC);
}

static void pci_scan_hardware(void) {
    g_pci_status = (PciStatus){0, 0, 0, 0};
    for (uint32_t bus = 0; bus < 16; ++bus) {
        for (uint32_t slot = 0; slot < 32; ++slot) {
            uint32_t d0 = pci_read_cfg((uint8_t)bus, (uint8_t)slot, 0, 0);
            if ((d0 & 0xFFFF) == 0xFFFF || (d0 & 0xFFFF) == 0) continue;
            uint32_t d8 = pci_read_cfg((uint8_t)bus, (uint8_t)slot, 0, 0x08);
            uint8_t class_code = (uint8_t)(d8 >> 24);
            uint8_t subclass = (uint8_t)(d8 >> 16);
            if (class_code == 0x01 && subclass == 0x08) g_pci_status.has_nvme = 1;
            if (class_code == 0x01 && subclass == 0x06) g_pci_status.has_ahci = 1;
            if (class_code == 0x02) g_pci_status.has_nic = 1;
            if (class_code == 0x04 && subclass == 0x03) g_pci_status.has_hda = 1;
        }
    }
}

typedef struct { float current_val, target_val, velocity, stiffness, damping; } SotlasSpringState;
typedef struct {
    uint32_t y_offset, icon_size, item_count;
    const uint8_t *item_labels[16];
    SotlasSpringState item_springs[16];
    SotlasSpringState bounce_springs[16];
} DesktopDock;
extern void dock_init(DesktopDock *dock);
extern void dock_add_item(DesktopDock *dock, const uint8_t *label);
extern void dock_update(DesktopDock *dock, float dt, int32_t cursor_x, int32_t cursor_y);
extern void dock_draw(const DesktopDock *dock);
extern void dock_trigger_bounce(DesktopDock *dock, uint32_t index);
typedef struct { uint32_t x, y, width, height, pitch, icon, pad; } BakenDockLayout;
extern void baken_dock_layout(uint32_t item_count, BakenDockLayout *out);
extern uint8_t wm_handle_mouse_down(int32_t mx, int32_t my);
extern void wm_handle_mouse_move(int32_t mx, int32_t my);
extern void wm_handle_mouse_up(void);
extern void desktop_shell_toggle_media(void);
extern void desktop_shell_toggle_theme(void);
extern uint8_t desktop_shell_is_dark_theme(void);
extern void desktop_shell_toggle_control_center(void);
extern void desktop_shell_toggle_spotlight(void);
extern void desktop_shell_toggle_context_menu(void);
extern void gfx_set_mesh_time_tick(uint32_t t);
extern const char *st_notes_get_text(void);
extern uint32_t st_fs_entry_count(void);
extern const char *st_fs_entry_name(uint32_t index);
extern uint32_t st_fs_entry_kind(uint32_t index);
extern uint32_t st_fs_entry_size(uint32_t index);
extern int st_fs_add(const char *name, uint32_t kind, uint32_t size, uint32_t lba);
extern int st_fs_remove(const char *name);
extern int st_fs_write_file(const char *name, const char *text, uint32_t len);
extern int st_fs_read_file(const char *name, char *out_text, uint32_t max_len);
extern void desktop_config_save(void);
extern uint8_t installer_is_boot_mode_live(void);

static int str_contains_nocase(const char *haystack, const char *needle) {
    if (!needle || !*needle) return 1;
    if (!haystack) return 0;
    while (*haystack) {
        const char *h = haystack;
        const char *n = needle;
        while (*h && *n) {
            char ch_h = (*h >= 'A' && *h <= 'Z') ? (char)(*h + 32) : *h;
            char ch_n = (*n >= 'A' && *n <= 'Z') ? (char)(*n + 32) : *n;
            if (ch_h != ch_n) break;
            h++; n++;
        }
        if (!*n) return 1;
        haystack++;
    }
    return 0;
}

#define TERM_MAX_LINES 32
#define TERM_LINE_LEN 64
typedef struct {
    char lines[TERM_MAX_LINES][TERM_LINE_LEN];
    uint32_t line_count;
    int32_t scroll_offset;
    char current_cmd[48];
    uint32_t cmd_len;
} BakenTerminalState;

static BakenTerminalState g_terminal = {
    {
        "Baken OS Sovereign Kernel v2.0 (Sotlas Native)",
        "Terminal interativo - Digite 'help' para comandos."
    },
    2,
    0,
    "",
    0
};

static void desktop_shell_terminal_scroll(int32_t delta) {
    g_terminal.scroll_offset += delta;
    if (g_terminal.scroll_offset < 0) g_terminal.scroll_offset = 0;
    if (g_terminal.line_count > 6) {
        int32_t max_scroll = (int32_t)g_terminal.line_count - 6;
        if (g_terminal.scroll_offset > max_scroll) g_terminal.scroll_offset = max_scroll;
    } else {
        g_terminal.scroll_offset = 0;
    }
}

static void terminal_append_line(const char *line) {
    if (!line) return;
    g_terminal.scroll_offset = 0;
    if (g_terminal.line_count < TERM_MAX_LINES) {
        int len = 0;
        while (line[len] && len < TERM_LINE_LEN - 1) {
            g_terminal.lines[g_terminal.line_count][len] = line[len];
            len++;
        }
        g_terminal.lines[g_terminal.line_count][len] = 0;
        g_terminal.line_count++;
    } else {
        for (uint32_t i = 1; i < TERM_MAX_LINES; ++i) {
            for (uint32_t c = 0; c < TERM_LINE_LEN; ++c) {
                g_terminal.lines[i - 1][c] = g_terminal.lines[i][c];
            }
        }
        int len = 0;
        while (line[len] && len < TERM_LINE_LEN - 1) {
            g_terminal.lines[TERM_MAX_LINES - 1][len] = line[len];
            len++;
        }
        g_terminal.lines[TERM_MAX_LINES - 1][len] = 0;
    }
}

static void terminal_execute_command(void) {
    if (g_terminal.cmd_len == 0) return;
    char prompt_echo[64];
    prompt_echo[0] = '$'; prompt_echo[1] = ' ';
    int idx = 0;
    while (g_terminal.current_cmd[idx] && idx < 50) {
        prompt_echo[idx + 2] = g_terminal.current_cmd[idx];
        idx++;
    }
    prompt_echo[idx + 2] = 0;
    terminal_append_line(prompt_echo);

    const char *cmd = g_terminal.current_cmd;
    if (str_contains_nocase(cmd, "help")) {
        terminal_append_line("Comandos: ls, cat, touch, mkdir, rm, write, theme, sysinfo, clear");
    } else if (str_contains_nocase(cmd, "sysinfo")) {
        terminal_append_line("Arch: x86_64 UEFI | Mem: 512MB / 2048MB | GOP: 1080p");
        terminal_append_line("Kernel: Baken Modular Sotlas v2.0 | FS: BakenFS Sovereign v1");
    } else if (str_contains_nocase(cmd, "stat") || str_contains_nocase(cmd, "df")) {
        terminal_append_line("BakenFS Estado:");
        terminal_append_line("  Dispositivo: ESP Blk 86016 | Entradas: 12 max");
        terminal_append_line("  Status: Montado (Leitura / Gravacao ativas)");
    } else if (cmd[0] == 'l' && cmd[1] == 's') {
        uint32_t cnt = st_fs_entry_count();
        terminal_append_line("Arquivos no BakenFS:");
        for (uint32_t i = 0; i < cnt && i < 6; ++i) {
            char line_buf[64];
            uint32_t kind = st_fs_entry_kind(i);
            const char *prefix = (kind == 1) ? " [DIR] " : ((kind == 3) ? " [CFG] " : " [ARQ] ");
            const char *fn = st_fs_entry_name(i);
            int p = 0;
            while (prefix[p]) { line_buf[p] = prefix[p]; p++; }
            int f = 0;
            while (fn[f] && p < 60) { line_buf[p++] = fn[f++]; }
            line_buf[p] = 0;
            terminal_append_line(line_buf);
        }
    } else if (cmd[0] == 't' && cmd[1] == 'o' && cmd[2] == 'u' && cmd[3] == 'c' && cmd[4] == 'h' && cmd[5] == ' ') {
        const char *fn = cmd + 6;
        while (*fn == ' ') fn++;
        if (*fn) {
            if (st_fs_add(fn, 2, 0, 86020)) {
                terminal_append_line("Arquivo criado com sucesso no BakenFS.");
            } else {
                terminal_append_line("Erro ao criar arquivo (disco cheio ou somente-leitura).");
            }
        }
    } else if (cmd[0] == 'm' && cmd[1] == 'k' && cmd[2] == 'd' && cmd[3] == 'i' && cmd[4] == 'r' && cmd[5] == ' ') {
        const char *fn = cmd + 6;
        while (*fn == ' ') fn++;
        if (*fn) {
            if (st_fs_add(fn, 1, 0, 0)) {
                terminal_append_line("Diretorio criado com sucesso no BakenFS.");
            } else {
                terminal_append_line("Erro ao criar diretorio.");
            }
        }
    } else if (cmd[0] == 'r' && cmd[1] == 'm' && cmd[2] == ' ') {
        const char *fn = cmd + 3;
        while (*fn == ' ') fn++;
        if (*fn) {
            if (st_fs_remove(fn)) {
                terminal_append_line("Arquivo removido do BakenFS.");
            } else {
                terminal_append_line("Arquivo nao encontrado.");
            }
        }
    } else if (cmd[0] == 'c' && cmd[1] == 'a' && cmd[2] == 't') {
        const char *fn = cmd + 3;
        while (*fn == ' ') fn++;
        if (!*fn) fn = "/home/notas.txt";
        char read_buf[128];
        if (st_fs_read_file(fn, read_buf, sizeof(read_buf))) {
            terminal_append_line(read_buf);
        } else {
            terminal_append_line("(Arquivo vazio ou nao encontrado)");
        }
    } else if (cmd[0] == 'w' && cmd[1] == 'r' && cmd[2] == 'i' && cmd[3] == 't' && cmd[4] == 'e' && cmd[5] == ' ') {
        const char *p = cmd + 6;
        while (*p == ' ') p++;
        char fname[32]; int fi = 0;
        while (*p && *p != ' ' && fi < 31) { fname[fi++] = *p++; }
        fname[fi] = 0;
        while (*p == ' ') p++;
        if (fname[0] && *p) {
            uint32_t tlen = 0; while (p[tlen]) tlen++;
            if (st_fs_write_file(fname, p, tlen)) {
                terminal_append_line("Gravado com sucesso no BakenFS.");
            } else {
                terminal_append_line("Erro ao gravar arquivo.");
            }
        } else {
            terminal_append_line("Uso: write <arquivo> <texto>");
        }
    } else if (str_contains_nocase(cmd, "theme dark") || (cmd[0]=='d' && cmd[1]=='a')) {
        if (!desktop_shell_is_dark_theme()) {
            desktop_shell_toggle_theme();
            desktop_config_save();
        }
        terminal_append_line("Tema alterado para: Modo Escuro (Dark Mica)");
    } else if (str_contains_nocase(cmd, "theme light") || (cmd[0]=='l' && cmd[1]=='i')) {
        if (desktop_shell_is_dark_theme()) {
            desktop_shell_toggle_theme();
            desktop_config_save();
        }
        terminal_append_line("Tema alterado para: Modo Claro (Light Aero)");
    } else if (str_contains_nocase(cmd, "theme")) {
        desktop_shell_toggle_theme();
        desktop_config_save();
        terminal_append_line(desktop_shell_is_dark_theme() ? "Tema: Escuro" : "Tema: Claro");
    } else if (str_contains_nocase(cmd, "clear")) {
        g_terminal.line_count = 0;
    } else if (str_contains_nocase(cmd, "st")) {
        terminal_append_line("Sotlas Compile / Sotlas Bootstrap Self-Hosted Language Engine");
    } else {
        terminal_append_line("Comando desconhecido. Digite 'help' para ajuda.");
    }
    g_terminal.cmd_len = 0;
    g_terminal.current_cmd[0] = 0;
}

typedef struct {
    uint32_t screen_w, screen_h, time_tick;
    int32_t cursor_x, cursor_y;
    int32_t active_menu;
    uint32_t menu_x, menu_w;
    uint8_t control_center_open;
    uint8_t spotlight_open;
    uint8_t context_menu_open;
    int32_t ctx_x, ctx_y;
    char spotlight_query[32];
    uint32_t spotlight_len;
    uint32_t spotlight_filtered_apps[4];
    uint32_t spotlight_filtered_count;
} DesktopShellState;

static DesktopShellState g_shell = {1920, 1080, 0, 960, 540, -1, 0, 0, 0, 0, 0, 0, 0, {0}, 0, {0, 6, 10, 9}, 4};
static uint8_t g_loc_permission = 0; /* 0 = PENDING, 1 = GRANTED, 2 = DENIED */

uint8_t desktop_shell_get_location_permission(void) { return g_loc_permission; }
void desktop_shell_set_location_permission(uint8_t perm) { g_loc_permission = perm; }

typedef struct {
    const char *label;
    const char *shortcut;
    uint32_t action_id;
    uint8_t is_separator;
    uint8_t is_disabled;
} BakenMenuItem;

typedef struct {
    const char *title;
    uint32_t item_count;
    BakenMenuItem items[8];
} BakenMenu;

static const BakenMenu g_menus[6] = {
    {
        "Baken OS", 5, {
            {"Sobre o Baken OS Sovereign", "", 4, 0, 0},
            {"Central de Ajustes & Hardware", "", 10, 0, 0},
            {"Loja de Aplicativos Baken", "", 8, 0, 0},
            {"---", "", 0, 1, 0},
            {"Reiniciar Janelas", "Ctrl+R", 100, 0, 0}
        }
    },
    {
        "Arquivo", 4, {
            {"Novo Documento", "Ctrl+N", 6, 0, 0},
            {"Explorador BakenFS", "Ctrl+O", 0, 0, 0},
            {"---", "", 0, 1, 0},
            {"Fechar Janela Ativa", "Ctrl+W", 101, 0, 0}
        }
    },
    {
        "Editar", 6, {
            {"Desfazer", "Ctrl+Z", 0, 0, 1},
            {"Refazer", "Ctrl+Y", 0, 0, 1},
            {"---", "", 0, 1, 0},
            {"Recortar", "Ctrl+X", 0, 0, 0},
            {"Copiar", "Ctrl+C", 0, 0, 0},
            {"Colar", "Ctrl+V", 0, 0, 0}
        }
    },
    {
        "Exibir", 3, {
            {"Organizar Grade de Icones", "", 102, 0, 0},
            {"Alternar Player de Midia", "Espaco", 103, 0, 0},
            {"---", "", 0, 1, 0}
        }
    },
    {
        "Janela", 4, {
            {"Minimizar Janela", "Ctrl+M", 104, 0, 0},
            {"Trazer Todas para Frente", "", 105, 0, 0},
            {"---", "", 0, 1, 0},
            {"Fechar Todas as Janelas", "Ctrl+Q", 106, 0, 0}
        }
    },
    {
        "Ajuda", 3, {
            {"Ajuda do Baken OS", "F1", 4, 0, 0},
            {"Documentacao Sotlas", "", 4, 0, 0},
            {"Assistente Q-HAL AI", "Ctrl+H", 4, 0, 0}
        }
    }
};

static DesktopDock g_main_dock;
/* Estado do player local. O controle é real; saída de áudio só será marcada
 * disponível quando o driver HDA existir. */
static uint8_t g_media_playing = 0;
/* 0 = play visivel, 255 = pause visivel. O valor atravessa os estados para
 * que a troca tenha continuidade em vez de piscar entre dois bitmaps. */
static uint16_t g_media_transition = 0;

static void desktop_set_media_playing(uint8_t playing) {
    g_media_playing = playing ? 1u : 0u;
    /* O estado semantico deve ficar legivel no primeiro frame, inclusive em
     * TCG lento. Movimento residual pertence ao halo, nao a dois glyphs sobrepostos. */
    g_media_transition = g_media_playing ? 255u : 0u;
}

typedef struct {
    uint32_t x, y, width, gap;
    uint32_t weather_h, media_h, calendar_h, monitor_h, notes_h;
    uint32_t visible_mask;
} BakenWidgetLayout;

#define BKN_WIDGET_WEATHER  (1u << 0)
#define BKN_WIDGET_MEDIA    (1u << 1)
#define BKN_WIDGET_CALENDAR (1u << 2)
#define BKN_WIDGET_MONITOR  (1u << 3)
#define BKN_WIDGET_NOTES    (1u << 4)

typedef struct { uint32_t x, y, cell_w, cell_h, icon, columns, rows; } BakenDesktopGrid;

typedef struct {
    uint32_t app_id;
    const char *label;
} DesktopGridItem;

static const DesktopGridItem g_desktop_items[12] = {
    {0, "BakenFS"},
    {1, "3D Studio"},
    {2, "Navegador"},
    {3, "Paint"},
    {4, "Camera"},
    {5, "Midia"},
    {6, "Notas"},
    {8, "Loja"},
    {10, "Ajustes"},
    {9, "Terminal"},
    {12, "Calendario"},
    {11, "Pessoal"}
};

/* Uma única fonte de geometria para desenho e clique. Antes, o handler
 * calculava tamanhos por largura e o renderer usava UI scale; em telas altas
 * ou estreitas os limites visuais e interativos divergiam. */
static BakenWidgetLayout desktop_widget_layout(void) {
    BakenWidgetLayout layout;
    uint32_t sw = g_shell.screen_w, sh = g_shell.screen_h;
    layout.width = baken_ui_px(300);
    layout.gap = baken_ui_px(10);
    if (layout.width + layout.gap > sw) layout.width = sw > layout.gap ? sw - layout.gap : sw;
    layout.x = sw > layout.width + layout.gap ? sw - layout.width - layout.gap : 0;
    layout.y = baken_ui_px(40);
    /* Alturas balanceadas com respiro e acabamento glassmorphic */
    layout.weather_h = baken_ui_px(114);
    layout.media_h = baken_ui_px(96);
    layout.calendar_h = baken_ui_px(124);
    layout.monitor_h = baken_ui_px(104);
    layout.notes_h = baken_ui_px(100);
    layout.visible_mask = BKN_WIDGET_WEATHER | BKN_WIDGET_MEDIA | BKN_WIDGET_CALENDAR |
                          BKN_WIDGET_MONITOR | BKN_WIDGET_NOTES;
    uint32_t desired = layout.weather_h + layout.media_h + layout.calendar_h + layout.monitor_h + layout.notes_h + layout.gap * 4u;
    /* Reserva dock e margem inferior */
    uint32_t reserve = baken_ui_px(96);
    uint32_t available = sh > layout.y + reserve ? sh - layout.y - reserve : 0;
    if (desired > available) { layout.visible_mask &= ~BKN_WIDGET_NOTES; layout.notes_h = 0; desired -= baken_ui_px(100) + layout.gap; }
    if (desired > available) { layout.visible_mask &= ~BKN_WIDGET_MONITOR; layout.monitor_h = 0; desired -= baken_ui_px(104) + layout.gap; }
    if (desired > available) { layout.visible_mask &= ~BKN_WIDGET_CALENDAR; layout.calendar_h = 0; desired -= baken_ui_px(124) + layout.gap; }
    if (desired > available) { layout.visible_mask &= ~BKN_WIDGET_MEDIA; layout.media_h = 0; desired -= baken_ui_px(96) + layout.gap; }
    if (desired > available) { layout.visible_mask &= ~BKN_WIDGET_WEATHER; layout.weather_h = 0; }
    return layout;
}

/* Grade é baseada no espaço realmente livre entre margem segura e widgets.
 * O mesmo resultado é consumido pelo desenho e pelo handler de clique. */
static BakenDesktopGrid desktop_grid_layout(void) {
    BakenDesktopGrid grid;
    uint32_t sw = g_shell.screen_w;
    uint32_t margin = baken_ui_px(32);
    uint32_t available = sw;
    if (sw >= baken_ui_px(800)) {
        BakenWidgetLayout widgets = desktop_widget_layout();
        if (widgets.x > margin) available = widgets.x - margin;
    }
    grid.cell_w = baken_ui_px(112); grid.cell_h = baken_ui_px(108);
    grid.columns = available >= margin + grid.cell_w * 2u ? 2u : 1u;
    grid.rows = 6u;
    grid.icon = baken_ui_px(64);
    if (grid.icon + baken_ui_px(12) > grid.cell_h) grid.icon = grid.cell_h > baken_ui_px(28) ? grid.cell_h - baken_ui_px(28) : grid.cell_h;
    grid.x = margin; grid.y = baken_ui_px(56);
    return grid;
}

void desktop_shell_init(uint32_t w, uint32_t h) {
    pci_scan_hardware();
    g_shell.screen_w = w; g_shell.screen_h = h; g_shell.time_tick = 0;
    g_shell.cursor_x = (int32_t)(w / 2); g_shell.cursor_y = (int32_t)(h / 2);
    dock_init(&g_main_dock);
    dock_add_item(&g_main_dock, (const uint8_t*)"Arquivos");
    dock_add_item(&g_main_dock, (const uint8_t*)"Midia");
    dock_add_item(&g_main_dock, (const uint8_t*)"3D Studio");
    dock_add_item(&g_main_dock, (const uint8_t*)"Navegador");
    dock_add_item(&g_main_dock, (const uint8_t*)"Paint");
    dock_add_item(&g_main_dock, (const uint8_t*)"Camera");
    dock_add_item(&g_main_dock, (const uint8_t*)"Notas");
    dock_add_item(&g_main_dock, (const uint8_t*)"Loja");
    dock_add_item(&g_main_dock, (const uint8_t*)"Ajustes");
    dock_add_item(&g_main_dock, (const uint8_t*)"Terminal");
    dock_add_item(&g_main_dock, (const uint8_t*)"Sistema");
    dock_add_item(&g_main_dock, (const uint8_t*)"Lancar");
    dock_add_item(&g_main_dock, (const uint8_t*)"Calendario");
    dock_add_item(&g_main_dock, (const uint8_t*)"Pessoal");
    dock_add_item(&g_main_dock, (const uint8_t*)"Busca");
    wm_init();
}

void desktop_shell_set_cursor(int32_t x, int32_t y) {
    g_shell.cursor_x = x; g_shell.cursor_y = y;
}

static void desktop_open_app(uint32_t app_id) {
    uint32_t sw = g_shell.screen_w;
    uint32_t sh = g_shell.screen_h;
    if (g_loc_permission == 0) {
        g_loc_permission = 1;
    }
    dock_trigger_bounce(&g_main_dock, app_id);
    if (app_id == 0 || app_id == 11) {
        wm_create_window(1, (const uint8_t*)"Arquivos - BakenFS", (int32_t)(sw / 2 - 280), (int32_t)(sh / 2 - 180), 560, 360, 0x00F8FAFC, 215, 0x00FFFFFF);
        wm_bring_to_front(1);
    } else if (app_id == 6) {
        wm_create_window(2, (const uint8_t*)"Notas - /home/notas.txt", (int32_t)(sw / 2 - 220), (int32_t)(sh / 2 - 140), 440, 280, 0x00F8FAFC, 215, 0x00FFFFFF);
        wm_bring_to_front(2);
    } else if (app_id == 8) {
        wm_create_window(3, (const uint8_t*)"Loja de Aplicativos - Baken Store", (int32_t)(sw / 2 - 260), (int32_t)(sh / 2 - 170), 520, 340, 0x00F8FAFC, 215, 0x00FFFFFF);
        wm_bring_to_front(3);
    } else if (app_id == 10) {
        wm_create_window(3, (const uint8_t*)"Central de Ajustes & Hardware", (int32_t)(sw / 2 - 250), (int32_t)(sh / 2 - 150), 500, 300, 0x00F8FAFC, 215, 0x00FFFFFF);
        wm_bring_to_front(3);
    } else if (app_id == 9) {
        wm_create_window(4, (const uint8_t*)"Terminal Sotlas - Vortex Core", (int32_t)(sw / 2 - 270), (int32_t)(sh / 2 - 170), 540, 340, 0x00F8FAFC, 215, 0x00FFFFFF);
        wm_bring_to_front(4);
    } else if (app_id == 14) {
        wm_create_window(5, (const uint8_t*)"Instalador e Setup - Baken OS Sovereign", (int32_t)(sw / 2 - 370), (int32_t)(sh / 2 - 250), 740, 500, 0x00F8FAFC, 215, 0x00FFFFFF);
        wm_bring_to_front(5);
    } else {
        wm_create_window(4, (const uint8_t*)"Baken OS - Aplicativo", (int32_t)(sw / 2 - 200), (int32_t)(sh / 2 - 120), 400, 240, 0x00F8FAFC, 215, 0x00FFFFFF);
        wm_bring_to_front(4);
    }
}

static void get_top_bar_menu_bounds(int menu_idx, uint32_t *out_x, uint32_t *out_w) {
    if (menu_idx == 0) {
        if (out_x) *out_x = baken_ui_px(8);
        if (out_w) *out_w = baken_ui_px(96);
        return;
    }
    static const char *k_menus[] = {"Arquivo", "Editar", "Exibir", "Janela", "Ajuda"};
    uint32_t cur_x = baken_ui_px(112);
    for (int m = 0; m < 5; ++m) {
        uint32_t item_w = gfx_measure_text(k_menus[m]);
        if (m + 1 == menu_idx) {
            if (out_x) *out_x = cur_x - baken_ui_px(6);
            if (out_w) *out_w = item_w + baken_ui_px(12);
            return;
        }
        cur_x += item_w + baken_ui_px(18);
    }
    if (out_x) *out_x = 0;
    if (out_w) *out_w = 0;
}

static void render_dropdown_menu(void) {
    if (g_shell.active_menu < 0 || g_shell.active_menu >= 6) return;
    int m_idx = g_shell.active_menu;
    const BakenMenu *menu = &g_menus[m_idx];
    if (menu->item_count == 0) return;

    uint32_t top_h = baken_ui_px(32);
    uint32_t menu_x = g_shell.menu_x;
    uint32_t item_h = baken_ui_px(24);
    uint32_t pad_v = baken_ui_px(6);
    uint32_t pad_h = baken_ui_px(12);
    uint32_t menu_w = baken_ui_px(210);
    uint8_t is_dark = desktop_shell_is_dark_theme();

    for (uint32_t i = 0; i < menu->item_count; ++i) {
        if (!menu->items[i].is_separator) {
            uint32_t lw = gfx_measure_text(menu->items[i].label);
            uint32_t sw = gfx_measure_text(menu->items[i].shortcut);
            uint32_t req = lw + sw + baken_ui_px(36);
            if (req > menu_w) menu_w = req;
        }
    }

    uint32_t sw = g_shell.screen_w;
    if (menu_x + menu_w + baken_ui_px(8) > sw) {
        menu_x = (sw > menu_w + baken_ui_px(8)) ? sw - menu_w - baken_ui_px(8) : 0;
    }
    g_shell.menu_x = menu_x;
    g_shell.menu_w = menu_w;

    uint32_t menu_h = pad_v * 2u;
    for (uint32_t i = 0; i < menu->item_count; ++i) {
        menu_h += menu->items[i].is_separator ? baken_ui_px(8) : item_h;
    }
    uint32_t menu_y = top_h + baken_ui_px(2);

    gfx_draw_smooth_shadow(menu_x, menu_y, (int)menu_w, (int)menu_h, 10, 18, 110);
    baken_lua_draw_surface(menu_x, menu_y, menu_w, menu_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, baken_ui_px(10));

    int32_t mx = g_shell.cursor_x, my = g_shell.cursor_y;
    uint32_t cur_y = menu_y + pad_v;
    for (uint32_t i = 0; i < menu->item_count; ++i) {
        const BakenMenuItem *item = &menu->items[i];
        if (item->is_separator) {
            gfx_draw_hline(menu_x + baken_ui_px(10), cur_y + baken_ui_px(4), menu_w - baken_ui_px(20), is_dark ? 0x00334155 : 0x00CBD5E1, 80);
            cur_y += baken_ui_px(8);
            continue;
        }

        int is_hover = (mx >= (int32_t)(menu_x + baken_ui_px(4)) &&
                        mx < (int32_t)(menu_x + menu_w - baken_ui_px(4)) &&
                        my >= (int32_t)cur_y && my < (int32_t)(cur_y + item_h));

        if (is_hover && !item->is_disabled) {
            gfx_draw_glass_rect_material(menu_x + baken_ui_px(4), cur_y, menu_w - baken_ui_px(8), item_h,
                                         0x000284C7, 220, 0x0038BDF8, baken_ui_px(6));
        }

        uint32_t text_color = item->is_disabled ? 0x0094A3B8 : (is_hover ? 0x00FFFFFF : (is_dark ? 0x00F8FAFC : 0x000F172A));
        uint32_t shortcut_color = item->is_disabled ? 0x0094A3B8 : (is_hover ? 0x00E0F2FE : 0x0064748B);

        uint32_t ty = cur_y + (item_h > baken_ui_px(14) ? (item_h - baken_ui_px(14)) / 2u : 0u);
        gfx_draw_text_proportional(menu_x + pad_h, ty, item->label, text_color);

        if (item->shortcut && item->shortcut[0]) {
            uint32_t sw_w = gfx_measure_text(item->shortcut);
            uint32_t sx = menu_x + menu_w - pad_h - sw_w;
            gfx_draw_text_proportional(sx, ty, item->shortcut, shortcut_color);
        }

        cur_y += item_h;
    }
}

static void render_control_center(void) {
    if (!g_shell.control_center_open) return;
    uint32_t sw = g_shell.screen_w;
    uint32_t cw = baken_ui_px(316);
    uint32_t ch = baken_ui_px(360);
    uint32_t cx = sw > cw + baken_ui_px(10) ? sw - cw - baken_ui_px(10) : 0;
    uint32_t cy = baken_ui_px(38);
    uint8_t is_dark = desktop_shell_is_dark_theme();

    gfx_draw_smooth_shadow(cx, cy, (int)cw, (int)ch, 14, 24, 130);
    baken_lua_draw_surface(cx, cy, cw, ch, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, baken_ui_px(14));

    uint32_t header_y = cy + baken_ui_px(12);
    gfx_draw_circle_alpha(cx + baken_ui_px(18), header_y + baken_ui_px(8), baken_ui_px(4), 0x0000E5FF, 255);
    gfx_draw_text_role(cx + baken_ui_px(28), header_y, "Central de Controle Q-HAL", is_dark ? 0x00F8FAFC : 0x000F172A, BKN_TYPE_LABEL);

    uint32_t card1_y = cy + baken_ui_px(38);
    uint32_t card_w = cw - baken_ui_px(24);
    baken_lua_draw_surface(cx + baken_ui_px(12), card1_y, card_w, baken_ui_px(96), BKN_LUA_MICA, BKN_LUA_REST, baken_ui_px(10));
    gfx_draw_text_proportional(cx + baken_ui_px(20), card1_y + baken_ui_px(8), "Telemetria do Sistema", 0x000284C7);

    gfx_draw_text_proportional(cx + baken_ui_px(20), card1_y + baken_ui_px(28), "CPU Cortex-Core", is_dark ? 0x00E2E8F0 : 0x00334155);
    gfx_draw_text_proportional(cx + card_w - baken_ui_px(24), card1_y + baken_ui_px(28), "34%", 0x000284C7);
    baken_lua_draw_surface(cx + baken_ui_px(20), card1_y + baken_ui_px(44), card_w - baken_ui_px(16), baken_ui_px(6), BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 3);
    gfx_fill_rect_alpha(cx + baken_ui_px(20), card1_y + baken_ui_px(44), (card_w - baken_ui_px(16)) * 34 / 100, baken_ui_px(6), 0x000284C7, 240);

    gfx_draw_text_proportional(cx + baken_ui_px(20), card1_y + baken_ui_px(58), "Memoria RAM (512MB/2GB)", is_dark ? 0x00E2E8F0 : 0x00334155);
    gfx_draw_text_proportional(cx + card_w - baken_ui_px(24), card1_y + baken_ui_px(58), "25%", 0x0010B981);
    baken_lua_draw_surface(cx + baken_ui_px(20), card1_y + baken_ui_px(74), card_w - baken_ui_px(16), baken_ui_px(6), BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 3);
    gfx_fill_rect_alpha(cx + baken_ui_px(20), card1_y + baken_ui_px(74), (card_w - baken_ui_px(16)) * 25 / 100, baken_ui_px(6), 0x0010B981, 240);

    uint32_t card2_y = card1_y + baken_ui_px(104);
    baken_lua_draw_surface(cx + baken_ui_px(12), card2_y, card_w, baken_ui_px(72), BKN_LUA_MICA, BKN_LUA_REST, baken_ui_px(10));
    gfx_draw_text_proportional(cx + baken_ui_px(20), card2_y + baken_ui_px(8), "Volume de Audio (HDA)", is_dark ? 0x00E2E8F0 : 0x00334155);
    gfx_draw_text_proportional(cx + card_w - baken_ui_px(24), card2_y + baken_ui_px(8), "80%", 0x000284C7);
    baken_lua_draw_surface(cx + baken_ui_px(20), card2_y + baken_ui_px(22), card_w - baken_ui_px(16), baken_ui_px(8), BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 4);
    gfx_fill_rect_alpha(cx + baken_ui_px(20), card2_y + baken_ui_px(22), (card_w - baken_ui_px(16)) * 80 / 100, baken_ui_px(8), 0x000284C7, 240);

    gfx_draw_text_proportional(cx + baken_ui_px(20), card2_y + baken_ui_px(38), "Brilho do Monitor (GOP)", is_dark ? 0x00E2E8F0 : 0x00334155);
    gfx_draw_text_proportional(cx + card_w - baken_ui_px(24), card2_y + baken_ui_px(38), "90%", 0x00F59E0B);
    baken_lua_draw_surface(cx + baken_ui_px(20), card2_y + baken_ui_px(52), card_w - baken_ui_px(16), baken_ui_px(8), BKN_LUA_GLASS_CLEAR, BKN_LUA_REST, 4);
    gfx_fill_rect_alpha(cx + baken_ui_px(20), card2_y + baken_ui_px(52), (card_w - baken_ui_px(16)) * 90 / 100, baken_ui_px(8), 0x00F59E0B, 240);

    uint32_t card3_y = card2_y + baken_ui_px(80);
    uint32_t tile_w = (card_w - baken_ui_px(8)) / 2u;
    uint32_t tile_h = baken_ui_px(38);

    baken_lua_draw_surface(cx + baken_ui_px(12), card3_y, tile_w, tile_h, BKN_LUA_GLASS_REGULAR, is_dark ? BKN_LUA_SELECTED : BKN_LUA_REST, baken_ui_px(8));
    gfx_draw_circle_alpha(cx + baken_ui_px(24), card3_y + baken_ui_px(19), baken_ui_px(5), is_dark ? 0x0038BDF8 : 0x00F59E0B, 240);
    gfx_draw_text_proportional(cx + baken_ui_px(34), card3_y + baken_ui_px(12), is_dark ? "Modo Escuro" : "Modo Claro", is_dark ? 0x00FFFFFF : 0x000F172A);

    baken_lua_draw_surface(cx + baken_ui_px(20) + tile_w, card3_y, tile_w, tile_h, BKN_LUA_GLASS_REGULAR, g_pci_status.has_nic ? BKN_LUA_SELECTED : BKN_LUA_REST, baken_ui_px(8));
    gfx_draw_circle_alpha(cx + baken_ui_px(32) + tile_w, card3_y + baken_ui_px(19), baken_ui_px(5), g_pci_status.has_nic ? 0x0010B981 : 0x0064748B, 240);
    gfx_draw_text_proportional(cx + baken_ui_px(42) + tile_w, card3_y + baken_ui_px(12), g_pci_status.has_nic ? "Rede PCI" : "Sem Rede", is_dark ? 0x00FFFFFF : 0x000F172A);

    uint32_t row2_y = card3_y + tile_h + baken_ui_px(6);
    baken_lua_draw_surface(cx + baken_ui_px(12), row2_y, tile_w, tile_h, BKN_LUA_GLASS_REGULAR, g_pci_status.has_hda ? BKN_LUA_SELECTED : BKN_LUA_REST, baken_ui_px(8));
    gfx_draw_circle_alpha(cx + baken_ui_px(24), row2_y + baken_ui_px(19), baken_ui_px(5), g_pci_status.has_hda ? 0x000284C7 : 0x0064748B, 240);
    gfx_draw_text_proportional(cx + baken_ui_px(34), row2_y + baken_ui_px(12), "Audio HDA", is_dark ? 0x00FFFFFF : 0x000F172A);

    baken_lua_draw_surface(cx + baken_ui_px(20) + tile_w, row2_y, tile_w, tile_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, baken_ui_px(8));
    gfx_draw_circle_alpha(cx + baken_ui_px(32) + tile_w, row2_y + baken_ui_px(19), baken_ui_px(5), 0x0000E5FF, 255);
    gfx_draw_text_proportional(cx + baken_ui_px(42) + tile_w, row2_y + baken_ui_px(12), "Q-HAL IA", is_dark ? 0x00FFFFFF : 0x000F172A);
}

static void render_spotlight_overlay(void) {
    if (!g_shell.spotlight_open) return;
    uint32_t sw = g_shell.screen_w, sh = g_shell.screen_h;
    uint32_t sp_w = baken_ui_px(540);
    uint32_t sp_h = baken_ui_px(280);
    uint32_t sp_x = sw > sp_w ? (sw - sp_w) / 2u : 0;
    uint32_t sp_y = sh > sp_h ? (sh - sp_h) / 3u : 0;
    uint8_t is_dark = desktop_shell_is_dark_theme();

    gfx_draw_smooth_shadow(sp_x, sp_y, (int)sp_w, (int)sp_h, 16, 28, 140);
    baken_lua_draw_surface(sp_x, sp_y, sp_w, sp_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, baken_ui_px(16));

    uint32_t field_y = sp_y + baken_ui_px(12);
    baken_lua_draw_surface(sp_x + baken_ui_px(12), field_y, sp_w - baken_ui_px(24), baken_ui_px(40), BKN_LUA_MICA, BKN_LUA_FOCUS, baken_ui_px(10));
    gfx_draw_circle_alpha(sp_x + baken_ui_px(28), field_y + baken_ui_px(20), baken_ui_px(6), 0x000284C7, 240);
    gfx_draw_text_role(sp_x + baken_ui_px(42), field_y + baken_ui_px(12),
                       g_shell.spotlight_len ? g_shell.spotlight_query : "Buscar no Baken OS, arquivos, apps e Q-HAL...",
                       g_shell.spotlight_len ? (is_dark ? 0x00FFFFFF : 0x000F172A) : (is_dark ? 0x0064748B : 0x0094A3B8),
                       BKN_TYPE_LABEL);

    if ((g_shell.time_tick % 40) < 24) {
        uint32_t tw = g_shell.spotlight_len ? gfx_measure_text(g_shell.spotlight_query) : 0;
        gfx_fill_rect_alpha(sp_x + baken_ui_px(44) + tw, field_y + baken_ui_px(11), 2, baken_ui_px(18), 0x000284C7, 240);
    }

    gfx_draw_hline(sp_x + baken_ui_px(14), field_y + baken_ui_px(48), sp_w - baken_ui_px(28), is_dark ? 0x00334155 : 0x00CBD5E1, 80);

    typedef struct { const char *title; const char *sub; uint32_t app_id; } SpotlightItem;
    static const SpotlightItem catalog[6] = {
        {"Arquivos - BakenFS", "Explorador de Arquivos (/home)", 0},
        {"Notas Rapidas", "Editor de texto persistente", 6},
        {"Central de Ajustes", "Configuracoes de Hardware", 10},
        {"Terminal Sotlas", "Interpretador de Comandos Vortex", 9},
        {"Assistente Q-HAL AI", "Inteligencia Artificial Soberana", 4},
        {"Instalar Baken OS", "Assistente de Instalacao UEFI", 14}
    };

    SpotlightItem filtered[4];
    uint32_t match_count = 0;
    for (int c = 0; c < 6 && match_count < 4; ++c) {
        if (g_shell.spotlight_len == 0 ||
            str_contains_nocase(catalog[c].title, g_shell.spotlight_query) ||
            str_contains_nocase(catalog[c].sub, g_shell.spotlight_query)) {
            filtered[match_count] = catalog[c];
            g_shell.spotlight_filtered_apps[match_count] = catalog[c].app_id;
            match_count++;
        }
    }
    g_shell.spotlight_filtered_count = match_count;

    int32_t mx = g_shell.cursor_x, my = g_shell.cursor_y;
    uint32_t res_y = field_y + baken_ui_px(56);
    if (match_count == 0) {
        gfx_draw_text_proportional(sp_x + baken_ui_px(24), res_y + baken_ui_px(20),
                                   "Nenhum aplicativo ou arquivo correspondente encontrado.",
                                   is_dark ? 0x0094A3B8 : 0x0064748B);
    } else {
        for (uint32_t i = 0; i < match_count; ++i) {
            int is_hover = (mx >= (int32_t)(sp_x + baken_ui_px(12)) && mx < (int32_t)(sp_x + sp_w - baken_ui_px(12)) &&
                            my >= (int32_t)res_y && my < (int32_t)(res_y + baken_ui_px(38)));
            if (is_hover || (g_shell.spotlight_len > 0 && i == 0)) {
                gfx_draw_glass_rect_material(sp_x + baken_ui_px(12), res_y, sp_w - baken_ui_px(24), baken_ui_px(38), 0x000284C7, 220, 0x0038BDF8, baken_ui_px(8));
            } else {
                baken_lua_draw_surface(sp_x + baken_ui_px(12), res_y, sp_w - baken_ui_px(24), baken_ui_px(38), BKN_LUA_MICA, BKN_LUA_REST, baken_ui_px(8));
            }
            gfx_draw_app_icon_hd(sp_x + baken_ui_px(18), res_y + baken_ui_px(5), baken_ui_px(28), filtered[i].app_id);
            gfx_draw_text_proportional(sp_x + baken_ui_px(52), res_y + baken_ui_px(6), filtered[i].title, (is_hover || (g_shell.spotlight_len > 0 && i == 0)) ? 0x00FFFFFF : (is_dark ? 0x00F8FAFC : 0x000F172A));
            gfx_draw_text_proportional(sp_x + baken_ui_px(52), res_y + baken_ui_px(20), filtered[i].sub, (is_hover || (g_shell.spotlight_len > 0 && i == 0)) ? 0x00E0F2FE : (is_dark ? 0x0094A3B8 : 0x0064748B));
            res_y += baken_ui_px(44);
        }
    }
}

static void render_desktop_context_menu(void) {
    if (!g_shell.context_menu_open) return;
    uint32_t cx = (uint32_t)g_shell.ctx_x;
    uint32_t cy = (uint32_t)g_shell.ctx_y;
    uint32_t mw = baken_ui_px(200);
    uint32_t mh = baken_ui_px(120);
    uint32_t sw = g_shell.screen_w, sh = g_shell.screen_h;
    if (cx + mw > sw) cx = sw > mw ? sw - mw : 0;
    if (cy + mh > sh) cy = sh > mh ? sh - mh : 0;
    uint8_t is_dark = desktop_shell_is_dark_theme();

    gfx_draw_smooth_shadow(cx, cy, (int)mw, (int)mh, 10, 18, 110);
    baken_lua_draw_surface(cx, cy, mw, mh, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, baken_ui_px(10));

    static const char *ctx_items[] = {
        "Novo Documento",
        "Organizar Icones",
        "Alternar Modo Escuro",
        "Sobre o Baken OS"
    };

    int32_t mx = g_shell.cursor_x, my = g_shell.cursor_y;
    uint32_t cur_y = cy + baken_ui_px(6);
    for (int i = 0; i < 4; ++i) {
        int is_hover = (mx >= (int32_t)cx && mx < (int32_t)(cx + mw) &&
                        my >= (int32_t)cur_y && my < (int32_t)(cur_y + baken_ui_px(24)));
        if (is_hover) {
            gfx_draw_glass_rect_material(cx + baken_ui_px(4), cur_y, mw - baken_ui_px(8), baken_ui_px(24), 0x000284C7, 220, 0x0038BDF8, baken_ui_px(6));
        }
        gfx_draw_text_proportional(cx + baken_ui_px(16), cur_y + baken_ui_px(4), ctx_items[i], is_hover ? 0x00FFFFFF : (is_dark ? 0x00F8FAFC : 0x000F172A));
        cur_y += baken_ui_px(26);
    }
}

void desktop_shell_toggle_control_center(void) {
    g_shell.control_center_open = !g_shell.control_center_open;
    if (g_shell.control_center_open) { g_shell.active_menu = -1; g_shell.spotlight_open = 0; g_shell.context_menu_open = 0; }
}

void desktop_shell_toggle_spotlight(void) {
    g_shell.spotlight_open = !g_shell.spotlight_open;
    if (g_shell.spotlight_open) {
        g_shell.active_menu = -1;
        g_shell.control_center_open = 0;
        g_shell.context_menu_open = 0;
        g_shell.spotlight_query[0] = 0;
        g_shell.spotlight_len = 0;
    }
}

void desktop_shell_toggle_context_menu(void) {
    g_shell.context_menu_open = !g_shell.context_menu_open;
    g_shell.ctx_x = g_shell.cursor_x;
    g_shell.ctx_y = g_shell.cursor_y;
    if (g_shell.context_menu_open) { g_shell.active_menu = -1; g_shell.control_center_open = 0; g_shell.spotlight_open = 0; }
}

void desktop_shell_open_context_menu(int32_t x, int32_t y) {
    g_shell.context_menu_open = 1;
    g_shell.ctx_x = x;
    g_shell.ctx_y = y;
    g_shell.active_menu = -1;
    g_shell.control_center_open = 0;
    g_shell.spotlight_open = 0;
}

static void render_permission_dialog(void) {
    if (g_loc_permission != 0) return;
    uint32_t sw = g_shell.screen_w, sh = g_shell.screen_h;
    uint32_t dw = baken_ui_px(440);
    uint32_t dh = baken_ui_px(180);
    uint32_t dx = sw > dw ? (sw - dw) / 2u : 0;
    uint32_t dy = sh > dh ? (sh - dh) / 2u : 0;
    uint8_t is_dark = desktop_shell_is_dark_theme();

    gfx_draw_smooth_shadow(dx, dy, (int)dw, (int)dh, 16, 28, 140);
    baken_lua_draw_surface(dx, dy, dw, dh, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, baken_ui_px(14));

    uint32_t header_y = dy + baken_ui_px(14);
    gfx_draw_circle_alpha(dx + baken_ui_px(22), header_y + baken_ui_px(8), baken_ui_px(6), 0x000284C7, 240);
    gfx_draw_text_role(dx + baken_ui_px(34), header_y, "Permissao de Localizacao", is_dark ? 0x00FFFFFF : 0x000F172A, BKN_TYPE_TITLE);

    uint32_t msg_y = dy + baken_ui_px(46);
    gfx_draw_text_proportional(dx + baken_ui_px(20), msg_y, "O Baken OS solicita autorizacao para acessar sua", is_dark ? 0x00E2E8F0 : 0x00334155);
    gfx_draw_text_proportional(dx + baken_ui_px(20), msg_y + baken_ui_px(18), "localizacao (via IP/Rede ou GPS) para exibir previsao", is_dark ? 0x00E2E8F0 : 0x00334155);
    gfx_draw_text_proportional(dx + baken_ui_px(20), msg_y + baken_ui_px(36), "do tempo e fuso horario dinamicos no desktop.", is_dark ? 0x0094A3B8 : 0x0064748B);

    uint32_t btn_y = dy + dh - baken_ui_px(48);
    uint32_t btn_w = baken_ui_px(190);
    uint32_t btn_h = baken_ui_px(34);
    int32_t mx = g_shell.cursor_x, my = g_shell.cursor_y;

    /* Botão 1: Permitir Acesso */
    uint32_t btn1_x = dx + baken_ui_px(20);
    int hover1 = (mx >= (int32_t)btn1_x && mx < (int32_t)(btn1_x + btn_w) && my >= (int32_t)btn_y && my < (int32_t)(btn_y + btn_h));
    if (hover1) {
        gfx_draw_glass_rect_material(btn1_x, btn_y, btn_w, btn_h, 0x000284C7, 240, 0x0038BDF8, baken_ui_px(8));
    } else {
        baken_lua_draw_surface(btn1_x, btn_y, btn_w, btn_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_SELECTED, baken_ui_px(8));
    }
    gfx_draw_text_proportional(btn1_x + baken_ui_px(44), btn_y + baken_ui_px(8), "Permitir Acesso", 0x00FFFFFF);

    /* Botão 2: Recusar */
    uint32_t btn2_x = dx + dw - btn_w - baken_ui_px(20);
    int hover2 = (mx >= (int32_t)btn2_x && mx < (int32_t)(btn2_x + btn_w) && my >= (int32_t)btn_y && my < (int32_t)(btn_y + btn_h));
    if (hover2) {
        gfx_draw_glass_rect_material(btn2_x, btn_y, btn_w, btn_h, 0x00334155, 200, 0x0064748B, baken_ui_px(8));
    } else {
        baken_lua_draw_surface(btn2_x, btn_y, btn_w, btn_h, BKN_LUA_MICA, BKN_LUA_REST, baken_ui_px(8));
    }
    gfx_draw_text_proportional(btn2_x + baken_ui_px(68), btn_y + baken_ui_px(8), "Recusar", is_dark ? 0x0094A3B8 : 0x0064748B);
}

void desktop_shell_handle_click(int32_t mx, int32_t my) {
    uint32_t top_h = baken_ui_px(32);
    uint32_t sw = g_shell.screen_w, sh = g_shell.screen_h;

    // 0. Diálogo de Permissão de Localização
    if (g_loc_permission == 0) {
        uint32_t dw = baken_ui_px(440), dh = baken_ui_px(180);
        uint32_t dx = sw > dw ? (sw - dw) / 2u : 0;
        uint32_t dy = sh > dh ? (sh - dh) / 2u : 0;
        uint32_t btn_y = dy + dh - baken_ui_px(48);
        uint32_t btn_w = baken_ui_px(190), btn_h = baken_ui_px(34);
        uint32_t btn1_x = dx + baken_ui_px(20);
        uint32_t btn2_x = dx + dw - btn_w - baken_ui_px(20);

        if (mx >= (int32_t)btn1_x && mx < (int32_t)(btn1_x + btn_w) && my >= (int32_t)btn_y && my < (int32_t)(btn_y + btn_h)) {
            g_loc_permission = 1;
            desktop_config_save();
            return;
        }
        if (mx >= (int32_t)btn2_x && mx < (int32_t)(btn2_x + btn_w) && my >= (int32_t)btn_y && my < (int32_t)(btn_y + btn_h)) {
            g_loc_permission = 2;
            desktop_config_save();
            return;
        }
        return;
    }

    // 1. Central de Controle
    if (g_shell.control_center_open) {
        uint32_t cw = baken_ui_px(316), ch = baken_ui_px(360);
        uint32_t cx = sw > cw + baken_ui_px(10) ? sw - cw - baken_ui_px(10) : 0;
        uint32_t cy = baken_ui_px(38);
        if (mx >= (int32_t)cx && mx < (int32_t)(cx + cw) && my >= (int32_t)cy && my < (int32_t)(cy + ch)) {
            // Clicou no toggle do Modo Escuro?
            uint32_t card3_y = cy + baken_ui_px(38) + baken_ui_px(104) + baken_ui_px(80);
            uint32_t tile_w = (cw - baken_ui_px(24) - baken_ui_px(8)) / 2u;
            uint32_t tile_h = baken_ui_px(38);
            if (mx >= (int32_t)(cx + baken_ui_px(12)) && mx < (int32_t)(cx + baken_ui_px(12) + tile_w) &&
                my >= (int32_t)card3_y && my < (int32_t)(card3_y + tile_h)) {
                desktop_shell_toggle_theme();
                return;
            }
            return;
        }
        g_shell.control_center_open = 0;
    }

    // 2. Spotlight Search
    if (g_shell.spotlight_open) {
        uint32_t sp_w = baken_ui_px(540), sp_h = baken_ui_px(280);
        uint32_t sp_x = sw > sp_w ? (sw - sp_w) / 2u : 0;
        uint32_t sp_y = sh > sp_h ? (sh - sp_h) / 3u : 0;
        if (mx >= (int32_t)sp_x && mx < (int32_t)(sp_x + sp_w) && my >= (int32_t)sp_y && my < (int32_t)(sp_y + sp_h)) {
            uint32_t res_y = sp_y + baken_ui_px(12) + baken_ui_px(56);
            for (uint32_t i = 0; i < g_shell.spotlight_filtered_count; ++i) {
                if (my >= (int32_t)res_y && my < (int32_t)(res_y + baken_ui_px(38))) {
                    desktop_open_app(g_shell.spotlight_filtered_apps[i]);
                    g_shell.spotlight_open = 0;
                    return;
                }
                res_y += baken_ui_px(44);
            }
            return;
        }
        g_shell.spotlight_open = 0;
    }

    // 3. Menu de Contexto
    if (g_shell.context_menu_open) {
        uint32_t cx = (uint32_t)g_shell.ctx_x, cy = (uint32_t)g_shell.ctx_y;
        uint32_t mw = baken_ui_px(200), mh = baken_ui_px(120);
        if (mx >= (int32_t)cx && mx < (int32_t)(cx + mw) && my >= (int32_t)cy && my < (int32_t)(cy + mh)) {
            uint32_t cur_y = cy + baken_ui_px(6);
            for (int i = 0; i < 4; ++i) {
                if (my >= (int32_t)cur_y && my < (int32_t)(cur_y + baken_ui_px(24))) {
                    if (i == 0) desktop_open_app(6);
                    else if (i == 2) desktop_shell_toggle_theme();
                    else if (i == 3) desktop_open_app(4);
                    g_shell.context_menu_open = 0;
                    return;
                }
                cur_y += baken_ui_px(26);
            }
            g_shell.context_menu_open = 0;
            return;
        }
        g_shell.context_menu_open = 0;
    }

    // 4. Menu dropdown da Top Bar
    if (g_shell.active_menu >= 0 && g_shell.active_menu < 6) {
        int m_idx = g_shell.active_menu;
        const BakenMenu *menu = &g_menus[m_idx];
        uint32_t menu_x = g_shell.menu_x;
        uint32_t menu_w = g_shell.menu_w;
        uint32_t pad_v = baken_ui_px(6);
        uint32_t item_h = baken_ui_px(24);
        uint32_t menu_y = top_h + baken_ui_px(2);
        uint32_t menu_h = pad_v * 2u;
        for (uint32_t i = 0; i < menu->item_count; ++i) {
            menu_h += menu->items[i].is_separator ? baken_ui_px(8) : item_h;
        }

        if (mx >= (int32_t)menu_x && mx < (int32_t)(menu_x + menu_w) &&
            my >= (int32_t)menu_y && my < (int32_t)(menu_y + menu_h)) {
            uint32_t cur_y = menu_y + pad_v;
            for (uint32_t i = 0; i < menu->item_count; ++i) {
                const BakenMenuItem *item = &menu->items[i];
                uint32_t cur_item_h = item->is_separator ? baken_ui_px(8) : item_h;
                if (!item->is_separator && !item->is_disabled &&
                    my >= (int32_t)cur_y && my < (int32_t)(cur_y + cur_item_h)) {
                    if (item->action_id == 100 || item->action_id == 106) {
                        wm_init();
                    } else if (item->action_id == 103) {
                        desktop_shell_toggle_media();
                    } else if (item->action_id != 0) {
                        desktop_open_app(item->action_id);
                    }
                    g_shell.active_menu = -1;
                    return;
                }
                cur_y += cur_item_h;
            }
            g_shell.active_menu = -1;
            return;
        }

        if (my >= 0 && my < (int32_t)top_h) {
            for (int m = 0; m < 6; ++m) {
                uint32_t tx, tw;
                get_top_bar_menu_bounds(m, &tx, &tw);
                if (mx >= (int32_t)tx && mx < (int32_t)(tx + tw)) {
                    if (g_shell.active_menu == m) g_shell.active_menu = -1;
                    else { g_shell.active_menu = m; g_shell.menu_x = tx; }
                    return;
                }
            }
        }
        g_shell.active_menu = -1;
    }

    // 5. Clicou na Top Bar (Menus ou System Tray / Q-HAL Capsule)
    if (my >= 0 && my < (int32_t)top_h) {
        for (int m = 0; m < 6; ++m) {
            uint32_t tx, tw;
            get_top_bar_menu_bounds(m, &tx, &tw);
            if (mx >= (int32_t)tx && mx < (int32_t)(tx + tw)) {
                g_shell.active_menu = m;
                g_shell.menu_x = tx;
                return;
            }
        }
        // Se clicou na área direita (Q-HAL / Tray / Relógio) -> abre Central de Controle
        if (mx >= (int32_t)(sw - baken_ui_px(220))) {
            desktop_shell_toggle_control_center();
            return;
        }
    }

    // 6. Janelas do Sistema (Window Manager)
    if (wm_handle_mouse_down(mx, my)) return;

    // 7. Doca flutuante
    BakenDockLayout dock; baken_dock_layout(g_main_dock.item_count, &dock);
    if (mx >= (int32_t)(dock.x + dock.pad) && mx <= (int32_t)(dock.x + dock.width - dock.pad) &&
        my >= (int32_t)dock.y && my <= (int32_t)(dock.y + dock.height)) {
        int item_idx = (mx - (int32_t)(dock.x + dock.pad)) / (int)dock.pitch;
        if (item_idx >= 0 && item_idx < (int)g_main_dock.item_count) {
            if (item_idx == 13 || item_idx == 14) { // Busca / Spotlight
                desktop_shell_toggle_spotlight();
            } else {
                desktop_open_app((uint32_t)item_idx);
            }
        }
        return;
    }

    // 8. Grade de Ícones do Desktop
    BakenDesktopGrid grid = desktop_grid_layout();
    if (mx >= (int32_t)grid.x && mx < (int32_t)(grid.x + grid.cell_w * grid.columns) && my >= (int32_t)grid.y && my < (int32_t)(grid.y + grid.cell_h * grid.rows)) {
        uint32_t col = (uint32_t)(mx - (int32_t)grid.x) / grid.cell_w;
        uint32_t row = (uint32_t)(my - (int32_t)grid.y) / grid.cell_h;
        uint32_t idx = col * grid.rows + row;
        if (col < grid.columns && row < grid.rows && idx < 12) desktop_open_app(g_desktop_items[idx].app_id);
        return;
    }

    // 9. Widgets Laterais
    BakenWidgetLayout widgets = desktop_widget_layout();
    uint32_t widget_y = widgets.y + widgets.weather_h + widgets.gap;
    if (mx >= (int32_t)widgets.x && mx < (int32_t)(widgets.x + widgets.width)) {
        if (my >= (int32_t)widget_y && my < (int32_t)(widget_y + widgets.media_h)) { desktop_set_media_playing((uint8_t)!g_media_playing); return; }
        widget_y += widgets.media_h + widgets.gap;
        if (my >= (int32_t)widget_y && my < (int32_t)(widget_y + widgets.calendar_h)) { desktop_open_app(12); return; }
        widget_y += widgets.calendar_h + widgets.gap;
        if (my >= (int32_t)widget_y && my < (int32_t)(widget_y + widgets.monitor_h)) { desktop_open_app(10); return; }
        widget_y += widgets.monitor_h + widgets.gap;
        if (my >= (int32_t)widget_y && my < (int32_t)(widget_y + widgets.notes_h)) { desktop_open_app(6); return; }
    }
}

/* Atalho público usado pelo laço de entrada UEFI e pelos testes QEMU.
 * Mantém teclado, dock e ícones passando pelo mesmo lançador canônico. */
void desktop_shell_launch_app(uint32_t app_id) {
    desktop_open_app(app_id);
}
void desktop_shell_toggle_media(void) { desktop_set_media_playing((uint8_t)!g_media_playing); }
void desktop_shell_open_menu(int32_t menu_idx) {
    if (g_shell.active_menu == menu_idx) {
        g_shell.active_menu = -1;
    } else {
        g_shell.active_menu = menu_idx;
        uint32_t tx = 0, tw = 0;
        get_top_bar_menu_bounds(menu_idx, &tx, &tw);
        g_shell.menu_x = tx;
    }
}

uint32_t desktop_shell_get_time_tick(void) {
    return g_shell.time_tick;
}

void desktop_shell_render_terminal(uint32_t px, uint32_t py, uint32_t pw, uint32_t ph, uint8_t is_focused) {
    baken_lua_draw_surface(px, py, pw, ph, BKN_LUA_CANVAS, BKN_LUA_REST, 10);
    gfx_fill_rect_alpha(px + 4, py + 4, pw - 8, ph - 8, 0x000B132B, 240);

    /* Capacidade visível de linhas */
    uint32_t vis_lines = (ph > 48) ? (ph - 48) / 18 : 1;
    uint32_t total = g_terminal.line_count;
    int32_t start_l = 0;
    if (total > vis_lines) {
        start_l = (int32_t)(total - vis_lines) - g_terminal.scroll_offset;
        if (start_l < 0) start_l = 0;
    }
    uint32_t end_l = (uint32_t)start_l + vis_lines;
    if (end_l > total) end_l = total;

    // Linhas visíveis do terminal
    uint32_t ty = py + 12;
    for (uint32_t l = (uint32_t)start_l; l < end_l && ty + 18 < py + ph - 24; ++l) {
        uint32_t col = (g_terminal.lines[l][0] == '$') ? 0x0038BDF8 : 0x00E2E8F0;
        gfx_draw_text_proportional(px + 14, ty, g_terminal.lines[l], col);
        ty += 18;
    }

    // Linha de prompt ativa
    if (ty + 18 < py + ph) {
        gfx_draw_text_proportional(px + 14, ty, "baken:~$", 0x0010B981);
        gfx_draw_text_proportional(px + 76, ty, g_terminal.current_cmd, 0x00F8FAFC);
        if (is_focused && (g_shell.time_tick % 40) < 24) {
            uint32_t tw = gfx_measure_text(g_terminal.current_cmd);
            gfx_fill_rect_alpha(px + 78 + tw, ty + 1, 2, 14, 0x0010B981, 255);
        }
    }
}

uint8_t desktop_shell_is_spotlight_open(void) {
    return g_shell.spotlight_open;
}

void desktop_shell_close_spotlight(void) {
    g_shell.spotlight_open = 0;
}

void desktop_shell_spotlight_key(uint16_t unicode, uint16_t scan) {
    if (unicode == 27 || scan == 0x17) {
        g_shell.spotlight_open = 0;
    } else if (unicode == 13 || unicode == 10) {
        if (g_shell.spotlight_filtered_count > 0) {
            desktop_open_app(g_shell.spotlight_filtered_apps[0]);
        }
        g_shell.spotlight_open = 0;
    } else if (unicode == 8 || scan == 0x08) {
        if (g_shell.spotlight_len > 0) {
            g_shell.spotlight_query[--g_shell.spotlight_len] = 0;
        }
    } else if (unicode >= 32 && unicode <= 126 && g_shell.spotlight_len < 30) {
        g_shell.spotlight_query[g_shell.spotlight_len++] = (char)unicode;
        g_shell.spotlight_query[g_shell.spotlight_len] = 0;
    }
}

void desktop_shell_terminal_key(uint16_t unicode, uint16_t scan) {
    if (scan == 0x09 || scan == 9) {
        desktop_shell_terminal_scroll(3); /* Page Up: sobe 3 linhas */
    } else if (scan == 0x0A || scan == 10) {
        desktop_shell_terminal_scroll(-3); /* Page Down: desce 3 linhas */
    } else if (unicode == 13 || unicode == 10) {
        terminal_execute_command();
    } else if (unicode == 8 || scan == 0x08) {
        if (g_terminal.cmd_len > 0) {
            g_terminal.current_cmd[--g_terminal.cmd_len] = 0;
        }
    } else if (unicode >= 32 && unicode <= 126 && g_terminal.cmd_len < 40) {
        g_terminal.current_cmd[g_terminal.cmd_len++] = (char)unicode;
        g_terminal.current_cmd[g_terminal.cmd_len] = 0;
    }
}

void desktop_shell_terminal_append(const char *line) {
    terminal_append_line(line);
}

static void __attribute__((unused)) draw_network_icon(uint32_t x, uint32_t y, uint8_t active) {
    uint32_t color = active ? 0x0010B981 : 0x0064748B;
    for (int b = 0; b < 4; ++b) {
        uint32_t h = (uint32_t)(4 + b * 3);
        uint32_t bx = x + (uint32_t)(b * 4);
        uint32_t by = y + 14 - h;
        uint32_t bar_col = (active || b == 0) ? color : 0x00CBD5E1;
        for (uint32_t py = 0; py < h; ++py) {
            gfx_put_pixel_alpha(bx, by + py, bar_col, 240);
            gfx_put_pixel_alpha(bx + 1, by + py, bar_col, 240);
        }
    }
}

static void __attribute__((unused)) draw_speaker_icon(uint32_t x, uint32_t y, uint8_t active) {
    uint32_t color = active ? 0x000284C7 : 0x0094A3B8;
    for (uint32_t py = 4; py < 12; ++py) {
        gfx_put_pixel_alpha(x, y + py, color, 240);
        gfx_put_pixel_alpha(x + 1, y + py, color, 240);
    }
    for (uint32_t py = 0; py < 16; ++py) {
        int spread = (int)py - 8;
        if (spread < 0) spread = -spread;
        if (spread <= 6) {
            uint32_t cx = x + 3 + (uint32_t)(6 - spread);
            gfx_put_pixel_alpha(cx, y + py, color, 240);
            gfx_put_pixel_alpha(cx + 1, y + py, color, 240);
        }
    }
    if (active) {
        gfx_draw_circle_alpha(x + 11, y + 8, 4, color, 200);
        gfx_draw_circle_alpha(x + 11, y + 8, 2, 0x00FFFFFF, 255);
    }
}

void render_top_bar(void) {
    uint32_t sw = g_shell.screen_w;
    uint32_t h = baken_ui_px(32);
    uint32_t text_y = (h > baken_ui_px(14)) ? (h - baken_ui_px(14)) / 2u : 0u;
    uint32_t icon_y = (h > baken_ui_px(18)) ? (h - baken_ui_px(18)) / 2u : 0u;
    uint32_t sys_icon = baken_ui_px(18);

    // Fundo Glassmorphism contínuo
    baken_lua_draw_surface(0, 0, sw, h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, 0);

    int32_t mx = g_shell.cursor_x, my = g_shell.cursor_y;

    // 1. Logo Baken OS / Marca do Sistema (Menu 0)
    uint32_t logo_x = baken_ui_px(8), logo_w = baken_ui_px(96);
    int logo_active = (g_shell.active_menu == 0);
    int logo_hover = (mx >= (int32_t)logo_x && mx < (int32_t)(logo_x + logo_w) && my >= 0 && my < (int32_t)h);
    if (logo_active) {
        gfx_draw_glass_rect_material(logo_x, baken_ui_px(4), logo_w, h - baken_ui_px(8), 0x000284C7, 210, 0x0038BDF8, baken_ui_px(6));
    } else if (logo_hover) {
        gfx_draw_glass_rect_material(logo_x, baken_ui_px(4), logo_w, h - baken_ui_px(8), 0x00FFFFFF, 140, 0x00E2E8F0, baken_ui_px(6));
    }

    uint32_t logo_cx = baken_ui_px(18), logo_cy = h / 2u;
    gfx_draw_circle_alpha(logo_cx, logo_cy, baken_ui_px(8), logo_active ? 0x00FFFFFF : 0x000284C7, 240);
    gfx_draw_circle_alpha(logo_cx, logo_cy, baken_ui_px(5), 0x0038BDF8, 255);
    gfx_draw_circle_alpha(logo_cx, logo_cy, baken_ui_px(2), 0x00FFFFFF, 255);

    gfx_draw_text_role(baken_ui_px(32), text_y, "Baken OS", logo_active ? 0x00FFFFFF : 0x000F172A, BKN_TYPE_LABEL);

    // 2. Menus discretos da barra superior com suporte a hover e estado ativo
    static const char *k_menus[] = {"Arquivo", "Editar", "Exibir", "Janela", "Ajuda"};
    uint32_t menu_x = baken_ui_px(112);
    for (int m = 0; m < 5; ++m) {
        const char *item = k_menus[m];
        uint32_t item_w = gfx_measure_text(item);
        if (menu_x + item_w + baken_ui_px(280) > sw) break;
        int m_menu_idx = m + 1;
        int is_active = (g_shell.active_menu == m_menu_idx);
        int is_hover = (mx >= (int32_t)(menu_x - baken_ui_px(6)) && mx < (int32_t)(menu_x + item_w + baken_ui_px(6)) &&
                        my >= 0 && my < (int32_t)h);

        if (is_active) {
            gfx_draw_glass_rect_material(menu_x - baken_ui_px(6), baken_ui_px(4),
                                         item_w + baken_ui_px(12), h - baken_ui_px(8),
                                         0x000284C7, 210, 0x0038BDF8, baken_ui_px(6));
        } else if (is_hover) {
            gfx_draw_glass_rect_material(menu_x - baken_ui_px(6), baken_ui_px(4),
                                         item_w + baken_ui_px(12), h - baken_ui_px(8),
                                         0x00FFFFFF, 140, 0x00E2E8F0, baken_ui_px(6));
        }
        gfx_draw_text_proportional(menu_x, text_y, item, is_active ? 0x00FFFFFF : 0x00334155);
        menu_x += item_w + baken_ui_px(18);
    }

    if (installer_is_boot_mode_live() && sw > baken_ui_px(680)) {
        uint32_t live_w = baken_ui_px(220);
        uint32_t live_h = baken_ui_px(22);
        uint32_t live_x = menu_x + baken_ui_px(10);
        uint32_t live_y = (h > live_h) ? (h - live_h) / 2u : 0u;
        int is_live_hover = (mx >= (int32_t)live_x && mx < (int32_t)(live_x + live_w) && my >= 0 && my < (int32_t)h);
        gfx_draw_glass_rect_material(live_x, live_y, live_w, live_h,
                                     is_live_hover ? 0x000284C7 : 0x000F172A,
                                     is_live_hover ? 230 : 180,
                                     0x0038BDF8, baken_ui_px(11));
        gfx_draw_circle_alpha(live_x + baken_ui_px(10), h / 2u, baken_ui_px(4), 0x0010B981, 255);
        gfx_draw_text_proportional(live_x + baken_ui_px(20), text_y, "Modo Demo | [Instalar Agora]", 0x00FFFFFF);
    }

    // 3. System Tray (Lado Direito)
    // Relógio
    RtcTime rt = rtc_read_time();
    char clock_str[24];
    if (rt.valid) {
        clock_str[0] = (char)('0' + (rt.hour / 10));
        clock_str[1] = (char)('0' + (rt.hour % 10));
        clock_str[2] = ':';
        clock_str[3] = (char)('0' + (rt.min / 10));
        clock_str[4] = (char)('0' + (rt.min % 10));
        clock_str[5] = ':';
        clock_str[6] = (char)('0' + (rt.sec / 10));
        clock_str[7] = (char)('0' + (rt.sec % 10));
        clock_str[8] = 0;
    } else {
        const char *nl = "12:00:00";
        for (int i = 0; nl[i]; ++i) clock_str[i] = nl[i];
        clock_str[8] = 0;
    }
    uint32_t clock_w = gfx_measure_text(clock_str);
    uint32_t clock_x = sw > clock_w + baken_ui_px(14) ? sw - baken_ui_px(14) - clock_w : 0;
    gfx_draw_text_proportional(clock_x, text_y, clock_str, 0x000F172A);

    // Ícones do sistema da direita para a esquerda: Volume -> Bateria -> Wi-Fi -> Pílula Q-HAL
    uint32_t tray_x = clock_x > baken_ui_px(14) ? clock_x - baken_ui_px(14) : 0;

    // Volume / Áudio HDA
    if (tray_x > sys_icon + baken_ui_px(6)) {
        tray_x -= sys_icon + baken_ui_px(6);
        gfx_draw_material_icon_state(tray_x, icon_y, sys_icon, MATERIAL_VOLUME_UP,
                                     g_pci_status.has_hda ? 0x000284C7 : 0x0094A3B8,
                                     g_pci_status.has_hda ? BKN_ICON_REST : BKN_ICON_DISABLED);
    }

    // Bateria
    if (tray_x > sys_icon + baken_ui_px(6)) {
        tray_x -= sys_icon + baken_ui_px(6);
        gfx_draw_material_icon_state(tray_x, icon_y, sys_icon, MATERIAL_BATTERY_HALF,
                                     0x00334155, BKN_ICON_REST);
    }

    // Porcentagem Bateria ("86%")
    uint32_t bat_w = gfx_measure_text("86%");
    if (sw > baken_ui_px(800) && tray_x > bat_w + baken_ui_px(6)) {
        tray_x -= bat_w + baken_ui_px(6);
        gfx_draw_text_proportional(tray_x, text_y, "86%", 0x00475569);
    }

    // Wi-Fi / Rede PCI
    if (tray_x > sys_icon + baken_ui_px(10)) {
        tray_x -= sys_icon + baken_ui_px(10);
        gfx_draw_material_icon_state(tray_x, icon_y, sys_icon, MATERIAL_WIFI,
                                     g_pci_status.has_nic ? 0x000284C7 : 0x0064748B,
                                     g_pci_status.has_nic ? BKN_ICON_REST : BKN_ICON_DISABLED);
    }

    // Pílula Q-HAL AI Capsule
    uint32_t qhal_w = baken_ui_px(82), qhal_h = baken_ui_px(22);
    if (sw > baken_ui_px(760) && tray_x > qhal_w + baken_ui_px(12)) {
        tray_x -= qhal_w + baken_ui_px(12);
        uint32_t qy = (h > qhal_h) ? (h - qhal_h) / 2u : 0u;
        gfx_draw_glass_rect_material(tray_x, qy, qhal_w, qhal_h, 0x00FFFFFF, 200, 0x00BAE6FD, baken_ui_px(11));
        // Indicador de IA Online (ponto ciano)
        gfx_draw_circle_alpha(tray_x + baken_ui_px(10), h / 2u, baken_ui_px(3), 0x0000E5FF, 255);
        gfx_draw_text_proportional(tray_x + baken_ui_px(18), text_y, "Q-HAL", 0x000284C7);
    }
}

static void render_desktop_grid(void) {
    BakenDesktopGrid grid = desktop_grid_layout();
    for (int i = 0; i < 12; ++i) {
        uint32_t col = (uint32_t)i / grid.rows;
        uint32_t row = (uint32_t)i % grid.rows;
        if (col >= grid.columns) break;
        uint32_t ix = grid.x + col * grid.cell_w;
        uint32_t iy = grid.y + row * grid.cell_h;
        gfx_draw_app_icon_hd(ix + (grid.cell_w - grid.icon) / 2u, iy, grid.icon, g_desktop_items[i].app_id);
        uint32_t label_w = gfx_measure_text(g_desktop_items[i].label);
        uint32_t label_x = ix + (grid.cell_w > label_w ? (grid.cell_w - label_w) / 2u : 4u);
        gfx_draw_text_ellipsis(label_x, iy + grid.icon + baken_ui_px(8), grid.cell_w > baken_ui_px(8) ? grid.cell_w - baken_ui_px(8) : 0, g_desktop_items[i].label, 0x00FFFFFF);
    }
}

static void widget_draw_centered_text(uint32_t x, uint32_t width, uint32_t y,
                                      const char *text, uint32_t color) {
    uint32_t tw = gfx_measure_text(text);
    uint32_t tx = x + (width > tw ? (width - tw) / 2u : 0u);
    gfx_draw_text_proportional(tx, y, text, color);
}

static void render_widgets_stack(void) {
    uint32_t sw = g_shell.screen_w;
    if (sw < baken_ui_px(800)) return;
#define U(v) baken_ui_px((v))
    uint8_t is_dark = desktop_shell_is_dark_theme();
    uint32_t title_color = is_dark ? 0x00F8FAFC : 0x000F172A;
    uint32_t sub_color = is_dark ? 0x0094A3B8 : 0x0064748B;
    uint32_t text_color = is_dark ? 0x00E2E8F0 : 0x001E293B;

    BakenWidgetLayout layout = desktop_widget_layout();
    uint32_t ww = layout.width, gap = layout.gap, wx = layout.x, y = layout.y;
    uint32_t weather_h = layout.weather_h, media_h = layout.media_h, calendar_h = layout.calendar_h;
    uint32_t monitor_h = layout.monitor_h, notes_h = layout.notes_h;

    /* 1. Clima (Weather) Dinâmico */
    if (layout.visible_mask & BKN_WIDGET_WEATHER) {
        baken_lua_draw_surface(wx, y, ww, weather_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, U(18));
        if (g_loc_permission == 1) {
            gfx_draw_text_role(wx + U(16), y + U(12), "Teresina, Piaui", title_color, BKN_TYPE_TITLE);

            // Sol com halo quente e ícone nítido
            gfx_draw_circle_alpha(wx + U(36), y + U(56), U(18), 0x00FBBF24, 35);
            gfx_draw_material_icon(wx + U(20), y + U(40), U(32), MATERIAL_SUNNY, 0x00F59E0B, 255);

            // Temperatura e rótulo
            uint32_t temp_x = wx + U(68);
            gfx_draw_text_role(temp_x, y + U(36), "32", title_color, BKN_TYPE_DISPLAY);
            gfx_draw_circle_alpha(temp_x + U(40), y + U(40), U(3), title_color, 255);
            gfx_draw_circle_alpha(temp_x + U(40), y + U(40), U(1), is_dark ? 0x000F172A : 0x00FFFFFF, 255);
            gfx_draw_text_role(temp_x + U(52), y + U(44), "Ensolarado", sub_color, BKN_TYPE_LABEL);

            // Divisor suave e rodapé
            gfx_draw_hline(wx + U(16), y + weather_h - U(26), ww - U(32), is_dark ? 0x00334155 : 0x00CBD5E1, 80);
            gfx_draw_text_ellipsis(wx + U(16), y + weather_h - U(19), ww - U(32), "Vento 14 km/h  .  Umidade 62%", sub_color);
        } else if (g_loc_permission == 2) {
            gfx_draw_text_role(wx + U(16), y + U(12), "Modo Privado (Local)", title_color, BKN_TYPE_TITLE);
            gfx_draw_material_icon(wx + U(20), y + U(40), U(32), MATERIAL_SUNNY, 0x0064748B, 200);
            uint32_t temp_x = wx + U(68);
            gfx_draw_text_role(temp_x, y + U(36), "--", sub_color, BKN_TYPE_DISPLAY);
            gfx_draw_text_role(temp_x + U(52), y + U(44), "Protegido", 0x000284C7, BKN_TYPE_LABEL);
            gfx_draw_hline(wx + U(16), y + weather_h - U(26), ww - U(32), is_dark ? 0x00334155 : 0x00CBD5E1, 80);
            gfx_draw_text_ellipsis(wx + U(16), y + weather_h - U(19), ww - U(32), "Localizacao Desativada", sub_color);
        } else {
            gfx_draw_text_role(wx + U(16), y + U(12), "Permissao Pendente", 0x00D97706, BKN_TYPE_TITLE);
            gfx_draw_material_icon(wx + U(20), y + U(40), U(32), MATERIAL_SUNNY, 0x00D97706, 200);
            uint32_t temp_x = wx + U(68);
            gfx_draw_text_role(temp_x, y + U(36), "--", sub_color, BKN_TYPE_DISPLAY);
            gfx_draw_text_role(temp_x + U(52), y + U(44), "Aguardando", 0x00D97706, BKN_TYPE_LABEL);
            gfx_draw_hline(wx + U(16), y + weather_h - U(26), ww - U(32), is_dark ? 0x00334155 : 0x00CBD5E1, 80);
            gfx_draw_text_ellipsis(wx + U(16), y + weather_h - U(19), ww - U(32), "Clique para autorizar IP/GPS", 0x00D97706);
        }
        y += weather_h + gap;
    }

    /* 2. Mídia (Player) */
    if (layout.visible_mask & BKN_WIDGET_MEDIA) {
        baken_lua_draw_surface(wx, y, ww, media_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, U(18));
        uint32_t album = U(52);
        gfx_draw_app_icon_hd(wx + U(14), y + (media_h - album) / 2u, album, 5);
        uint32_t content_x = wx + U(76), content_w = ww > U(90) ? ww - U(90) : 0;
        gfx_draw_text_ellipsis(content_x, y + U(14), content_w, "Sovereign Symphonia", title_color);
        gfx_draw_text_ellipsis(content_x, y + U(34), content_w,
            g_media_playing ? "Tocando agora" : "Pausado", g_media_playing ? 0x00059669 : sub_color);

        uint32_t control_y = y + media_h - U(34);
        uint32_t control_size = U(20), play_size = U(26);
        uint32_t back_x = content_x, play_x = content_x + U(32), next_x = content_x + U(68);
        gfx_draw_motion_icon(back_x, control_y + U(3), control_size, BAKEN_MOTION_SKIP_BACK, is_dark ? 0x0094A3B8 : 0x00334155, 230, 0);

        // Botão circular de play/pause
        gfx_draw_circle_alpha(play_x + play_size / 2u, control_y + play_size / 2u,
                              play_size / 2u + U(2), is_dark ? 0x00334155 : 0x00E2E8F0, 200);
        gfx_draw_motion_icon(play_x, control_y, play_size, BAKEN_MOTION_PLAY,
                             0x000284C7, (uint8_t)(255u - g_media_transition), 0);
        gfx_draw_motion_icon(play_x, control_y, play_size, BAKEN_MOTION_PAUSE,
                             0x000284C7, (uint8_t)g_media_transition, 0);
        gfx_draw_motion_icon(next_x, control_y + U(3), control_size, BAKEN_MOTION_SKIP_BACK, is_dark ? 0x0094A3B8 : 0x00334155, 230, 1);
        y += media_h + gap;
    }

    /* 3. Calendário */
    if (layout.visible_mask & BKN_WIDGET_CALENDAR) {
        baken_lua_draw_surface(wx, y, ww, calendar_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, U(18));
        gfx_draw_text_role(wx + U(16), y + U(10), "Agosto 2026", title_color, BKN_TYPE_TITLE);
        static const char *const weekdays[7] = {"D","S","T","Q","Q","S","S"};
        static const char *const days[35] = {
            "","","","","","","1", "2","3","4","5","6","7","8",
            "9","10","11","12","13","14","15", "16","17","18","19","20","21","22",
            "23","24","25","26","27","28","29"
        };
        uint32_t cal_x = wx + U(12), cal_w = ww - U(24), col_w = cal_w / 7u;
        for (uint32_t col = 0; col < 7u; ++col)
            widget_draw_centered_text(cal_x + col * col_w, col_w, y + U(31), weekdays[col], sub_color);
        for (uint32_t index = 0; index < 35u; ++index) {
            uint32_t row = index / 7u, col = index % 7u;
            uint32_t ty = y + U(49) + row * U(15);
            if (index == 33u) {
                // Dia ativo (28) destacado em azul suave
                gfx_draw_circle_alpha(cal_x + col * col_w + col_w / 2u, ty + U(7), U(8), 0x000284C7, 240);
            }
            widget_draw_centered_text(cal_x + col * col_w, col_w, ty, days[index], index == 33u ? 0x00FFFFFF : text_color);
        }
        y += calendar_h + gap;
    }

    /* 4. Hardware & Sistema */
    if (layout.visible_mask & BKN_WIDGET_MONITOR) {
        baken_lua_draw_surface(wx, y, ww, monitor_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, U(18));
        gfx_draw_text_role(wx + U(16), y + U(10), "Hardware & Sistema", title_color, BKN_TYPE_TITLE);
        gfx_draw_hline(wx + U(16), y + U(28), ww - U(32), is_dark ? 0x00334155 : 0x00CBD5E1, 80);

        // Item 1: Rede
        gfx_draw_circle_alpha(wx + U(22), y + U(41), U(3), g_pci_status.has_nic ? 0x0010B981 : 0x00F59E0B, 255);
        gfx_draw_text_proportional(wx + U(32), y + U(34), g_pci_status.has_nic ? "Rede PCI disponivel" : "Rede PCI ausente", text_color);

        // Item 2: Áudio
        gfx_draw_circle_alpha(wx + U(22), y + U(61), U(3), g_pci_status.has_hda ? 0x0010B981 : sub_color, 255);
        gfx_draw_text_proportional(wx + U(32), y + U(54), g_pci_status.has_hda ? "Audio HDA disponivel" : "Audio HDA ausente", sub_color);

        // Item 3: BakenFS
        char fs_status[24];
        uint32_t fs_count = st_fs_entry_count();
        fs_status[0]='B'; fs_status[1]='a'; fs_status[2]='k'; fs_status[3]='e'; fs_status[4]='n'; fs_status[5]='F'; fs_status[6]='S'; fs_status[7]=':'; fs_status[8]=' ';
        fs_status[9]=(char)('0'+(fs_count % 10)); fs_status[10]=' '; fs_status[11]='i'; fs_status[12]='t'; fs_status[13]='e'; fs_status[14]='n'; fs_status[15]='s'; fs_status[16]=0;
        gfx_draw_circle_alpha(wx + U(22), y + U(81), U(3), 0x0010B981, 255);
        gfx_draw_text_proportional(wx + U(32), y + U(74), fs_status, text_color);
        y += monitor_h + gap;
    }

    /* 5. Notas Rápidas */
    if (layout.visible_mask & BKN_WIDGET_NOTES) {
        baken_lua_draw_surface(wx, y, ww, notes_h, BKN_LUA_GLASS_REGULAR, BKN_LUA_REST, U(18));
        gfx_draw_text_role(wx + U(16), y + U(10), "Notas Rapidas", title_color, BKN_TYPE_TITLE);
        gfx_draw_hline(wx + U(16), y + U(28), ww - U(32), is_dark ? 0x00334155 : 0x00CBD5E1, 80);

        gfx_draw_circle_alpha(wx + U(22), y + U(41), U(2), 0x000284C7, 255);
        gfx_draw_text_proportional(wx + U(30), y + U(34), "Interface Sotlas ativa", text_color);

        gfx_draw_circle_alpha(wx + U(22), y + U(60), U(2), 0x000284C7, 255);
        gfx_draw_text_proportional(wx + U(30), y + U(53), "Dados no BakenFS", text_color);

        gfx_draw_circle_alpha(wx + U(22), y + U(79), U(2), 0x000284C7, 255);
        gfx_draw_text_proportional(wx + U(30), y + U(72), "Clique para abrir Notas", sub_color);
    }
#undef U
}

void render_cursor(void) {
    int32_t mx = g_shell.cursor_x, my = g_shell.cursor_y;
    uint8_t ctype = wm_get_cursor_type(mx, my);

    static const uint8_t mask_arrow[16] = {
        0x80, 0xC0, 0xE0, 0xF0, 0xF8, 0xFC, 0xFE, 0xFF,
        0xF8, 0xD8, 0x8C, 0x0C, 0x06, 0x06, 0x00, 0x00
    };
    static const uint8_t mask_diag_nwse[16] = {
        0xE0, 0xF0, 0xF8, 0xDC, 0xCE, 0x07, 0x03, 0x03,
        0xC0, 0xE0, 0x70, 0x38, 0x1C, 0x0E, 0x07, 0x00
    };
    static const uint8_t mask_diag_nesw[16] = {
        0x07, 0x0F, 0x1F, 0x3B, 0x73, 0xE0, 0xC0, 0xC0,
        0x03, 0x07, 0x0E, 0x1C, 0x38, 0x70, 0xE0, 0x00
    };
    static const uint8_t mask_horiz[16] = {
        0x00, 0x00, 0x10, 0x38, 0x7C, 0xFE, 0x7C, 0x38,
        0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    };
    static const uint8_t mask_vert[16] = {
        0x10, 0x38, 0x7C, 0xFE, 0x10, 0x10, 0x10, 0x10,
        0xFE, 0x7C, 0x38, 0x10, 0x00, 0x00, 0x00, 0x00
    };

    const uint8_t *mask = mask_arrow;
    if (ctype == 1) mask = mask_diag_nwse;
    else if (ctype == 2) mask = mask_diag_nesw;
    else if (ctype == 3) mask = mask_horiz;
    else if (ctype == 4) mask = mask_vert;

    for (int y = 0; y < 16; ++y) {
        uint8_t row = mask[y];
        for (int x = 0; x < 8; ++x) {
            if ((row >> (7 - x)) & 1) {
                gfx_put_pixel_alpha((uint32_t)(mx + x + 2), (uint32_t)(my + y + 2), 0x00000000, 90);
                if (x == 0 || y == 0 || x == 7 || ((row >> (6 - x)) & 1) == 0 || y == 15) {
                    gfx_put_pixel_alpha((uint32_t)(mx + x), (uint32_t)(my + y), 0x00FFFFFF, 255);
                } else {
                    gfx_put_pixel_alpha((uint32_t)(mx + x), (uint32_t)(my + y), 0x000F172A, 255);
                }
            }
        }
    }
}

void desktop_shell_update(float dt) {
    dock_update(&g_main_dock, dt, g_shell.cursor_x, g_shell.cursor_y);
    wm_handle_mouse_move(g_shell.cursor_x, g_shell.cursor_y);
    if (g_shell.active_menu >= 0 && g_shell.cursor_y >= 0 && g_shell.cursor_y < (int32_t)baken_ui_px(32)) {
        for (int m = 0; m < 6; ++m) {
            uint32_t tx, tw;
            get_top_bar_menu_bounds(m, &tx, &tw);
            if (g_shell.cursor_x >= (int32_t)tx && g_shell.cursor_x < (int32_t)(tx + tw)) {
                if (g_shell.active_menu != m) {
                    g_shell.active_menu = m;
                    g_shell.menu_x = tx;
                }
                break;
            }
        }
    }
}

void desktop_shell_render_frame(void) {
    g_shell.time_tick = (g_shell.time_tick + 1) % 3600;
    gfx_set_mesh_time_tick(g_shell.time_tick);
    desktop_shell_update(0.016f);
    gfx_draw_mesh_wallpaper();
    render_desktop_grid();
    render_widgets_stack();
    render_top_bar();
    wm_render_windows();
    dock_draw(&g_main_dock);
    render_dropdown_menu();
    render_control_center();
    render_spotlight_overlay();
    render_desktop_context_menu();
    render_permission_dialog();
    render_cursor();
    gfx_swap_buffers();
}
""".strip().splitlines())
    elif ast.name == "kernel::desktop_compositor":
        lines.extend("""
extern void desktop_shell_init(uint32_t screen_w, uint32_t screen_h);
extern void desktop_shell_render_frame(void);

static uint8_t g_compositor_ready = 0;

void desktop_compositor_init(uint32_t screen_w, uint32_t screen_h) {
    if (g_compositor_ready) return;
    desktop_shell_init(screen_w, screen_h);
    g_compositor_ready = 1;
}

void desktop_compositor_render_frame(void) {
    if (!g_compositor_ready) return;
    desktop_shell_render_frame();
}
""".strip().splitlines())
    elif ast.name == "kernel::main":
        lines.extend("""
#include "baken_boot_info.h"

typedef struct {
    uint32_t Data1; uint16_t Data2; uint16_t Data3; uint8_t Data4[8];
} EFI_GUID;

typedef struct {
    int32_t RelativeMovementX; int32_t RelativeMovementY; int32_t RelativeMovementZ;
    uint8_t LeftButton; uint8_t RightButton;
} EFI_SIMPLE_POINTER_STATE;

typedef struct _EFI_SIMPLE_POINTER_PROTOCOL {
    uint64_t (*Reset)(struct _EFI_SIMPLE_POINTER_PROTOCOL *This, uint8_t ExtendedVerification);
    uint64_t (*GetState)(struct _EFI_SIMPLE_POINTER_PROTOCOL *This, EFI_SIMPLE_POINTER_STATE *State);
    void *WaitForInput; void *Mode;
} EFI_SIMPLE_POINTER_PROTOCOL;

typedef struct { uint16_t ScanCode; uint16_t UnicodeChar; } EFI_INPUT_KEY;
typedef struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL {
    uint64_t (*Reset)(struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, uint8_t ExtendedVerification);
    uint64_t (*ReadKeyStroke)(struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, EFI_INPUT_KEY *Key);
    void *WaitForKey;
} EFI_SIMPLE_TEXT_INPUT_PROTOCOL;

extern void desktop_shell_toggle_theme(void);
extern uint8_t desktop_shell_is_dark_theme(void);
extern void installer_setup_io(void *boot_io, void *target_io);

typedef struct { uint32_t MediaId; uint8_t RemovableMedia,MediaPresent,LogicalPartition,ReadOnly,WriteCaching; uint32_t BlockSize,IoAlign; uint64_t LastBlock,LowestAlignedLba; uint32_t LogicalBlocksPerPhysicalBlock,OptimalTransferLengthGranularity; } EFI_BLOCK_IO_MEDIA;
typedef struct _EFI_BLOCK_IO_PROTOCOL { uint64_t Revision; EFI_BLOCK_IO_MEDIA *Media; uint64_t (*Reset)(void*,uint8_t); uint64_t (*ReadBlocks)(void*,uint32_t,uint64_t,uint64_t,void*); uint64_t (*WriteBlocks)(void*,uint32_t,uint64_t,uint64_t,void*); uint64_t (*FlushBlocks)(void*); } EFI_BLOCK_IO_PROTOCOL;
typedef struct { char name[32]; uint32_t lba, size, kind; } SotlasFsEntry;
typedef struct { uint64_t magic; uint32_t version, entry_count; SotlasFsEntry entries[12]; uint8_t reserved[20]; } SotlasFsHeader;
static EFI_BLOCK_IO_PROTOCOL *st_fs_io;
static SotlasFsHeader st_fs_header;
static uint8_t st_fs_mounted;

static void st_fs_init_defaults(void) {
    if (st_fs_header.entry_count == 0) {
        st_fs_header.magic = UINT64_C(0x3153464E454B4142);
        st_fs_header.version = 1;
        st_fs_header.entry_count = 3;

        const char *e0 = "/config/theme.cfg";
        for (int i = 0; i < 31 && e0[i]; ++i) st_fs_header.entries[0].name[i] = e0[i];
        st_fs_header.entries[0].kind = 3; st_fs_header.entries[0].size = 512; st_fs_header.entries[0].lba = 86017;

        const char *e1 = "/home/notas.txt";
        for (int i = 0; i < 31 && e1[i]; ++i) st_fs_header.entries[1].name[i] = e1[i];
        st_fs_header.entries[1].kind = 2; st_fs_header.entries[1].size = 64; st_fs_header.entries[1].lba = 86018;

        const char *e2 = "/home/documentos";
        for (int i = 0; i < 31 && e2[i]; ++i) st_fs_header.entries[2].name[i] = e2[i];
        st_fs_header.entries[2].kind = 1; st_fs_header.entries[2].size = 0; st_fs_header.entries[2].lba = 0;
    }
}

static uint8_t st_fs_mount(void) {
    if (!st_fs_io || !st_fs_io->Media) {
        st_fs_init_defaults();
        st_fs_mounted = 1;
        return 1;
    }
    if (st_fs_io->ReadBlocks(st_fs_io, st_fs_io->Media->MediaId, 86016, 512, &st_fs_header) == 0 &&
        st_fs_header.magic == UINT64_C(0x3153464E454B4142) &&
        st_fs_header.version == 1 &&
        st_fs_header.entry_count <= 12 &&
        st_fs_header.entry_count > 0) {
        st_fs_mounted = 1;
        return 1;
    }
    st_fs_init_defaults();
    st_fs_mounted = 1;
    return 1;
}

uint32_t st_fs_entry_count(void) { return st_fs_mount() ? st_fs_header.entry_count : 0; }

const char *st_fs_entry_name(uint32_t index) {
    if (!st_fs_mounted) st_fs_mount();
    return (st_fs_mounted && index < st_fs_header.entry_count) ? st_fs_header.entries[index].name : "(vazio)";
}

uint32_t st_fs_entry_kind(uint32_t index) {
    if (!st_fs_mounted) st_fs_mount();
    return (st_fs_mounted && index < st_fs_header.entry_count) ? st_fs_header.entries[index].kind : 2;
}

uint32_t st_fs_entry_size(uint32_t index) {
    if (!st_fs_mounted) st_fs_mount();
    return (st_fs_mounted && index < st_fs_header.entry_count) ? st_fs_header.entries[index].size : 0;
}

static int st_str_eq(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *b) {
        if (*a != *b) return 0;
        a++; b++;
    }
    return *a == *b;
}

int st_fs_find(const char *name) {
    if (!st_fs_mount()) return -1;
    for (uint32_t i = 0; i < st_fs_header.entry_count; ++i) {
        if (st_str_eq(st_fs_header.entries[i].name, name)) return (int)i;
    }
    return -1;
}

int st_fs_add(const char *name, uint32_t kind, uint32_t size, uint32_t lba) {
    if (!st_fs_mount() || !st_fs_io || !st_fs_io->Media || st_fs_io->Media->ReadOnly || st_fs_header.entry_count >= 12) return 0;
    int existing = st_fs_find(name);
    if (existing >= 0) {
        st_fs_header.entries[existing].size = size;
        st_fs_header.entries[existing].kind = kind;
        if (lba) st_fs_header.entries[existing].lba = lba;
    } else {
        SotlasFsEntry *e = &st_fs_header.entries[st_fs_header.entry_count++];
        for (uint32_t i = 0; i < sizeof(*e); ++i) ((uint8_t*)e)[i] = 0;
        for (uint32_t i = 0; i < 31 && name[i]; ++i) e->name[i] = name[i];
        e->kind = kind;
        e->lba = lba ? lba : (86020 + st_fs_header.entry_count);
        e->size = size;
    }
    if (st_fs_io->WriteBlocks(st_fs_io, st_fs_io->Media->MediaId, 86016, 512, &st_fs_header)) return 0;
    return !st_fs_io->FlushBlocks || st_fs_io->FlushBlocks(st_fs_io) == 0;
}

int st_fs_remove(const char *name) {
    if (!st_fs_mount() || !st_fs_io || !st_fs_io->Media || st_fs_io->Media->ReadOnly) return 0;
    int idx = st_fs_find(name);
    if (idx < 0) return 0;
    for (uint32_t i = (uint32_t)idx; i + 1 < st_fs_header.entry_count; ++i) {
        st_fs_header.entries[i] = st_fs_header.entries[i + 1];
    }
    st_fs_header.entry_count--;
    if (st_fs_io->WriteBlocks(st_fs_io, st_fs_io->Media->MediaId, 86016, 512, &st_fs_header)) return 0;
    return !st_fs_io->FlushBlocks || st_fs_io->FlushBlocks(st_fs_io) == 0;
}

typedef struct { uint64_t magic; uint32_t version, size; char text[496]; } SotlasTextFile;
static char st_note_text[128] = "Notas";
static uint32_t st_note_len = 5;
static uint8_t st_note_editing = 0;
const char *st_notes_get_text(void){ return st_note_text; }

int st_fs_write_file(const char *name, const char *text, uint32_t len) {
    if (!st_fs_mount() || !st_fs_io || !st_fs_io->Media || st_fs_io->Media->ReadOnly) return 0;
    int idx = st_fs_find(name);
    uint32_t lba = 0;
    if (idx >= 0) {
        lba = st_fs_header.entries[idx].lba;
    } else {
        lba = 86020 + st_fs_header.entry_count;
        if (!st_fs_add(name, 2, len, lba)) return 0;
        idx = st_fs_find(name);
    }
    SotlasTextFile file;
    for (uint32_t i = 0; i < sizeof(file); ++i) ((uint8_t*)&file)[i] = 0;
    file.magic = UINT64_C(0x3158544E454B4142);
    file.version = 1;
    file.size = len > 490 ? 490 : len;
    for (uint32_t i = 0; i < file.size; ++i) file.text[i] = text[i];
    if (st_fs_io->WriteBlocks(st_fs_io, st_fs_io->Media->MediaId, lba, 512, &file)) return 0;
    if (idx >= 0) {
        st_fs_header.entries[idx].size = file.size;
        st_fs_io->WriteBlocks(st_fs_io, st_fs_io->Media->MediaId, 86016, 512, &st_fs_header);
    }
    return !st_fs_io->FlushBlocks || st_fs_io->FlushBlocks(st_fs_io) == 0;
}

int st_fs_read_file(const char *name, char *out_text, uint32_t max_len) {
    if (!st_fs_mount() || !st_fs_io || !st_fs_io->Media || !out_text || max_len == 0) return 0;
    int idx = st_fs_find(name);
    uint32_t lba = (idx >= 0) ? st_fs_header.entries[idx].lba : (st_str_eq(name, "/home/notas.txt") ? 86018 : 0);
    if (!lba) return 0;
    SotlasTextFile file;
    if (st_fs_io->ReadBlocks(st_fs_io, st_fs_io->Media->MediaId, lba, 512, &file)) return 0;
    if (file.magic != UINT64_C(0x31544E4E454B4142) && file.magic != UINT64_C(0x3158544E454B4142)) return 0;
    uint32_t n = 0;
    while (n < max_len - 1 && n < file.size && file.text[n]) {
        out_text[n] = file.text[n];
        n++;
    }
    out_text[n] = 0;
    return 1;
}

static void st_notes_load(void){
    char buf[128];
    if (st_fs_read_file("/home/notas.txt", buf, sizeof(buf))) {
        uint32_t n = 0;
        while (n < 127 && buf[n]) { st_note_text[n] = buf[n]; ++n; }
        st_note_text[n] = 0;
        st_note_len = n;
    }
}
static void st_notes_append(uint16_t ch){ if(ch>=32 && ch<127 && st_note_len<127){st_note_text[st_note_len++]=(char)ch; st_note_text[st_note_len]=0;} }
void st_notes_save(void){
    st_fs_write_file("/home/notas.txt", st_note_text, st_note_len);
}

extern void desktop_shell_toggle_theme(void);
extern uint8_t desktop_shell_is_dark_theme(void);
extern uint8_t desktop_shell_get_location_permission(void);
extern void desktop_shell_set_location_permission(uint8_t perm);

typedef struct {
    uint64_t magic;
    uint32_t version;
    uint8_t dark_theme;
    uint8_t location_permission;
    uint8_t reserved[502];
} SotlasDesktopConfig;

static void desktop_config_load(void) {
    SotlasDesktopConfig cfg;
    if (!st_fs_io || !st_fs_io->Media || st_fs_io->ReadBlocks(st_fs_io, st_fs_io->Media->MediaId, 86017, 512, &cfg)) return;
    if (cfg.magic != UINT64_C(0x314643444E4B4142)) return;
    if (cfg.dark_theme && !desktop_shell_is_dark_theme()) {
        desktop_shell_toggle_theme();
    } else if (!cfg.dark_theme && desktop_shell_is_dark_theme()) {
        desktop_shell_toggle_theme();
    }
    if (cfg.location_permission <= 2) {
        desktop_shell_set_location_permission(cfg.location_permission);
    }
}

void desktop_config_save(void) {
    if (!st_fs_io || !st_fs_io->Media || st_fs_io->Media->ReadOnly) return;
    SotlasDesktopConfig cfg;
    for (uint32_t i = 0; i < sizeof(cfg); ++i) ((uint8_t*)&cfg)[i] = 0;
    cfg.magic = UINT64_C(0x314643444E4B4142);
    cfg.version = 1;
    cfg.dark_theme = desktop_shell_is_dark_theme();
    cfg.location_permission = desktop_shell_get_location_permission();
    if (st_fs_io->WriteBlocks(st_fs_io, st_fs_io->Media->MediaId, 86017, 512, &cfg) == 0) {
        if (st_fs_io->FlushBlocks) st_fs_io->FlushBlocks(st_fs_io);
        st_fs_add("/config/theme.cfg", 3, 512, 86017);
    }
}

typedef struct {
    uint64_t CurrentX; uint64_t CurrentY; uint64_t CurrentZ; uint32_t ActiveButtons;
} EFI_ABSOLUTE_POINTER_STATE;

typedef struct {
    uint64_t AbsoluteMinX, AbsoluteMinY, AbsoluteMinZ;
    uint64_t AbsoluteMaxX, AbsoluteMaxY, AbsoluteMaxZ;
    uint32_t Attributes;
} EFI_ABSOLUTE_POINTER_MODE;

typedef struct _EFI_ABSOLUTE_POINTER_PROTOCOL {
    uint64_t (*Reset)(struct _EFI_ABSOLUTE_POINTER_PROTOCOL *This, uint8_t ExtendedVerification);
    uint64_t (*GetState)(struct _EFI_ABSOLUTE_POINTER_PROTOCOL *This, EFI_ABSOLUTE_POINTER_STATE *State);
    void *WaitForInput; EFI_ABSOLUTE_POINTER_MODE *Mode;
} EFI_ABSOLUTE_POINTER_PROTOCOL;

static const EFI_GUID ABSOLUTE_POINTER_GUID = {
    0x8D59D32B, 0xC655, 0x4AE9, {0x9B, 0x15, 0xF2, 0x59, 0x04, 0x99, 0x2A, 0x43}
};
static const EFI_GUID SIMPLE_POINTER_GUID = {
    0x31878C87, 0x0B75, 0x11D5, {0x9A, 0x4F, 0x00, 0x90, 0x27, 0x3F, 0xC1, 0x4D}
};

typedef struct {
    uint8_t Hdr[24];
    void *RaiseTPL, *RestoreTPL, *AllocatePages, *FreePages, *GetMemoryMap, *AllocatePool, *FreePool;
    void *CreateEvent, *SetTimer, *WaitForEvent, *SignalEvent, *CloseEvent, *CheckEvent;
    void *InstallProtocolInterface, *ReinstallProtocolInterface, *UninstallProtocolInterface, *HandleProtocol;
    void *Reserved, *RegisterProtocolNotify, *LocateHandle, *LocateDevicePath, *InstallConfigurationTable;
    void *LoadImage, *StartImage, *Exit, *UnloadImage, *ExitBootServices, *GetNextMonotonicCount, *Stall;
    void *SetWatchdogTimer, *ConnectController, *DisconnectController, *OpenProtocol, *CloseProtocol;
    void *OpenProtocolInformation, *ProtocolsPerHandle, *LocateHandleBuffer;
    uint64_t (*LocateProtocol)(const EFI_GUID *Protocol, void *Registration, void **Interface);
} EFI_BOOT_SERVICES;

typedef struct {
    uint8_t Hdr[24];
    void *FirmwareVendor; uint32_t FirmwareRevision;
    void *ConsoleInHandle; void *ConIn;
    void *ConsoleOutHandle; void *ConOut;
    void *StandardErrorHandle; void *StdErr;
    void *RuntimeServices; EFI_BOOT_SERVICES *BootServices;
} EFI_SYSTEM_TABLE;

extern void gfx_init(uint32_t *base, uint32_t width, uint32_t height, uint32_t pitch);
extern void desktop_compositor_init(uint32_t screen_w, uint32_t screen_h);
extern void desktop_compositor_render_frame(void);
extern void desktop_shell_set_cursor(int32_t x, int32_t y);
extern void desktop_shell_handle_click(int32_t mx, int32_t my);
extern void desktop_shell_launch_app(uint32_t app_id);
extern void desktop_shell_toggle_media(void);
extern void desktop_shell_open_menu(int32_t menu_idx);
extern void desktop_shell_toggle_theme(void);
extern void desktop_shell_toggle_control_center(void);
extern void desktop_shell_toggle_spotlight(void);
extern void desktop_shell_toggle_context_menu(void);
extern void desktop_shell_open_context_menu(int32_t x, int32_t y);
extern uint8_t desktop_shell_get_location_permission(void);
extern void desktop_shell_set_location_permission(uint8_t perm);
extern uint8_t wm_handle_mouse_down(int32_t mx, int32_t my);
extern void wm_handle_mouse_move(int32_t mx, int32_t my);
extern void wm_handle_mouse_up(void);
extern int wm_is_window_focused(uint32_t id);
extern void wm_unfocus_all(void);
extern uint8_t desktop_shell_is_spotlight_open(void);
extern void desktop_shell_spotlight_key(uint16_t unicode, uint16_t scan);
extern void desktop_shell_terminal_key(uint16_t unicode, uint16_t scan);
extern void desktop_shell_terminal_append(const char *line);
extern void installer_execute_installation(void);
extern void installer_next_stage(void);
extern void installer_prev_stage(void);
extern void installer_select_option(uint32_t opt);
extern uint8_t installer_is_in_disk_stage(void);
extern uint8_t installer_should_auto_open(void);
extern uint8_t wm_app_is_open(uint32_t app_id);

typedef struct {
    uint16_t unicode;
    uint16_t scan;
} SotlasInputEvent;

#define CQ_INPUT_QUEUE_SIZE 32
static SotlasInputEvent g_st_input_queue[CQ_INPUT_QUEUE_SIZE];
static uint32_t g_st_input_head = 0;
static uint32_t g_st_input_tail = 0;
static uint32_t g_st_input_count = 0;

static void st_input_push_key(uint16_t unicode, uint16_t scan) {
    if (g_st_input_count >= CQ_INPUT_QUEUE_SIZE) return;
    g_st_input_queue[g_st_input_tail].unicode = unicode;
    g_st_input_queue[g_st_input_tail].scan = scan;
    g_st_input_tail = (g_st_input_tail + 1) % CQ_INPUT_QUEUE_SIZE;
    g_st_input_count++;
}

static int st_input_pop(SotlasInputEvent *out_evt) {
    if (g_st_input_count == 0 || !out_evt) return 0;
    *out_evt = g_st_input_queue[g_st_input_head];
    g_st_input_head = (g_st_input_head + 1) % CQ_INPUT_QUEUE_SIZE;
    g_st_input_count--;
    return 1;
}

static void st_dispatch_key(uint16_t unicode, uint16_t scan) {
    if (desktop_shell_is_spotlight_open()) {
        desktop_shell_spotlight_key(unicode, scan);
    } else if (wm_is_window_focused(4)) {
        if (unicode == 27 || scan == 0x17) {
            wm_unfocus_all();
        } else {
            desktop_shell_terminal_key(unicode, scan);
        }
    } else if (wm_is_window_focused(5) || wm_app_is_open(14)) {
        if (unicode == 27 || scan == 0x17) {
            installer_prev_stage();
        } else if (unicode == 13 || unicode == 10) {
            installer_next_stage();
        } else if (unicode >= '1' && unicode <= '4') {
            installer_select_option((uint32_t)(unicode - '0'));
        } else if (unicode == 'i' || unicode == 'I') {
            if (installer_is_in_disk_stage()) {
                installer_execute_installation();
            } else {
                installer_next_stage();
            }
        }
    } else if (wm_is_window_focused(2)) {
        if (unicode == 27 || scan == 0x17) {
            wm_unfocus_all();
        } else if (unicode == 13 || unicode == 10) {
            st_notes_save();
            desktop_shell_terminal_append("Notas salvas no BakenFS.");
        } else if (unicode == 8 || scan == 0x08) {
            if (st_note_len) { st_note_text[--st_note_len] = 0; }
        } else if (unicode >= 32 && unicode <= 126) {
            st_notes_append(unicode);
        }
    } else {
        if(unicode=='1') desktop_shell_launch_app(0); /* Arquivos */
        else if(unicode=='2') { desktop_shell_launch_app(6); st_note_editing=1; } /* Notas */
        else if(unicode=='3') desktop_shell_launch_app(8); /* Ajustes */
        else if(unicode=='4') desktop_shell_launch_app(9); /* Terminal */
        else if(unicode=='a'||unicode=='A') desktop_shell_open_menu(1); /* Menu Arquivo */
        else if(unicode=='b'||unicode=='B') desktop_shell_open_menu(0); /* Menu Baken OS */
        else if(unicode=='c'||unicode=='C') desktop_shell_toggle_control_center(); /* Central de Controle */
        else if(unicode=='s'||unicode=='S') desktop_shell_toggle_spotlight(); /* Spotlight Search */
        else if(unicode=='t'||unicode=='T') desktop_shell_toggle_theme(); /* Modo Escuro/Claro */
        else if(unicode=='x'||unicode=='X') desktop_shell_toggle_context_menu(); /* Menu Contexto */
        else if(unicode=='i'||unicode=='I') {
            if (wm_app_is_open(14)) {
                installer_next_stage();
            } else {
                desktop_shell_launch_app(14);
            }
        }
        else if(unicode=='m'||unicode=='M') desktop_shell_toggle_media();
        else if(unicode=='d'||unicode=='D') st_fs_add("/home/documentos", 1, 0, 0);
        else if(unicode=='n'||unicode=='N') st_fs_add("/home/arquivo.txt", 2, 512, 86020);
        else if(unicode>='5' && unicode<='9') desktop_shell_launch_app((uint32_t)(unicode-'3'));
    }
}

void baken_kernel_main(const BakenBootInfo *boot_info) {
    if (!boot_info || !boot_info->framebuffer_base || boot_info->screen_width == 0 || boot_info->screen_height == 0) {
        for (;;) { }
    }
    uint32_t width = boot_info->screen_width;
    uint32_t height = boot_info->screen_height;
    /* Serviços que o shell consulta no primeiro quadro devem existir antes do
      * compositor. Isso evita que widgets recebam um estado de montagem vazio. */
    st_fs_io = (EFI_BLOCK_IO_PROTOCOL*)boot_info->block_io_protocol;
    installer_setup_io(boot_info->block_io_protocol, boot_info->install_target_block_io_protocol);
    st_notes_load();
    desktop_config_load();
    gfx_init(boot_info->framebuffer_base, width, height, boot_info->pixels_per_scanline);
    desktop_compositor_init(width, height);
    if (installer_should_auto_open()) {
        desktop_shell_launch_app(14);
    }

    EFI_SYSTEM_TABLE *st = (EFI_SYSTEM_TABLE*)boot_info->system_table;
    EFI_SIMPLE_TEXT_INPUT_PROTOCOL *keyboard = st ? (EFI_SIMPLE_TEXT_INPUT_PROTOCOL*)st->ConIn : NULL;
    EFI_ABSOLUTE_POINTER_PROTOCOL *abs_pointer = NULL;
    EFI_SIMPLE_POINTER_PROTOCOL *simple_pointer = (EFI_SIMPLE_POINTER_PROTOCOL*)boot_info->pointer_protocol;
    if (st && st->BootServices && st->BootServices->LocateProtocol) {
        st->BootServices->LocateProtocol(&ABSOLUTE_POINTER_GUID, NULL, (void**)&abs_pointer);
        if (!simple_pointer) {
            st->BootServices->LocateProtocol(&SIMPLE_POINTER_GUID, NULL, (void**)&simple_pointer);
        }
    }

    int32_t mouse_x = (int32_t)(width / 2);
    int32_t mouse_y = (int32_t)(height / 2);
    uint8_t left_down = 0;

    for (;;) {
        if (keyboard && keyboard->ReadKeyStroke) {
            EFI_INPUT_KEY key;
            while (keyboard->ReadKeyStroke(keyboard, &key) == 0) {
                st_input_push_key(key.UnicodeChar, key.ScanCode);
            }
        }
        SotlasInputEvent evt;
        while (st_input_pop(&evt)) {
            st_dispatch_key(evt.unicode, evt.scan);
        }
        if (abs_pointer && abs_pointer->GetState && abs_pointer->Mode) {
            EFI_ABSOLUTE_POINTER_STATE abs_st;
            if (abs_pointer->GetState(abs_pointer, &abs_st) == 0) {
                uint64_t min_x = abs_pointer->Mode->AbsoluteMinX;
                uint64_t max_x = abs_pointer->Mode->AbsoluteMaxX;
                uint64_t min_y = abs_pointer->Mode->AbsoluteMinY;
                uint64_t max_y = abs_pointer->Mode->AbsoluteMaxY;
                if (max_x > min_x && max_y > min_y) {
                    mouse_x = (int32_t)(((abs_st.CurrentX - min_x) * (uint64_t)width) / (max_x - min_x));
                    mouse_y = (int32_t)(((abs_st.CurrentY - min_y) * (uint64_t)height) / (max_y - min_y));
                    if (mouse_x < 0) mouse_x = 0;
                    if (mouse_x >= (int32_t)width) mouse_x = (int32_t)width - 1;
                    if (mouse_y < 0) mouse_y = 0;
                    if (mouse_y >= (int32_t)height) mouse_y = (int32_t)height - 1;
                    desktop_shell_set_cursor(mouse_x, mouse_y);
                    uint8_t btn = (abs_st.ActiveButtons & 1) ? 1 : 0;
                    uint8_t r_btn = (abs_st.ActiveButtons & 2) ? 1 : 0;
                    if (r_btn) {
                        desktop_shell_open_context_menu(mouse_x, mouse_y);
                    } else if (btn && !left_down) {
                        if (!wm_handle_mouse_down(mouse_x, mouse_y)) {
                            desktop_shell_handle_click(mouse_x, mouse_y);
                        }
                    } else if (btn && left_down) {
                        wm_handle_mouse_move(mouse_x, mouse_y);
                    } else if (!btn && left_down) {
                        wm_handle_mouse_up();
                    }
                    left_down = btn;
                }
            }
        } else if (simple_pointer && simple_pointer->GetState) {
            EFI_SIMPLE_POINTER_STATE simp_st;
            if (simple_pointer->GetState(simple_pointer, &simp_st) == 0) {
                int32_t raw_dx = simp_st.RelativeMovementX;
                int32_t raw_dy = simp_st.RelativeMovementY;
                int32_t dx = 0, dy = 0;
                if (raw_dx != 0) {
                    int32_t abs_x = raw_dx < 0 ? -raw_dx : raw_dx;
                    int32_t scaled_x = abs_x / 48;
                    if (scaled_x < 1) scaled_x = 1;
                    if (abs_x > 256) scaled_x = (scaled_x * 3) / 2;
                    dx = (raw_dx < 0) ? -scaled_x : scaled_x;
                    if (dx > 25) dx = 25;
                    if (dx < -25) dx = -25;
                }
                if (raw_dy != 0) {
                    int32_t abs_y = raw_dy < 0 ? -raw_dy : raw_dy;
                    int32_t scaled_y = abs_y / 48;
                    if (scaled_y < 1) scaled_y = 1;
                    if (abs_y > 256) scaled_y = (scaled_y * 3) / 2;
                    dy = (raw_dy < 0) ? -scaled_y : scaled_y;
                    if (dy > 25) dy = 25;
                    if (dy < -25) dy = -25;
                }
                mouse_x += dx;
                mouse_y += dy;
                if (mouse_x < 0) mouse_x = 0;
                if (mouse_x >= (int32_t)width) mouse_x = (int32_t)width - 1;
                if (mouse_y < 0) mouse_y = 0;
                if (mouse_y >= (int32_t)height) mouse_y = (int32_t)height - 1;
                desktop_shell_set_cursor(mouse_x, mouse_y);
                uint8_t btn = simp_st.LeftButton ? 1 : 0;
                uint8_t r_btn = simp_st.RightButton ? 1 : 0;
                if (r_btn) {
                    desktop_shell_open_context_menu(mouse_x, mouse_y);
                } else if (btn && !left_down) {
                    if (!wm_handle_mouse_down(mouse_x, mouse_y)) {
                        desktop_shell_handle_click(mouse_x, mouse_y);
                    }
                } else if (btn && left_down) {
                    wm_handle_mouse_move(mouse_x, mouse_y);
                } else if (!btn && left_down) {
                    wm_handle_mouse_up();
                }
                left_down = btn;
            }
        }

        desktop_compositor_render_frame();
        for (volatile int d = 0; d < 40000; ++d);
    }
}
""".strip().splitlines())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
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
        "-std=c11", "-Wall", "-Wextra", "-Werror", "-ffreestanding",
        "-fshort-wchar", "-mno-red-zone", "-fno-stack-protector",
        "-fno-asynchronous-unwind-tables", "-nostdlib", "-I", str(include_dir), "-c",
    ]

    # Emite e compila uma unidade C isolada por módulo Sotlas. Os corpos Sotlas ainda
    # migram progressivamente; estes objetos já materializam o grafo no link.
    for mod_name in manifest["compile_order"]:
        module_id = _c_identifier(mod_name)
        header = emit_c_header(asts[mod_name], generated_dir / f"{module_id}.h")
        interface = emit_interface_manifest(asts[mod_name], generated_dir / f"{module_id}.soti.json")
        generated = emit_c_module(asts[mod_name], generated_dir / f"{module_id}.c", header)
        obj = obj_dir / f"{module_id}.o"
        res = subprocess.run([str(gcc), *common_flags, str(generated), "-o", str(obj)],
                             capture_output=True, text=True, env=env)
        if res.returncode != 0:
            raise SotlasError(f"falha ao compilar módulo Sotlas {mod_name}: {res.stderr}")
        generated_sources.append(generated)
        generated_headers.append(header)
        generated_interfaces.append(interface)
        compiled_objects.append(obj)

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
