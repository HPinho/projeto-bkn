"""Extensões oficiais da gramática/emissão do frontend Sotlas.

Esta camada é instalada sobre ``bootstrap`` antes de o compilador modular ser
carregado. Ela mantém lexer, parser e lowering alinhados: operadores compostos
reconhecidos pelo lexer precisam ser aceitos pelo parser, ``let mut`` precisa
preservar mutabilidade até C11 e identificadores Sotlas válidos não podem
colidir com palavras reservadas do backend C.
"""
from __future__ import annotations


_COMPOUND_ASSIGNMENTS = (
    ("+=", "+"),
    ("-=", "-"),
    ("*=", "*"),
    ("/=", "/"),
    ("%=", "%"),
    ("&=", "&"),
    ("|=", "|"),
    ("^=", "^"),
    ("<<=", "<<"),
    (">>=", ">>"),
)

# Palavras que podem ser identificadores válidos em Sotlas, mas não podem ser
# emitidas literalmente como nomes locais no backend C11.
_C_RESERVED = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Alignas", "_Alignof",
    "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary", "_Noreturn",
    "_Static_assert", "_Thread_local",
}

_MUT_AUTO_MARKER = "__SOTLAS_MUT_AUTO_ARRAY__"
_MUT_STATIC_MARKER = "__SOTLAS_MUT_STATIC_ARRAY__"


def _safe_local(name: str) -> str:
    if name in _C_RESERVED:
        return f"sotlas_c_kw_{name}"
    return name


