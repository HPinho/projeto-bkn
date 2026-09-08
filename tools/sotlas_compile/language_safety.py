"""Canonical Sotlas safety and C-ABI policy for the production frontend.

This module is installed on top of ``bootstrap`` after the grammar extensions.
It deliberately keeps @system and unsafe as different concepts:

* @system grants access to system-facing APIs;
* unsafe authorizes a concrete memory-unsafe operation;
* extern "C" is a foreign ABI boundary with unknown ownership/lifetime.

The production parser remains the bootstrap parser.  FFI syntax is normalized at
the token level into ordinary function declarations carrying semantic attributes,
so there is no second body parser or lowering path.
"""
from __future__ import annotations

from dataclasses import dataclass


_EXTERN_ATTR = "@extern(C)"
_UNSAFE_ATTR = "@unsafe"
_EXPORT_ATTR = "@export"


def _attr(function, name: str) -> bool:
    return name in getattr(function, "attributes", ())


def _mark_raw_pointer_kind(type_obj, raw: bool = False, reference: bool = False) -> None:
    if not getattr(type_obj, "pointer", False):
        return
    if raw:
        object.__setattr__(type_obj, "_sotlas_raw_pointer", True)
    if reference:
        object.__setattr__(type_obj, "_sotlas_reference", True)


def _is_raw_pointer(type_obj) -> bool:
    if type_obj is None or not getattr(type_obj, "pointer", False):
        return False
    if getattr(type_obj, "_sotlas_reference", False):
        return False
    return True


def _mark_foreign_pointer(type_obj) -> None:
    if _is_raw_pointer(type_obj):
        object.__setattr__(type_obj, "_sotlas_foreign_pointer", True)


def _abi_from_string(token, bootstrap, filename, source) -> str:
    text = token.text
    if len(text) < 2 or not (text.startswith('"') and text.endswith('"')):
        raise bootstrap.SotlasBootstrapError(
            "extern exige ABI em string, por exemplo extern \"C\"",
            token.line, token.column, filename, source,
        )
    abi = text[1:-1]
    if abi != "C":
        raise bootstrap.SotlasBootstrapError(
            f"ABI externa não suportada: {abi!r}; Sotlas estabiliza apenas extern \"C\"",
            token.line, token.column, filename, source,
        )
    return abi


def _synthetic(bootstrap, kind: str, text: str, anchor):
    return bootstrap.Token(kind, text, anchor.line, anchor.column)


