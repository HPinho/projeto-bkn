"""Canonical safety and C-ABI policy for the production Sotlas frontend.

`@system` identifies code that may cross into privileged backend intrinsics.
It is not an implicit unsafe block.  Safe Sotlas may call a safe @system wrapper;
only direct privileged builtins, FFI entry points, and concrete raw-memory
operations are restricted by this pass.
"""
from __future__ import annotations

from dataclasses import dataclass

_EXTERN_ATTR = "@extern(C)"
_UNSAFE_ATTR = "@unsafe"
_EXPORT_ATTR = "@export"

# Bounds-checked accessors for immutable embedded assets and pure colour LUTs.
# Returning a raw pointer is safe; dereferencing it still needs lexical unsafe.
_SAFE_ASSET_BUILTINS = frozenset({
    "baken_get_font_advances", "baken_get_font_alpha", "baken_get_font_width",
    "baken_get_font_height", "baken_get_font_px", "baken_get_cjk_width",
    "baken_get_cjk_height", "baken_get_cjk_alpha", "baken_get_logo_pixels",
    "baken_get_logo_size", "baken_srgb_to_linear", "baken_linear_to_srgb",
    "baken_get_app_icon_alpha", "baken_get_motion_icon_alpha",
})


def _attr(function, name: str) -> bool:
    return name in getattr(function, "attributes", ())


def _mark_pointer_kind(type_obj, *, raw=False, reference=False) -> None:
    if type_obj is None or not getattr(type_obj, "pointer", False):
        return
    if raw:
        object.__setattr__(type_obj, "_sotlas_raw_pointer", True)
    if reference:
        object.__setattr__(type_obj, "_sotlas_reference", True)


def _is_raw_pointer(type_obj) -> bool:
    return bool(
        type_obj is not None
        and getattr(type_obj, "pointer", False)
        and not getattr(type_obj, "is_array", False)
        and not getattr(type_obj, "_sotlas_reference", False)
    )


def _mark_foreign(type_obj) -> None:
    if _is_raw_pointer(type_obj):
        object.__setattr__(type_obj, "_sotlas_foreign_pointer", True)


def _synthetic(bootstrap, kind: str, text: str, anchor):
    return bootstrap.Token(kind, text, anchor.line, anchor.column)


def _validate_abi(token, bootstrap, filename, source) -> None:
    text = token.text
    if len(text) < 2 or not text.startswith('"') or not text.endswith('"'):
        raise bootstrap.SotlasBootstrapError(
            'extern exige ABI explícita: extern "C"',
            token.line, token.column, filename, source,
        )
    abi = text[1:-1]
    if abi != "C":
        raise bootstrap.SotlasBootstrapError(
            f"ABI externa não suportada: {abi!r}; somente extern \"C\" é estável",
            token.line, token.column, filename, source,
        )


def _copy_extern_decl(tokens, index, bootstrap, anchor, filename, source):
    """Turn one FFI prototype into a normal canonical fn AST declaration.

    The signature tokens are not reparsed here.  They are copied verbatim and
    consumed by the normal bootstrap parser, which remains the sole type/body
    grammar.  Only the foreign-boundary metadata and synthetic empty body are
    introduced by this normalization.
    """
    attrs = []
    public = None
    is_unsafe = False
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "ATTR":
            attrs.append(token); index += 1; continue
        if token.kind == "pub" and public is None:
            public = token; index += 1; continue
        if token.kind == "unsafe" and not is_unsafe:
            is_unsafe = True; index += 1; continue
        break

    if index >= len(tokens) or tokens[index].kind != "fn":
        token = tokens[index] if index < len(tokens) else anchor
        raise bootstrap.SotlasBootstrapError(
            'extern "C" aceita somente declarações fn',
            token.line, token.column, filename, source,
        )

    output = list(attrs)
    output.extend([
        _synthetic(bootstrap, "ATTR", _EXTERN_ATTR, anchor),
        _synthetic(bootstrap, "ATTR", _EXPORT_ATTR, anchor),
    ])
    if is_unsafe:
        output.append(_synthetic(bootstrap, "ATTR", _UNSAFE_ATTR, anchor))
    if public is not None:
        output.append(public)

    paren_depth = 0
    bracket_depth = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "EOF":
            break
        if token.kind == "(": paren_depth += 1
        elif token.kind == ")": paren_depth -= 1
        elif token.kind == "[": bracket_depth += 1
        elif token.kind == "]": bracket_depth -= 1
        if token.kind == ";" and paren_depth == 0 and bracket_depth == 0:
            output.append(_synthetic(bootstrap, "{", "{", token))
            output.append(_synthetic(bootstrap, "}", "}", token))
            return output, index + 1
        output.append(token)
        index += 1

    raise bootstrap.SotlasBootstrapError(
        "declaração extern sem ';'",
        anchor.line, anchor.column, filename, source,
    )