def install(bootstrap) -> None:
    """Instala a gramática estendida de forma idempotente no módulo bootstrap."""
    if getattr(bootstrap, "_FRONTEND_EXTENSIONS_INSTALLED", False):
        return

    # O lexer já conhecia a maior parte destes tokens, mas %= não fazia parte do
    # conjunto. Mantê-los explicitamente antes das formas curtas evita que <<=
    # seja dividido em << + =, e faz lexer/parser compartilharem o contrato.
    required_multi = ("<<=", ">>=", "^=", "%=")
    bootstrap.MULTI = required_multi + tuple(
        token for token in bootstrap.MULTI if token not in required_multi
    )

    base_parser = bootstrap.Parser

    class ExtendedParser(base_parser):
        """Parser procedural com mutabilidade e atribuições compostas completas."""

        def _finish_assignment(self, token, expr):
            if self.accept("="):
                value = self.expression()
                self.expect(";")
                return bootstrap.Assign(token, expr, value)
            for compound, binary in _COMPOUND_ASSIGNMENTS:
                if self.accept(compound):
                    value = self.expression()
                    self.expect(";")
                    return bootstrap.Assign(
                        token, expr, bootstrap.Binary(token, expr, binary, value)
                    )
            return None

        def statement(self):
            token = self.current

            # Preserve a informação de mutabilidade que o parser bootstrap
            # anteriormente calculava e descartava antes do lowering.
            if self.accept("let"):
                is_mut = bool(self.accept("mut"))
                name = self.ident()
                typ = None
                if self.accept(":"):
                    typ = self.type()
                self.expect("=")
                value = self.expression()
                self.expect(";")
                node = bootstrap.Let(token, name, typ, value)
                node.is_mut = is_mut
                node.is_const = False
                node.is_static = False
                return node

            if self.accept("const"):
                name = self.ident()
                typ = None
                if self.accept(":"):
                    typ = self.type()
                self.expect("=")
                value = self.expression()
                self.expect(";")
                node = bootstrap.Let(token, name, typ, value)
                node.is_mut = False
                node.is_const = True
                node.is_static = False
                return node

            if self.accept("static"):
                is_const = bool(self.accept("const"))
                is_mut = bool(self.accept("mut"))
                name = self.ident()
                typ = None
                if self.accept(":"):
                    typ = self.type()
                self.expect("=")
                value = self.expression()
                self.expect(";")
                node = bootstrap.Let(token, name, typ, value)
                node.is_mut = is_mut
                node.is_const = is_const
                node.is_static = True
                return node

            # Defer também aceita a mesma família de assignments. Blocos usam
            # block() sem pré-consumir '{', corrigindo a dupla leitura antiga.
            if self.accept("defer"):
                if self.current.kind == "{":
                    return bootstrap.Defer(token, body=self.block())
                expr = self.expression()
                assignment = self._finish_assignment(token, expr)
                if assignment is not None:
                    return bootstrap.Defer(token, assignment)
                self.expect(";")
                return bootstrap.Defer(token, expr)

            # Fluxos de controle continuam no parser base. Como block() chama
            # self.statement(), a extensão também vale em blocos aninhados.
            if token.kind in {
                "return", "break", "continue", "if", "while", "loop", "for", "unsafe"
            }:
                return super().statement()

            expr = self.expression()
            assignment = self._finish_assignment(token, expr)
            if assignment is not None:
                return assignment
            self.expect(";")
            return bootstrap.Expression(token, expr)

    bootstrap.Parser = ExtendedParser

    # Marcação de storage em tipos de arrays mutáveis. Type é frozen para a
    # linguagem, então o metadado do lowering é anexado somente internamente.
    original_c_decl = bootstrap.Type.c_decl

    def extended_c_decl(type_obj, var_name: str) -> str:
        declaration = original_c_decl(type_obj, var_name)
        storage = getattr(type_obj, "_sotlas_mut_array_storage", None)
        if storage == "auto":
            return f"{_MUT_AUTO_MARKER} {declaration}"
        if storage == "static":
            return f"{_MUT_STATIC_MARKER} {declaration}"
        return declaration

    bootstrap.Type.c_decl = extended_c_decl

    def walk_statements(items):
        for item in items:
            yield item
            if isinstance(item, bootstrap.If):
                yield from walk_statements(item.then_body)
                yield from walk_statements(item.else_body)
            elif isinstance(item, (bootstrap.While, bootstrap.Loop, bootstrap.Unsafe)):
                yield from walk_statements(item.body)
            elif isinstance(item, bootstrap.For):
                yield from walk_statements(item.body)
            elif isinstance(item, bootstrap.Defer) and item.body is not None:
                yield from walk_statements(item.body)

    def mark_mutable_arrays(module) -> None:
        for function in module.functions:
            for item in walk_statements(function.body):
                if (
                    isinstance(item, bootstrap.Let)
                    and getattr(item, "is_mut", False)
                    and item.type is not None
                    and item.type.is_array
                ):
                    storage = "static" if getattr(item, "is_static", False) else "auto"
                    object.__setattr__(item.type, "_sotlas_mut_array_storage", storage)

    def collect_local_names(items, output: set[str]) -> None:
        for item in items:
            if isinstance(item, bootstrap.Let):
                output.add(item.name)
            elif isinstance(item, bootstrap.For):
                output.add(item.var_name)
                collect_local_names(item.body, output)
            elif isinstance(item, bootstrap.If):
                collect_local_names(item.then_body, output)
                collect_local_names(item.else_body, output)
            elif isinstance(item, (bootstrap.While, bootstrap.Loop, bootstrap.Unsafe)):
                collect_local_names(item.body, output)
            elif isinstance(item, bootstrap.Defer) and item.body is not None:
                collect_local_names(item.body, output)

    def rename_expr(expr, mapping: dict[str, str]) -> None:
        if expr is None:
            return
        if isinstance(expr, bootstrap.Name):
            expr.value = mapping.get(expr.value, expr.value)
        elif isinstance(expr, bootstrap.Call):
            expr.callee = mapping.get(expr.callee, expr.callee)
            for arg in expr.args:
                rename_expr(arg, mapping)
        elif isinstance(expr, bootstrap.Unary):
            rename_expr(expr.value, mapping)
        elif isinstance(expr, bootstrap.Binary):
            rename_expr(expr.left, mapping)
            rename_expr(expr.right, mapping)
        elif isinstance(expr, bootstrap.Index):
            rename_expr(expr.target, mapping)
            rename_expr(expr.index, mapping)
        elif isinstance(expr, bootstrap.Member):
            rename_expr(expr.target, mapping)
        elif isinstance(expr, bootstrap.MethodCall):
            rename_expr(expr.target, mapping)
            for arg in expr.args:
                rename_expr(arg, mapping)
        elif isinstance(expr, bootstrap.Cast):
            rename_expr(expr.expr, mapping)
        elif isinstance(expr, bootstrap.ArrayLit):
            for element in expr.elements:
                rename_expr(element, mapping)
        elif isinstance(expr, bootstrap.StructLit):
            for _, value in expr.fields:
                rename_expr(value, mapping)
        elif isinstance(expr, bootstrap.IfExpr):
            rename_expr(expr.condition, mapping)
            rename_expr(expr.then_expr, mapping)
            rename_expr(expr.else_expr, mapping)

    def rename_statements(items, mapping: dict[str, str]) -> None:
        for item in items:
            if isinstance(item, bootstrap.Let):
                rename_expr(item.value, mapping)
                item.name = mapping.get(item.name, item.name)
            elif isinstance(item, bootstrap.Assign):
                rename_expr(item.target, mapping)
                rename_expr(item.value, mapping)
            elif isinstance(item, bootstrap.Return):
                rename_expr(item.value, mapping)
            elif isinstance(item, bootstrap.Expression):
                rename_expr(item.value, mapping)
            elif isinstance(item, bootstrap.If):
                rename_expr(item.condition, mapping)
                rename_statements(item.then_body, mapping)
                rename_statements(item.else_body, mapping)
            elif isinstance(item, bootstrap.While):
                rename_expr(item.condition, mapping)
                rename_statements(item.body, mapping)
            elif isinstance(item, (bootstrap.Loop, bootstrap.Unsafe)):
                rename_statements(item.body, mapping)
            elif isinstance(item, bootstrap.For):
                rename_expr(item.start, mapping)
                rename_expr(item.end, mapping)
                item.var_name = mapping.get(item.var_name, item.var_name)
                rename_statements(item.body, mapping)
            elif isinstance(item, bootstrap.Defer):
                if item.body is not None:
                    rename_statements(item.body, mapping)
                elif isinstance(item.value, bootstrap.Assign):
                    rename_expr(item.value.target, mapping)
                    rename_expr(item.value.value, mapping)
                else:
                    rename_expr(item.value, mapping)

    def sanitize_c_local_names(module) -> None:
        for function in module.functions:
            names = {name for name, _ in function.params}
            collect_local_names(function.body, names)
            mapping = {name: _safe_local(name) for name in names if name in _C_RESERVED}
            if not mapping:
                continue
            function.params = [
                (mapping.get(name, name), typ) for name, typ in function.params
            ]
            rename_statements(function.body, mapping)

    original_emit_c = bootstrap.emit_c

    def emit_c(module, *args, **kwargs):
        # Semântica Sotlas já foi validada com os nomes originais. A partir
        # daqui tratamos somente detalhes do lowering C.
        sanitize_c_local_names(module)
        mark_mutable_arrays(module)
        code = original_emit_c(module, *args, **kwargs)

        # O emissor bootstrap historicamente transformava arrays locais em
        # ``static const``. Os marcadores tornam a correção exata por tipo, sem
        # substituir declarações imutáveis homônimas em outras funções.
        code = code.replace(f"static const {_MUT_AUTO_MARKER} ", "")
        code = code.replace(f"static {_MUT_AUTO_MARKER} ", "")
        code = code.replace(f"{_MUT_AUTO_MARKER} ", "")
        code = code.replace(f"static const {_MUT_STATIC_MARKER} ", "static ")
        code = code.replace(f"static {_MUT_STATIC_MARKER} ", "static ")
        code = code.replace(f"{_MUT_STATIC_MARKER} ", "static ")
        return code

    bootstrap.emit_c = emit_c

    # Headers recebem a mesma sanitização de parâmetros para que a assinatura
    # pública e a unidade C usem nomes backend-safe de forma determinística.
    original_emit_header = bootstrap.emit_header

    def emit_header(module, *args, **kwargs):
        sanitize_c_local_names(module)
        return original_emit_header(module, *args, **kwargs)

    bootstrap.emit_header = emit_header
    bootstrap._FRONTEND_EXTENSIONS_INSTALLED = True
