#!/usr/bin/env python3
"""Servidor LSP Sotlas Bootstrap: autocompletion, go-to-definition, hover e document symbols.

Sem dependências externas além da biblioteca padrão do Python. Compartilha
o parser e sistema de tipos do compilador Sotlas Bootstrap (bootstrap.py).
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse

_SOTLAS_COMPILE_DIR = str(Path(__file__).resolve().parent)
if _SOTLAS_COMPILE_DIR not in sys.path:
    sys.path.insert(0, _SOTLAS_COMPILE_DIR)

from bootstrap import (
    KEYWORDS,
    PRIMITIVES,
    SotlasBootstrapError,
    Enum,
    EnumVariant,
    FieldDef,
    Function,
    Global,
    Module,
    Number,
    Struct,
    Token,
    Type,
    check,
    parse,
)


def uri_to_path(uri: str) -> Path | None:
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        path_str = unquote(parsed.path)
        if sys.platform == "win32" and path_str.startswith("/") and len(path_str) > 2 and path_str[2] == ":":
            path_str = path_str[1:]
        return Path(path_str)
    return None


def path_to_uri(path: Path) -> str:
    return path.resolve().as_uri()


class SotlasLanguageServer:
    def __init__(self):
        self.documents: dict[str, str] = {}
        self.parsed_modules: dict[str, Module] = {}
        self.last_valid_modules: dict[str, Module] = {}
        self.workspace_root: Path | None = None

    def _extract_heuristic(self, source: str, uri: str) -> Module:
        """Extrai símbolos por heurística quando o código contém erros sintáticos durante digitação."""
        mod_name = "unknown"
        m = re.search(r"\bmodule\s+([A-Za-z0-9_:]+)\s*;", source)
        if m:
            mod_name = m.group(1)

        imports = [im.group(1) for im in re.finditer(r"\bimport\s+([A-Za-z0-9_:]+)::\*\s*;", source)]

        enums = []
        for em in re.finditer(r"\b(?:pub\s+)?enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}", source):
            ename = em.group(1)
            body = em.group(2)
            variants = []
            for vm in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\b(?:\s*=\s*(\d+|0x[0-9A-Fa-f]+))?", body):
                vname = vm.group(1)
                vval = int(vm.group(2), 0) if vm.group(2) else None
                variants.append(EnumVariant(vname, vval))
            enums.append(Enum(ename, variants, public=True))

        structs = []
        for sm in re.finditer(r"\b(?:pub\s+)?struct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}", source):
            sname = sm.group(1)
            body = sm.group(2)
            fields = []
            for fm in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z0-9_\[\];* ]+?)\s*;", body):
                fname = fm.group(1)
                ftype_str = fm.group(2).strip()
                fields.append(FieldDef(fname, Type(ftype_str)))
            structs.append(Struct(sname, fields, public=True))

        functions = []
        for fm in re.finditer(r"\b(?:pub\s+)?(?:@system\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)(?:\s*->\s*([A-Za-z0-9_]+))?", source):
            fname = fm.group(1)
            params_raw = fm.group(2)
            ret_str = fm.group(3) or "void"
            params = []
            if params_raw.strip():
                for pm in params_raw.split(","):
                    if ":" in pm:
                        pname, ptyp = pm.split(":", 1)
                        params.append((pname.strip(), Type(ptyp.strip())))
            functions.append(Function(fname, params, Type(ret_str), [], public=True))

        classes = []
        for cm in re.finditer(r"\b(?:pub\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{([^}]*)\}", source):
            cname = cm.group(1)
            cbody = cm.group(2)
            cfields = []
            cmethods = []
            for fm in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z0-9_\[\];* ]+?)\s*;", cbody):
                fname = fm.group(1)
                ftype_str = fm.group(2).strip()
                cfields.append(FieldDef(fname, Type(ftype_str)))
            for mm in re.finditer(r"\b(?:pub\s+)?(?:@system\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)(?:\s*->\s*([A-Za-z0-9_]+))?", cbody):
                mname = mm.group(1)
                mparams_raw = mm.group(2)
                mret_str = mm.group(3) or "void"
                mparams = []
                if mparams_raw.strip():
                    for pm in mparams_raw.split(","):
                        if ":" in pm:
                            pname, ptyp = pm.split(":", 1)
                            mparams.append((pname.strip(), Type(ptyp.strip())))
                mfn = Function(f"{cname}_{mname}", mparams, Type(mret_str), [], public=True)
                cmethods.append(mfn)
                functions.append(mfn)
            cls_obj = Class(cname, cfields, cmethods, public=True)
            classes.append(cls_obj)
            structs.append(Struct(cname, cfields, public=True))

        globals_list = []
        for gm in re.finditer(r"\b(?:pub\s+)?(const|static)\s+(?:mut\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z0-9_]+)", source):
            is_const = (gm.group(1) == "const")
            gname = gm.group(2)
            gtype = gm.group(3)
            globals_list.append(Global(gname, Type(gtype), Number(Token("NUMBER", "0", 1, 1), "0"), is_const=is_const, is_mut=not is_const, public=True))

        return Module(
            name=mod_name,
            imports=imports,
            structs=structs,
            classes=classes,
            enums=enums,
            globals=globals_list,
            functions=functions,
            filename=uri,
            source=source
        )

    def find_project_modules(self, current_file: Path | None) -> dict[str, tuple[Module, Path]]:
        """Descobre todos os módulos .st no projeto a partir do arquivo atual."""
        project_modules: dict[str, tuple[Module, Path]] = {}
        if not current_file or not current_file.exists():
            return project_modules
        root = current_file.parent
        while root.parent != root and not (root / "core").is_dir():
            root = root.parent
        for path in root.rglob("*.st"):
            try:
                text = path.read_text(encoding="utf-8")
                try:
                    mod = parse(text, filename=str(path))
                except Exception:
                    mod = self._extract_heuristic(text, str(path))
                project_modules[mod.name] = (mod, path)
            except Exception:
                pass
        return project_modules

    def validate(self, uri: str, source: str) -> list[dict]:
        self.documents[uri] = source
        diagnostics = []
        file_path = uri_to_path(uri)
        try:
            mod = parse(source, filename=str(file_path) if file_path else None)
            self.parsed_modules[uri] = mod
            self.last_valid_modules[uri] = mod
            # Descobre dependências importadas
            imported_fns: dict[str, Function] = {}
            imported_types: dict[str, Struct] = {}
            imported_enums: dict[str, Enum] = {}
            imported_globals: dict[str, Global] = {}
            if file_path:
                project_mods = self.find_project_modules(file_path)
                for dep_name in mod.imports:
                    if dep_name in project_mods:
                        dep_mod, _ = project_mods[dep_name]
                        imported_fns.update({fn.name: fn for fn in dep_mod.functions if fn.public})
                        imported_types.update({s.name: s for s in dep_mod.structs if s.public})
                        imported_enums.update({e.name: e for e in dep_mod.enums if e.public})
                        imported_globals.update({g.name: g for g in dep_mod.globals if g.public})
            check(mod, imported_fns, imported_types, imported_enums, imported_globals)
        except SotlasBootstrapError as error:
            # Fallback para extração heurística para não perder símbolos
            self.parsed_modules[uri] = self.last_valid_modules.get(uri) or self._extract_heuristic(source, uri)
            diagnostics.append({
                "range": {
                    "start": {"line": max(0, error.line - 1), "character": max(0, error.column - 1)},
                    "end": {"line": max(0, error.line - 1), "character": max(0, error.column + 5)},
                },
                "severity": 1,
                "source": "bootstrap",
                "message": error.message,
            })
        except Exception:
            self.parsed_modules[uri] = self.last_valid_modules.get(uri) or self._extract_heuristic(source, uri)
        return diagnostics

    def get_word_at(self, source: str, line: int, character: int) -> str:
        lines = source.splitlines()
        if line >= len(lines):
            return ""
        curr_line = lines[line]
        if character > len(curr_line):
            return ""
        # Procura delimitadores de palavra
        start = character
        while start > 0 and (curr_line[start - 1].isalnum() or curr_line[start - 1] in "_:"):
            start -= 1
        end = character
        while end < len(curr_line) and (curr_line[end].isalnum() or curr_line[end] in "_:"):
            end += 1
        return curr_line[start:end]

    def completion(self, uri: str, line: int, character: int) -> list[dict]:
        source = self.documents.get(uri, "")
        lines = source.splitlines()
        prefix_line = lines[line][:character] if line < len(lines) else ""
        items = []

        # 1. Atributos: se digitou '@'
        if prefix_line.endswith("@") or "@" in prefix_line.split()[-1:]:
            for attr, doc in [("@repr(C)", "Representação compatível com C"),
                              ("@packed", "Alinhamento compacto de 1 byte sem padding"),
                              ("@export", "Exporta símbolo ABI C não-mangled"),
                              ("@system", "Permite acesso irrestrito a hardware e ponteiros"),
                              ("@inline", "Sugere inlining pelo compilador C")]:
                items.append({
                    "label": attr,
                    "kind": 15,  # Snippet
                    "detail": "Atributo Sotlas Bootstrap",
                    "documentation": doc,
                    "insertText": attr[1:] if prefix_line.endswith("@") else attr,
                })
            return items

        # 2. Variantes de Enum: se digitou 'EnumName::'
        match_enum = re.search(r"([A-Za-z_][A-Za-z0-9_]*)::$", prefix_line)
        if match_enum:
            enum_name = match_enum.group(1)
            file_path = uri_to_path(uri)
            all_enums: dict[str, Enum] = {}
            if uri in self.parsed_modules:
                all_enums.update({e.name: e for e in self.parsed_modules[uri].enums})
            if file_path:
                project_mods = self.find_project_modules(file_path)
                for dep_mod, _ in project_mods.values():
                    all_enums.update({e.name: e for e in dep_mod.enums if e.public})
            if enum_name in all_enums:
                enum_obj = all_enums[enum_name]
                for v in enum_obj.variants:
                    val_doc = f" = {v.value}" if v.value is not None else ""
                    items.append({
                        "label": v.name,
                        "kind": 20,  # EnumMember
                        "detail": f"Variante de {enum_name}{val_doc}",
                        "documentation": f"{enum_name}::{v.name}",
                    })
                return items

        # 3. Campos de Struct: se digitou 'obj.'
        match_dot = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\.$", prefix_line)
        if match_dot:
            # Lista campos de todas as structs conhecidas
            file_path = uri_to_path(uri)
            all_structs: dict[str, Struct] = {}
            if uri in self.parsed_modules:
                all_structs.update({s.name: s for s in self.parsed_modules[uri].structs})
            if file_path:
                project_mods = self.find_project_modules(file_path)
                for dep_mod, _ in project_mods.values():
                    all_structs.update({s.name: s for s in dep_mod.structs if s.public})
            for sname, sobj in all_structs.items():
                for fld in sobj.fields:
                    items.append({
                        "label": fld.name,
                        "kind": 5,  # Field
                        "detail": f"{fld.type.name} (campo de {sname})",
                    })
            return items

        # 4. Palavras-chave
        for kw in sorted(KEYWORDS):
            items.append({
                "label": kw,
                "kind": 14,  # Keyword
                "detail": "Palavra-chave Sotlas Bootstrap",
            })

        # 5. Tipos Primitivos
        for prim in sorted(PRIMITIVES):
            items.append({
                "label": prim,
                "kind": 7,  # Class / Type
                "detail": "Tipo Primitivo Sotlas Bootstrap",
            })

        # 6. Símbolos do Módulo Atual e Módulos Importados
        file_path = uri_to_path(uri)
        all_funcs: dict[str, tuple[Function, str]] = {}
        all_structs: dict[str, tuple[Struct, str]] = {}
        all_enums: dict[str, tuple[Enum, str]] = {}
        all_globals: dict[str, tuple[Global, str]] = {}

        if uri in self.parsed_modules:
            curr_mod = self.parsed_modules[uri]
            for fn in curr_mod.functions: all_funcs[fn.name] = (fn, curr_mod.name)
            for st in curr_mod.structs: all_structs[st.name] = (st, curr_mod.name)
            for en in curr_mod.enums: all_enums[en.name] = (en, curr_mod.name)
            for gl in curr_mod.globals: all_globals[gl.name] = (gl, curr_mod.name)

        if file_path:
            project_mods = self.find_project_modules(file_path)
            for dep_mod, _ in project_mods.values():
                for fn in dep_mod.functions:
                    if fn.public: all_funcs[fn.name] = (fn, dep_mod.name)
                for st in dep_mod.structs:
                    if st.public: all_structs[st.name] = (st, dep_mod.name)
                for en in dep_mod.enums:
                    if en.public: all_enums[en.name] = (en, dep_mod.name)
                for gl in dep_mod.globals:
                    if gl.public: all_globals[gl.name] = (gl, dep_mod.name)

        for fn_name, (fn_obj, mod_origin) in all_funcs.items():
            params_str = ", ".join(f"{pname}: {ptype.name}" for pname, ptype in fn_obj.params)
            items.append({
                "label": fn_name,
                "kind": 3,  # Function
                "detail": f"fn({params_str}) -> {fn_obj.result.name} [{mod_origin}]",
                "documentation": f"Função de {mod_origin}",
            })

        for st_name, (st_obj, mod_origin) in all_structs.items():
            items.append({
                "label": st_name,
                "kind": 22,  # Struct
                "detail": f"struct {st_name} [{mod_origin}]",
            })

        for en_name, (en_obj, mod_origin) in all_enums.items():
            items.append({
                "label": en_name,
                "kind": 13,  # Enum
                "detail": f"enum {en_name} [{mod_origin}]",
            })

        for gl_name, (gl_obj, mod_origin) in all_globals.items():
            kind_str = "const" if gl_obj.is_const else "static"
            items.append({
                "label": gl_name,
                "kind": 21,  # Constant
                "detail": f"{kind_str} {gl_name}: {gl_obj.type.name} [{mod_origin}]",
            })

        return items

    def hover(self, uri: str, line: int, character: int) -> dict | None:
        source = self.documents.get(uri, "")
        word = self.get_word_at(source, line, character)
        if not word:
            return None

        # Trata Enum::Variant
        if "::" in word:
            parts = word.split("::")
            if len(parts) == 2:
                enum_name, var_name = parts
                file_path = uri_to_path(uri)
                if file_path:
                    project_mods = self.find_project_modules(file_path)
                    for dep_mod, _ in project_mods.values():
                        for en in dep_mod.enums:
                            if en.name == enum_name:
                                for v in en.variants:
                                    if v.name == var_name:
                                        val_str = f" = {v.value}" if v.value is not None else ""
                                        return {"contents": {"kind": "markdown", "value": f"```st\n{enum_name}::{var_name}{val_str}\n```\n*Variante do enum `{enum_name}`*"}}

        # Procura funções, structs, enums ou variáveis
        file_path = uri_to_path(uri)
        all_mods: list[Module] = []
        if uri in self.parsed_modules:
            all_mods.append(self.parsed_modules[uri])
        if file_path:
            project_mods = self.find_project_modules(file_path)
            all_mods.extend(mod for mod, _ in project_mods.values())

        for mod in all_mods:
            # Funções
            for fn in mod.functions:
                if fn.name == word:
                    pub_str = "pub " if fn.public else ""
                    attrs_str = " ".join(fn.attributes) + " " if fn.attributes else ""
                    params_str = ", ".join(f"{pname}: {ptype.name}" for pname, ptype in fn.params)
                    ret_str = f" -> {fn.result.name}" if fn.result.name != "void" else ""
                    sig = f"```st\n{attrs_str}{pub_str}fn {fn.name}({params_str}){ret_str}\n```\n*Módulo: `{mod.name}`*"
                    return {"contents": {"kind": "markdown", "value": sig}}

            # Structs
            for st in mod.structs:
                if st.name == word:
                    pub_str = "pub " if st.public else ""
                    attrs_str = " ".join(st.attributes) + " " if st.attributes else ""
                    fields_str = "\n".join(f"    {f.name}: {f.type.name};" for f in st.fields)
                    sig = f"```st\n{attrs_str}{pub_str}struct {st.name} {{\n{fields_str}\n}}\n```\n*Módulo: `{mod.name}`*"
                    return {"contents": {"kind": "markdown", "value": sig}}

            # Enums
            for en in mod.enums:
                if en.name == word:
                    pub_str = "pub " if en.public else ""
                    vars_str = "\n".join(f"    {v.name}" + (f" = {v.value}" if v.value is not None else "") + "," for v in en.variants)
                    sig = f"```st\n{pub_str}enum {en.name} {{\n{vars_str}\n}}\n```\n*Módulo: `{mod.name}`*"
                    return {"contents": {"kind": "markdown", "value": sig}}

            # Globals
            for gl in mod.globals:
                if gl.name == word:
                    pub_str = "pub " if gl.public else ""
                    kind_str = "const" if gl.is_const else ("static mut" if gl.is_mut else "static")
                    sig = f"```st\n{pub_str}{kind_str} {gl.name}: {gl.type.name}\n```\n*Módulo: `{mod.name}`*"
                    return {"contents": {"kind": "markdown", "value": sig}}

        # Tipos primitivos
        if word in PRIMITIVES:
            return {"contents": {"kind": "markdown", "value": f"```st\ntype {word}\n```\n*Tipo primitivo escalar Sotlas Bootstrap*"}}

        # Palavras-chave
        if word in KEYWORDS:
            return {"contents": {"kind": "markdown", "value": f"```st\nkeyword {word}\n```\n*Palavra-chave normativa Sotlas Bootstrap*"}}

        return None

    def definition(self, uri: str, line: int, character: int) -> dict | None:
        source = self.documents.get(uri, "")
        word = self.get_word_at(source, line, character)
        if not word:
            return None

        # Trata Enum::Variant
        if "::" in word:
            parts = word.split("::")
            if len(parts) == 2:
                word = parts[0]

        file_path = uri_to_path(uri)
        if not file_path:
            return None

        project_mods = self.find_project_modules(file_path)
        # Inclui o módulo atual se ainda não estiver na lista
        if uri in self.parsed_modules:
            project_mods[self.parsed_modules[uri].name] = (self.parsed_modules[uri], file_path)

        for mod, mod_path in project_mods.values():
            text = mod_path.read_text(encoding="utf-8")
            lines = text.splitlines()

            # Procura função
            for fn in mod.functions:
                if fn.name == word:
                    for l_idx, l_text in enumerate(lines):
                        if re.search(rf"\bfn\s+{word}\b", l_text):
                            col = l_text.find(word)
                            return {
                                "uri": path_to_uri(mod_path),
                                "range": {
                                    "start": {"line": l_idx, "character": col},
                                    "end": {"line": l_idx, "character": col + len(word)},
                                },
                            }

            # Procura struct
            for st in mod.structs:
                if st.name == word:
                    for l_idx, l_text in enumerate(lines):
                        if re.search(rf"\bstruct\s+{word}\b", l_text):
                            col = l_text.find(word)
                            return {
                                "uri": path_to_uri(mod_path),
                                "range": {
                                    "start": {"line": l_idx, "character": col},
                                    "end": {"line": l_idx, "character": col + len(word)},
                                },
                            }

            # Procura enum
            for en in mod.enums:
                if en.name == word:
                    for l_idx, l_text in enumerate(lines):
                        if re.search(rf"\benum\s+{word}\b", l_text):
                            col = l_text.find(word)
                            return {
                                "uri": path_to_uri(mod_path),
                                "range": {
                                    "start": {"line": l_idx, "character": col},
                                    "end": {"line": l_idx, "character": col + len(word)},
                                },
                            }

            # Procura global
            for gl in mod.globals:
                if gl.name == word:
                    for l_idx, l_text in enumerate(lines):
                        if re.search(rf"\b(?:const|static)\s+(?:mut\s+)?{word}\b", l_text):
                            col = l_text.find(word)
                            return {
                                "uri": path_to_uri(mod_path),
                                "range": {
                                    "start": {"line": l_idx, "character": col},
                                    "end": {"line": l_idx, "character": col + len(word)},
                                },
                            }

        return None

    def document_symbols(self, uri: str) -> list[dict]:
        source = self.documents.get(uri, "")
        if not source:
            return []
        lines = source.splitlines()
        symbols = []
        try:
            mod = parse(source, filename=uri)
            for fn in mod.functions:
                for idx, line_text in enumerate(lines):
                    if re.search(rf"\bfn\s+{fn.name}\b", line_text):
                        col = line_text.find(fn.name)
                        symbols.append({
                            "name": fn.name,
                            "detail": f"fn -> {fn.result.name}",
                            "kind": 12,  # Function
                            "range": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(line_text)}},
                            "selectionRange": {"start": {"line": idx, "character": col}, "end": {"line": idx, "character": col + len(fn.name)}},
                        })
                        break

            for st in mod.structs:
                for idx, line_text in enumerate(lines):
                    if re.search(rf"\bstruct\s+{st.name}\b", line_text):
                        col = line_text.find(st.name)
                        children = []
                        for fld in st.fields:
                            children.append({
                                "name": fld.name,
                                "detail": fld.type.name,
                                "kind": 8,  # Field
                                "range": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(line_text)}},
                                "selectionRange": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(fld.name)}},
                            })
                        symbols.append({
                            "name": st.name,
                            "detail": "struct",
                            "kind": 23,  # Struct
                            "range": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(line_text)}},
                            "selectionRange": {"start": {"line": idx, "character": col}, "end": {"line": idx, "character": col + len(st.name)}},
                            "children": children,
                        })
                        break

            for en in mod.enums:
                for idx, line_text in enumerate(lines):
                    if re.search(rf"\benum\s+{en.name}\b", line_text):
                        col = line_text.find(en.name)
                        children = []
                        for v in en.variants:
                            children.append({
                                "name": v.name,
                                "detail": f"= {v.value}" if v.value is not None else "",
                                "kind": 22,  # EnumMember
                                "range": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(line_text)}},
                                "selectionRange": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(v.name)}},
                            })
                        symbols.append({
                            "name": en.name,
                            "detail": "enum",
                            "kind": 10,  # Enum
                            "range": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(line_text)}},
                            "selectionRange": {"start": {"line": idx, "character": col}, "end": {"line": idx, "character": col + len(en.name)}},
                            "children": children,
                        })
                        break

            for gl in mod.globals:
                for idx, line_text in enumerate(lines):
                    if re.search(rf"\b(?:const|static)\s+(?:mut\s+)?{gl.name}\b", line_text):
                        col = line_text.find(gl.name)
                        symbols.append({
                            "name": gl.name,
                            "detail": gl.type.name,
                            "kind": 14 if gl.is_const else 13,  # Constant / Variable
                            "range": {"start": {"line": idx, "character": 0}, "end": {"line": idx, "character": len(line_text)}},
                            "selectionRange": {"start": {"line": idx, "character": col}, "end": {"line": idx, "character": col + len(gl.name)}},
                        })
                        break
        except Exception:
            pass
        return symbols


def send(payload: dict) -> None:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.write(f"Content-Length: {len(encoded)}\r\n\r\n")
    sys.stdout.flush()
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def read_message() -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line: return None
        if line in (b"\n", b"\r\n"): break
        key, _, value = line.decode("ascii", errors="replace").partition(":")
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def main() -> int:
    server = SotlasLanguageServer()
    while message := read_message():
        method = message.get("method")
        params = message.get("params", {})
        request_id = message.get("id")

        if method == "initialize":
            server.workspace_root = uri_to_path(params.get("rootUri") or "")
            send({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "completionProvider": {
                            "resolveProvider": False,
                            "triggerCharacters": [":", ".", "@"],
                        },
                        "definitionProvider": True,
                        "hoverProvider": True,
                        "documentSymbolProvider": True,
                    }
                }
            })
        elif method in ("textDocument/didOpen", "textDocument/didChange"):
            document = params.get("textDocument", {})
            changes = params.get("contentChanges", [])
            source = document.get("text") or (changes[-1].get("text", "") if changes else "")
            uri = document.get("uri", "")
            diagnostics = server.validate(uri, source)
            send({
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {"uri": uri, "diagnostics": diagnostics}
            })
        elif method == "textDocument/completion":
            doc_uri = params.get("textDocument", {}).get("uri", "")
            pos = params.get("position", {})
            completions = server.completion(doc_uri, pos.get("line", 0), pos.get("character", 0))
            send({"jsonrpc": "2.0", "id": request_id, "result": completions})
        elif method == "textDocument/hover":
            doc_uri = params.get("textDocument", {}).get("uri", "")
            pos = params.get("position", {})
            hover_info = server.hover(doc_uri, pos.get("line", 0), pos.get("character", 0))
            send({"jsonrpc": "2.0", "id": request_id, "result": hover_info})
        elif method == "textDocument/definition":
            doc_uri = params.get("textDocument", {}).get("uri", "")
            pos = params.get("position", {})
            definition_loc = server.definition(doc_uri, pos.get("line", 0), pos.get("character", 0))
            send({"jsonrpc": "2.0", "id": request_id, "result": definition_loc})
        elif method == "textDocument/documentSymbol":
            doc_uri = params.get("textDocument", {}).get("uri", "")
            symbols = server.document_symbols(doc_uri)
            send({"jsonrpc": "2.0", "id": request_id, "result": symbols})
        elif method == "shutdown":
            send({"jsonrpc": "2.0", "id": request_id, "result": None})
        elif method == "exit":
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