def _normalize_extern_tokens(tokens, bootstrap, filename, source):
    output = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind != "extern":
            output.append(token); index += 1; continue

        anchor = token
        index += 1
        if index >= len(tokens) or tokens[index].kind != "STRING":
            current = tokens[index] if index < len(tokens) else anchor
            raise bootstrap.SotlasBootstrapError(
                'extern exige ABI explícita: extern "C"',
                current.line, current.column, filename, source,
            )
        _validate_abi(tokens[index], bootstrap, filename, source)
        index += 1

        if index < len(tokens) and tokens[index].kind == "{":
            index += 1
            while index < len(tokens) and tokens[index].kind != "}":
                normalized, index = _copy_extern_decl(
                    tokens, index, bootstrap, anchor, filename, source
                )
                output.extend(normalized)
            if index >= len(tokens) or tokens[index].kind != "}":
                raise bootstrap.SotlasBootstrapError(
                    "bloco extern sem '}'",
                    anchor.line, anchor.column, filename, source,
                )
            index += 1
        else:
            normalized, index = _copy_extern_decl(
                tokens, index, bootstrap, anchor, filename, source
            )
            output.extend(normalized)
    return output


@dataclass
class _ExprInfo:
    type_obj: object | None
    foreign: bool = False


class _StrictSafetyChecker:
    def __init__(self, bootstrap, module, imported_fns=None, imported_types=None,
                 imported_globals=None):
        self.b = bootstrap
        self.module = module
        self.filename = getattr(module, "filename", None)
        self.source = getattr(module, "source", None)
        self.functions = dict(getattr(bootstrap, "BUILTIN_FUNCTIONS", {}))
        self.functions.update({fn.name: fn for fn in module.functions})
        if imported_fns:
            self.functions.update(imported_fns)
        self.globals = {item.name: item.type for item in module.globals}
        self.globals.update({name: item.type for name, item in (imported_globals or {}).items()})
        self.structs = {item.name: item for item in module.structs}
        self.structs.update(imported_types or {})

    def error(self, message, token) -> None:
        raise self.b.SotlasBootstrapError(
            message, token.line, token.column, self.filename, self.source
        )

    def _require_unsafe(self, token, depth: int, operation: str) -> None:
        if depth <= 0:
            self.error(
                f"{operation} exige bloco unsafe explícito; @system não substitui unsafe",
                token,
            )

    def check(self) -> None:
        for function in self.module.functions:
            if _attr(function, _EXTERN_ATTR):
                continue
            self._statements(
                function.body,
                {name: typ for name, typ in function.params},
                0,
                _attr(function, "@system"),
            )

    def _infer(self, expr, scope, depth: int, system_context: bool) -> _ExprInfo:
        b = self.b
        if expr is None: return _ExprInfo(None)
        if isinstance(expr, b.UnsafeExpr):
            return self._infer(expr.value, scope, depth + 1, system_context)
        if isinstance(expr, b.Number):
            try: return _ExprInfo(b.Type(b.numeric_literal_type(expr.value)))
            except Exception: return _ExprInfo(b.Type("u64"))
        if isinstance(expr, b.Boolean): return _ExprInfo(b.Type("bool"))
        if isinstance(expr, b.CharLit): return _ExprInfo(b.Type("u8"))
        if isinstance(expr, b.StringLit):
            typ = b.Type("u8", pointer=True)
            object.__setattr__(typ, "_sotlas_reference", True)
            return _ExprInfo(typ)
        if isinstance(expr, b.NullLit): return _ExprInfo(b.Type("null", pointer=True))
        if isinstance(expr, b.Name):
            typ = scope.get(expr.value, self.globals.get(expr.value))
            return _ExprInfo(typ, bool(getattr(typ, "_sotlas_foreign_pointer", False)))
        if isinstance(expr, b.EnumAccess): return _ExprInfo(b.Type(expr.enum_name))
        if isinstance(expr, b.ArrayLit):
            infos = [self._infer(e, scope, depth, system_context) for e in expr.elements]
            if not infos or infos[0].type_obj is None: return _ExprInfo(None)
            inner = infos[0].type_obj
            size = expr.repeat_size if expr.is_repeat else len(expr.elements)
            return _ExprInfo(b.Type(inner.name, pointer=inner.pointer, is_array=True,
                                    array_size=size, elem_type=inner))
        if isinstance(expr, b.StructLit):
            for _, value in expr.fields: self._infer(value, scope, depth, system_context)
            return _ExprInfo(b.Type(expr.struct_name))
        if isinstance(expr, b.IfExpr):
            self._infer(expr.condition, scope, depth, system_context)
            left = self._infer(expr.then_expr, scope, depth, system_context)
            self._infer(expr.else_expr, scope, depth, system_context)
            return left
        if isinstance(expr, b.Unary):
            inner = self._infer(expr.value, scope, depth, system_context)
            if expr.op == "*":
                if _is_raw_pointer(inner.type_obj):
                    self._require_unsafe(expr.token, depth, "desreferenciamento de ponteiro cru")
                if inner.type_obj is None: return _ExprInfo(None)
                return _ExprInfo(b.Type(inner.type_obj.name, mutable=inner.type_obj.mutable), inner.foreign)
            if expr.op == "&":
                if inner.type_obj is None: return _ExprInfo(None)
                typ = b.Type(inner.type_obj.name, pointer=True, mutable=inner.type_obj.mutable)
                object.__setattr__(typ, "_sotlas_reference", True)
                return _ExprInfo(typ)
            if expr.op == "!": return _ExprInfo(b.Type("bool"))
            return inner
        if isinstance(expr, b.Binary):
            left = self._infer(expr.left, scope, depth, system_context)
            self._infer(expr.right, scope, depth, system_context)
            if expr.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
                return _ExprInfo(b.Type("bool"))
            return left
        if isinstance(expr, b.Call):
            for arg in expr.args: self._infer(arg, scope, depth, system_context)
            function = self.functions.get(expr.callee)
            if function is None: return _ExprInfo(None)
            is_extern = _attr(function, _EXTERN_ATTR)
            is_privileged_builtin = (
                expr.callee in getattr(b, "BUILTIN_FUNCTIONS", {})
                and _attr(function, "@system")
                and expr.callee not in _SAFE_ASSET_BUILTINS
            )
            if is_extern and not system_context:
                self.error('chamada a FFI extern "C" exige função @system', expr.token)
            if is_privileged_builtin and not system_context:
                self.error("chamada a intrínseco privilegiado exige função @system", expr.token)
            if is_extern and _attr(function, _UNSAFE_ATTR):
                self._require_unsafe(expr.token, depth, "chamada FFI marcada unsafe")
            return _ExprInfo(function.result, is_extern and _is_raw_pointer(function.result))
        if isinstance(expr, b.Index):
            target = self._infer(expr.target, scope, depth, system_context)
            self._infer(expr.index, scope, depth, system_context)
            if _is_raw_pointer(target.type_obj):
                self._require_unsafe(expr.token, depth, "indexação de ponteiro cru")
            typ = target.type_obj
            if typ is None: return _ExprInfo(None)
            if getattr(typ, "is_array", False) and getattr(typ, "elem_type", None):
                return _ExprInfo(typ.elem_type, target.foreign)
            return _ExprInfo(b.Type(typ.name, mutable=typ.mutable), target.foreign)
        if isinstance(expr, b.Member):
            target = self._infer(expr.target, scope, depth, system_context)
            if _is_raw_pointer(target.type_obj):
                self._require_unsafe(expr.token, depth, "acesso a campo via ponteiro cru")
            struct = self.structs.get(getattr(target.type_obj, "name", None))
            field = next((f for f in struct.fields if f.name == expr.field), None) if struct else None
            return _ExprInfo(field.type if field else None, target.foreign)
        if isinstance(expr, b.MethodCall):
            target = self._infer(expr.target, scope, depth, system_context)
            for arg in expr.args: self._infer(arg, scope, depth, system_context)
            if expr.method == "as_ptr":
                typ = target.type_obj
                element = getattr(typ, "elem_type", None) or typ
                return _ExprInfo(b.Type(element.name, pointer=True), target.foreign) if element else _ExprInfo(None)
            if _is_raw_pointer(target.type_obj):
                self._require_unsafe(expr.token, depth, "chamada de método via ponteiro cru")
            if expr.method in ("add", "abs"):
                return target
            method = None
            if target.type_obj is not None:
                method = self.functions.get(f"{target.type_obj.name}_{expr.method}")
            return _ExprInfo(method.result if method else None, target.foreign)
        if isinstance(expr, b.Cast):
            info = self._infer(expr.expr, scope, depth, system_context)
            target_is_raw = _is_raw_pointer(expr.target_type)
            source_is_raw = _is_raw_pointer(info.type_obj)
            # Requalifying/reinterpreting an already-raw pointer does not create
            # a new address and therefore needs no unsafe by itself. Address
            # creation from integers/references remains an explicit boundary.
            if target_is_raw and not source_is_raw and not isinstance(expr.expr, b.NullLit):
                self._require_unsafe(expr.token, depth, "criação/conversão para ponteiro cru")
            return _ExprInfo(expr.target_type, info.foreign)
        return _ExprInfo(None)

    def _statements(self, items, scope, depth: int, system_context: bool) -> None:
        b = self.b
        for item in items:
            if isinstance(item, b.Let):
                info = self._infer(item.value, scope, depth, system_context)
                typ = item.type or info.type_obj
                if typ is not None and info.foreign and _is_raw_pointer(typ): _mark_foreign(typ)
                scope[item.name] = typ
            elif isinstance(item, b.Assign):
                self._infer(item.target, scope, depth, system_context)
                self._infer(item.value, scope, depth, system_context)
            elif isinstance(item, b.Return): self._infer(item.value, scope, depth, system_context)
            elif isinstance(item, b.Expression): self._infer(item.value, scope, depth, system_context)
            elif isinstance(item, b.If):
                self._infer(item.condition, scope, depth, system_context)
                self._statements(item.then_body, dict(scope), depth, system_context)
                self._statements(item.else_body, dict(scope), depth, system_context)
            elif isinstance(item, b.While):
                self._infer(item.condition, scope, depth, system_context)
                self._statements(item.body, dict(scope), depth, system_context)
            elif isinstance(item, b.Loop): self._statements(item.body, dict(scope), depth, system_context)
            elif isinstance(item, b.For):
                self._infer(item.start, scope, depth, system_context)
                self._infer(item.end, scope, depth, system_context)
                nested = dict(scope); nested[item.var_name] = b.Type("usize")
                self._statements(item.body, nested, depth, system_context)
            elif isinstance(item, b.Unsafe):
                self._statements(item.body, dict(scope), depth + 1, system_context)
            elif isinstance(item, b.Defer):
                if item.body is not None:
                    self._statements(item.body, dict(scope), depth, system_context)
                elif isinstance(item.value, b.Assign):
                    self._infer(item.value.target, scope, depth, system_context)
                    self._infer(item.value.value, scope, depth, system_context)
                else:
                    self._infer(item.value, scope, depth, system_context)