def _copy_extern_decl(tokens, index: int, bootstrap, anchor, filename, source):
    """Normaliza um protótipo FFI sem reimplementar a gramática de tipos.

    Prefixos são reorganizados para o contrato já aceito pelo parser canônico:
    atributos -> pub -> fn. A assinatura inteira é apenas copiada token a token
    até o ';', que vira um corpo vazio. O parser normal continua responsável por
    parâmetros, tipos, ponteiros e retorno.
    """
    attrs = []
    public = None
    unsafe = False

    while index < len(tokens):
        token = tokens[index]
        if token.kind == "ATTR":
            attrs.append(token)
            index += 1
            continue
        if token.kind == "pub" and public is None:
            public = token
            index += 1
            continue
        if token.kind == "unsafe" and not unsafe:
            unsafe = True
            index += 1
            continue
        break

    if index >= len(tokens) or tokens[index].kind != "fn":
        token = tokens[index] if index < len(tokens) else anchor
        raise bootstrap.SotlasBootstrapError(
            "extern \"C\" aceita somente declarações fn",
            token.line, token.column, filename, source,
        )

    output = list(attrs)
    output.append(_synthetic(bootstrap, "ATTR", _EXTERN_ATTR, anchor))
    output.append(_synthetic(bootstrap, "ATTR", _EXPORT_ATTR, anchor))
    if unsafe:
        output.append(_synthetic(bootstrap, "ATTR", _UNSAFE_ATTR, anchor))
    if public is not None:
        output.append(public)

    paren_depth = 0
    bracket_depth = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "EOF":
            raise bootstrap.SotlasBootstrapError(
                "declaração extern sem ';'",
                anchor.line, anchor.column, filename, source,
            )
        if token.kind == "(" :
            paren_depth += 1
        elif token.kind == ")":
            paren_depth -= 1
        elif token.kind == "[":
            bracket_depth += 1
        elif token.kind == "]":
            bracket_depth -= 1
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
            output.append(token)
            index += 1
            continue

        anchor = token
        index += 1
        if index >= len(tokens) or tokens[index].kind != "STRING":
            current = tokens[index] if index < len(tokens) else anchor
            raise bootstrap.SotlasBootstrapError(
                "extern exige ABI explícita: extern \"C\"",
                current.line, current.column, filename, source,
            )
        _abi_from_string(tokens[index], bootstrap, filename, source)
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
            continue

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
    def __init__(self, bootstrap, module, imported_fns=None):
        self.b = bootstrap
        self.module = module
        self.filename = getattr(module, "filename", None)
        self.source = getattr(module, "source", None)
        self.functions = dict(getattr(bootstrap, "BUILTIN_FUNCTIONS", {}))
        self.functions.update({fn.name: fn for fn in module.functions})
        if imported_fns:
            self.functions.update(imported_fns)
        self.globals = {item.name: item.type for item in module.globals}

    def error(self, message: str, token) -> None:
        raise self.b.SotlasBootstrapError(
            message, token.line, token.column, self.filename, self.source
        )

    def check(self) -> None:
        for function in self.module.functions:
            if _attr(function, _EXTERN_ATTR):
                continue
            scope = {name: typ for name, typ in function.params}
            self._statements(
                function.body,
                scope,
                unsafe_depth=0,
                system_context=_attr(function, "@system"),
            )

    def _require_unsafe(self, token, unsafe_depth: int, operation: str) -> None:
        if unsafe_depth <= 0:
            self.error(
                f"{operation} exige bloco unsafe explícito; @system não substitui unsafe",
                token,
            )

    def _infer(self, expr, scope, unsafe_depth: int, system_context: bool) -> _ExprInfo:
        b = self.b
        if expr is None:
            return _ExprInfo(None)
        if isinstance(expr, b.Number):
            try:
                return _ExprInfo(b.Type(b.numeric_literal_type(expr.value)))
            except Exception:
                return _ExprInfo(b.Type("u64"))
        if isinstance(expr, b.Boolean):
            return _ExprInfo(b.Type("bool"))
        if isinstance(expr, b.CharLit):
            return _ExprInfo(b.Type("u8"))
        if isinstance(expr, b.StringLit):
            # String literals are compiler-owned immutable storage, not foreign raw memory.
            typ = b.Type("u8", pointer=True)
            object.__setattr__(typ, "_sotlas_reference", True)
            return _ExprInfo(typ)
        if isinstance(expr, b.NullLit):
            return _ExprInfo(b.Type("null", pointer=True))
        if isinstance(expr, b.Name):
            typ = scope.get(expr.value, self.globals.get(expr.value))
            return _ExprInfo(typ, bool(getattr(typ, "_sotlas_foreign_pointer", False)))
        if isinstance(expr, b.ArrayLit):
            for element in expr.elements:
                self._infer(element, scope, unsafe_depth, system_context)
            if not expr.elements:
                return _ExprInfo(None)
            inner = self._infer(expr.elements[0], scope, unsafe_depth, system_context).type_obj
            if inner is None:
                return _ExprInfo(None)
            size = expr.repeat_size if expr.is_repeat else len(expr.elements)
            return _ExprInfo(b.Type(inner.name, pointer=inner.pointer, is_array=True,
                                    array_size=size, elem_type=inner))
        if isinstance(expr, b.StructLit):
            for _, value in expr.fields:
                self._infer(value, scope, unsafe_depth, system_context)
            return _ExprInfo(b.Type(expr.struct_name))
        if isinstance(expr, b.IfExpr):
            self._infer(expr.condition, scope, unsafe_depth, system_context)
            then_info = self._infer(expr.then_expr, scope, unsafe_depth, system_context)
            self._infer(expr.else_expr, scope, unsafe_depth, system_context)
            return then_info
        if isinstance(expr, b.EnumAccess):
            return _ExprInfo(b.Type(expr.enum_name))
        if isinstance(expr, b.Unary):
            inner = self._infer(expr.value, scope, unsafe_depth, system_context)
            if expr.op == "*":
                if _is_raw_pointer(inner.type_obj):
                    self._require_unsafe(expr.token, unsafe_depth, "desreferenciamento de ponteiro cru")
                if inner.type_obj is None:
                    return _ExprInfo(None)
                return _ExprInfo(b.Type(inner.type_obj.name, mutable=inner.type_obj.mutable), inner.foreign)
            if expr.op == "&":
                if inner.type_obj is None:
                    return _ExprInfo(None)
                typ = b.Type(inner.type_obj.name, pointer=True, mutable=inner.type_obj.mutable)
                object.__setattr__(typ, "_sotlas_reference", True)
                return _ExprInfo(typ)
            if expr.op == "!":
                return _ExprInfo(b.Type("bool"))
            return inner
        if isinstance(expr, b.Binary):
            left = self._infer(expr.left, scope, unsafe_depth, system_context)
            self._infer(expr.right, scope, unsafe_depth, system_context)
            if expr.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
                return _ExprInfo(b.Type("bool"))
            return left
        if isinstance(expr, b.Call):
            for argument in expr.args:
                self._infer(argument, scope, unsafe_depth, system_context)
            function = self.functions.get(expr.callee)
            if function is None:
                return _ExprInfo(None)
            is_extern = _attr(function, _EXTERN_ATTR)
            is_system = _attr(function, "@system")
            if (is_extern or is_system) and not system_context:
                boundary = "FFI extern \"C\"" if is_extern else "API @system"
                self.error(
                    f"chamada a {boundary} exige que a função chamadora seja @system",
                    expr.token,
                )
            if is_extern and _attr(function, _UNSAFE_ATTR):
                self._require_unsafe(expr.token, unsafe_depth, "chamada FFI marcada unsafe")
            result = function.result
            foreign = is_extern and _is_raw_pointer(result)
            return _ExprInfo(result, foreign)
        if isinstance(expr, b.Index):
            target = self._infer(expr.target, scope, unsafe_depth, system_context)
            self._infer(expr.index, scope, unsafe_depth, system_context)
            if _is_raw_pointer(target.type_obj):
                self._require_unsafe(expr.token, unsafe_depth, "indexação de ponteiro cru")
            typ = target.type_obj
            if typ is None:
                return _ExprInfo(None)
            if getattr(typ, "is_array", False) and getattr(typ, "elem_type", None):
                return _ExprInfo(typ.elem_type, target.foreign)
            return _ExprInfo(b.Type(typ.name, mutable=typ.mutable), target.foreign)
        if isinstance(expr, b.Member):
            target = self._infer(expr.target, scope, unsafe_depth, system_context)
            if _is_raw_pointer(target.type_obj):
                self._require_unsafe(expr.token, unsafe_depth, "acesso a campo via ponteiro cru")
            return _ExprInfo(None, target.foreign)
        if isinstance(expr, b.MethodCall):
            target = self._infer(expr.target, scope, unsafe_depth, system_context)
            for argument in expr.args:
                self._infer(argument, scope, unsafe_depth, system_context)
            if _is_raw_pointer(target.type_obj):
                self._require_unsafe(expr.token, unsafe_depth, "chamada de método via ponteiro cru")
            method = None
            if target.type_obj is not None:
                method = self.functions.get(f"{target.type_obj.name}_{expr.method}")
            if method and _attr(method, "@system") and not system_context:
                self.error("chamada a API @system exige que a função chamadora seja @system", expr.token)
            return _ExprInfo(method.result if method else None, target.foreign)
        if isinstance(expr, b.Cast):
            source_info = self._infer(expr.expr, scope, unsafe_depth, system_context)
            target = expr.target_type
            if _is_raw_pointer(target) and not isinstance(expr.expr, b.NullLit):
                self._require_unsafe(expr.token, unsafe_depth, "criação/conversão para ponteiro cru")
            return _ExprInfo(target, source_info.foreign)
        return _ExprInfo(None)

    def _statements(self, items, scope, unsafe_depth: int, system_context: bool) -> None:
        b = self.b
        for item in items:
            if isinstance(item, b.Let):
                info = self._infer(item.value, scope, unsafe_depth, system_context)
                typ = item.type or info.type_obj
                if typ is not None and info.foreign and _is_raw_pointer(typ):
                    _mark_foreign_pointer(typ)
                scope[item.name] = typ
            elif isinstance(item, b.Assign):
                self._infer(item.target, scope, unsafe_depth, system_context)
                self._infer(item.value, scope, unsafe_depth, system_context)
            elif isinstance(item, b.Return):
                self._infer(item.value, scope, unsafe_depth, system_context)
            elif isinstance(item, b.Expression):
                self._infer(item.value, scope, unsafe_depth, system_context)
            elif isinstance(item, b.If):
                self._infer(item.condition, scope, unsafe_depth, system_context)
                self._statements(item.then_body, dict(scope), unsafe_depth, system_context)
                self._statements(item.else_body, dict(scope), unsafe_depth, system_context)
            elif isinstance(item, b.While):
                self._infer(item.condition, scope, unsafe_depth, system_context)
                self._statements(item.body, dict(scope), unsafe_depth, system_context)
            elif isinstance(item, b.Loop):
                self._statements(item.body, dict(scope), unsafe_depth, system_context)
            elif isinstance(item, b.For):
                self._infer(item.start, scope, unsafe_depth, system_context)
                self._infer(item.end, scope, unsafe_depth, system_context)
                nested = dict(scope)
                nested[item.var_name] = b.Type("usize")
                self._statements(item.body, nested, unsafe_depth, system_context)
            elif isinstance(item, b.Unsafe):
                self._statements(item.body, dict(scope), unsafe_depth + 1, system_context)
            elif isinstance(item, b.Defer):
                if item.body is not None:
                    self._statements(item.body, dict(scope), unsafe_depth, system_context)
                elif isinstance(item.value, b.Assign):
                    self._infer(item.value.target, scope, unsafe_depth, system_context)
                    self._infer(item.value.value, scope, unsafe_depth, system_context)
                else:
                    self._infer(item.value, scope, unsafe_depth, system_context)


def _ffi_signature(function) -> str:
    params = ", ".join(typ.c_decl(name) for name, typ in function.params) or "void"
    return f"{function.result.c()} {function.name}({params})"


def _annotate_ffi(module) -> None:
    for function in module.functions:
        if not _attr(function, _EXTERN_ATTR):
            continue
        for _, typ in function.params:
            _mark_foreign_pointer(typ)
        _mark_foreign_pointer(function.result)


def install(bootstrap) -> None:
    """Install the canonical safety/FFI contract exactly once."""
    if getattr(bootstrap, "_LANGUAGE_SAFETY_INSTALLED", False):
        return

    bootstrap.KEYWORDS.add("extern")

    # Preserve the distinction between safe references and raw pointers even
    # though the C-lowering Type representation uses pointer=True for both.
    original_type = bootstrap.Parser.type

    def strict_type(parser):
        starting_kind = parser.current.kind
        result = original_type(parser)
        if starting_kind == "*":
            _mark_raw_pointer_kind(result, raw=True)
        elif starting_kind == "&":
            _mark_raw_pointer_kind(result, reference=True)
        return result

    bootstrap.Parser.type = strict_type

    original_parse = bootstrap.parse

    def canonical_parse(source: str, filename: str | None = None):
        if "extern" not in source:
            module = original_parse(source, filename=filename)
            _annotate_ffi(module)
            return module
        tokens = bootstrap.lex(source, filename=filename)
        tokens = _normalize_extern_tokens(tokens, bootstrap, filename, source)
        module = bootstrap.Parser(tokens, filename=filename, source=source).parse()
        _annotate_ffi(module)
        return module

    bootstrap.parse = canonical_parse

    original_check = bootstrap.check

    def strict_check(module, imported_fns=None, imported_types=None,
                     imported_enums=None, imported_globals=None):
        # The legacy type checker still performs all existing structural/type
        # checks. The strict pass intentionally runs afterwards and can only
        # reject more code; it never turns an old error into success.
        result = original_check(
            module, imported_fns, imported_types, imported_enums, imported_globals
        )
        _StrictSafetyChecker(bootstrap, module, imported_fns).check()
        return result

    bootstrap.check = strict_check

    original_emit_c = bootstrap.emit_c

    def strict_emit_c(module, *args, **kwargs):
        code = original_emit_c(module, *args, **kwargs)
        for function in module.functions:
            if not _attr(function, _EXTERN_ATTR):
                continue
            signature = _ffi_signature(function)
            # Keep the normal forward declaration, make its external ABI
            # explicit, and remove the synthetic empty body used only so the
            # canonical parser can represent a prototype.
            code = code.replace(f"{signature};", f"extern {signature};", 1)
            code = code.replace(f"{signature} {{\n}}\n", "")
            code = code.replace(f"{signature} {{\n}}\n\n", "")
        return code

    bootstrap.emit_c = strict_emit_c

    original_emit_header = bootstrap.emit_header

    def strict_emit_header(module, *args, **kwargs):
        code = original_emit_header(module, *args, **kwargs)
        for function in module.functions:
            if not _attr(function, _EXTERN_ATTR):
                continue
            signature = _ffi_signature(function)
            code = code.replace(f"{signature};", f"extern {signature};", 1)
        return code

    bootstrap.emit_header = strict_emit_header

    bootstrap._LANGUAGE_SAFETY_INSTALLED = True


__all__ = ["install"]