def _annotate_ffi(module) -> None:
    for function in module.functions:
        if _attr(function, _EXTERN_ATTR):
            for _, typ in function.params: _mark_foreign(typ)
            _mark_foreign(function.result)


def _signature(function) -> str:
    params = ", ".join(typ.c_decl(name) for name, typ in function.params) or "void"
    return f"{function.result.c()} {function.name}({params})"


def install(bootstrap) -> None:
    if getattr(bootstrap, "_LANGUAGE_SAFETY_INSTALLED", False): return

    bootstrap.KEYWORDS.add("extern")

    # Keep &T / &mut T distinct from raw *const/*mut even though both lower to
    # native C pointers. This metadata has zero runtime cost.
    original_type = bootstrap.Parser.type
    def strict_type(parser):
        starting = parser.current.kind
        result = original_type(parser)
        if starting == "*": _mark_pointer_kind(result, raw=True)
        elif starting == "&": _mark_pointer_kind(result, reference=True)
        return result
    bootstrap.Parser.type = strict_type

    original_parse = bootstrap.parse
    def canonical_parse(source: str, filename: str | None = None):
        if "extern" not in source:
            module = original_parse(source, filename=filename)
        else:
            tokens = _normalize_extern_tokens(
                bootstrap.lex(source, filename=filename), bootstrap, filename, source
            )
            module = bootstrap.Parser(tokens, filename=filename, source=source).parse()
        _annotate_ffi(module)
        return module
    bootstrap.parse = canonical_parse

    original_check = bootstrap.check
    def strict_check(module, imported_fns=None, imported_types=None,
                     imported_enums=None, imported_globals=None):
        # The old checker used @system as an implicit dereference exemption.
        # Temporarily neutralize only that legacy rule while retaining all of
        # its structural/type checks; the strict lexical pass below becomes the
        # single source of truth for unsafe memory.
        added_system = []
        for function in module.functions:
            if "@system" not in function.attributes:
                function.attributes.append("@system")
                added_system.append(function)
        try:
            result = original_check(
                module, imported_fns, imported_types, imported_enums, imported_globals
            )
        finally:
            for function in added_system:
                function.attributes.remove("@system")
        _StrictSafetyChecker(bootstrap, module, imported_fns, imported_types, imported_globals).check()
        return result
    bootstrap.check = strict_check

    original_emit_c = bootstrap.emit_c
    def strict_emit_c(module, *args, **kwargs):
        code = original_emit_c(module, *args, **kwargs)
        for function in module.functions:
            if not _attr(function, _EXTERN_ATTR): continue
            signature = _signature(function)
            code = code.replace(f"{signature};", f"extern {signature};", 1)
            code = code.replace(f"{signature} {{\n}}\n\n", "")
            code = code.replace(f"{signature} {{\n}}\n", "")
        return code
    bootstrap.emit_c = strict_emit_c

    original_emit_header = bootstrap.emit_header
    def strict_emit_header(module, *args, **kwargs):
        code = original_emit_header(module, *args, **kwargs)
        for function in module.functions:
            if _attr(function, _EXTERN_ATTR):
                signature = _signature(function)
                code = code.replace(f"{signature};", f"extern {signature};", 1)
        return code
    bootstrap.emit_header = strict_emit_header

    bootstrap._LANGUAGE_SAFETY_INSTALLED = True


__all__ = ["install"]