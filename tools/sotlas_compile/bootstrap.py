"""Frontend Sotlas Bootstrap: lexer, parser recursivo, tipagem, verificação unsafe e emissor C11.

Este módulo é deliberadamente independente do shell legado do Baken OS. Ele é
o contrato executável do subconjunto procedural da linguagem Sotlas:
módulos, structs com atributos, enums, globais/constantes, funções, tipos fixos,
arrays fixos [T; N], ponteiros unsafe, casts ('as'), expressões, fluxo e mangling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


class SotlasBootstrapError(Exception):
    def __init__(self, message: str, line: int = 1, column: int = 1, file: str | None = None, source: str | None = None):
        self.message = message
        self.line = line
        self.column = column
        self.file = file
        self.source = source
        loc = f"{file}:{line}:{column}" if file else f"{line}:{column}"
        snippet = ""
        if source:
            lines = source.splitlines()
            if 1 <= line <= len(lines):
                src_line = lines[line - 1]
                pointer = " " * (max(0, column - 1)) + "^"
                snippet = f"\n  {src_line}\n  {pointer}"
        super().__init__(f"{loc}: {message}{snippet}")

# Alias de compatibilidade
Cq01Error = SotlasBootstrapError


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


KEYWORDS = {"module", "import", "pub", "struct", "class", "enum", "fn", "let", "mut",
            "const", "static", "return", "break", "continue", "if", "else", "while", "for", "in",
            "unsafe", "true", "false", "as", "null", "defer", "loop"}
MULTI = ("::", "->", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "&=", "|=", "^=", "<<=", ">>=", "&&", "||", "<<", ">>", "..")
SINGLE = set(";,:{}()[]=+-*/%!<>&|^~.")
PRIMITIVES = {"void", "bool", "u8", "u16", "u32", "u64", "usize",
              "i8", "i16", "i32", "i64", "isize", "f32", "f64", "str"}
C_TYPES = {"void": "void", "bool": "_Bool", "u8": "uint8_t", "u16": "uint16_t",
           "u32": "uint32_t", "u64": "uint64_t", "usize": "size_t",
           "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
           "isize": "intptr_t", "f32": "float", "f64": "double", "str": "char"}


def lex(source: str, filename: str | None = None) -> list[Token]:
    tokens: list[Token] = []
    i = line = 0
    column = 1
    while i < len(source):
        ch = source[i]
        if ch in " \t\r":
            i += 1; column += 1; continue
        if ch == "\n":
            i += 1; line += 1; column = 1; continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            if end < 0: break
            column = 1; line += 1; i = end + 1; continue
        if source.startswith("/*", i):
            end = source.find("*/", i)
            if end < 0:
                raise SotlasBootstrapError("comentário de bloco não finalizado", line + 1, column, filename, source)
            block_text = source[i:end + 2]
            nl_count = block_text.count("\n")
            if nl_count > 0:
                line += nl_count
                column = len(block_text) - block_text.rfind("\n")
            else:
                column += len(block_text)
            i = end + 2
            continue
        start_col = column
        # Atributos: @ident ou @ident(args)
        if ch == "@":
            match = re.match(r"@[A-Za-z_][A-Za-z0-9_]*(?:\([^\)]*\))?", source[i:])
            if match:
                text = match.group(0)
                tokens.append(Token("ATTR", text, line + 1, start_col))
                i += len(text); column += len(text); continue
        # Strings literais com escape (\", \\)
        if ch == '"':
            j = i + 1
            while j < len(source):
                if source[j] == '\\':
                    j += 2
                    continue
                if source[j] == '"':
                    break
                j += 1
            if j >= len(source):
                raise SotlasBootstrapError("string literal não terminada", line + 1, start_col, filename, source)
            text = source[i:j + 1]
            tokens.append(Token("STRING", text, line + 1, start_col))
            i = j + 1; column += len(text); continue
        # Char literais
        if ch == "'":
            j = i + 1
            while j < len(source):
                if source[j] == '\\':
                    j += 2
                    continue
                if source[j] == "'":
                    break
                j += 1
            if j >= len(source):
                raise SotlasBootstrapError("caractere literal não terminado", line + 1, start_col, filename, source)
            text = source[i:j + 1]
            tokens.append(Token("CHAR", text, line + 1, start_col))
            i = j + 1; column += len(text); continue
        pair = next((item for item in MULTI if source.startswith(item, i)), None)
        if pair:
            tokens.append(Token(pair, pair, line + 1, start_col)); i += len(pair); column += len(pair); continue
        if ch in SINGLE:
            tokens.append(Token(ch, ch, line + 1, start_col)); i += 1; column += 1; continue
        if ch.isdigit():
            match = re.match(r"(?:0x[0-9A-Fa-f]+|[0-9]+(?:\.[0-9]+)?)", source[i:])
            assert match
            text = match.group(0); tokens.append(Token("NUMBER", text, line + 1, start_col)); i += len(text); column += len(text); continue
        if ch.isalpha() or ch == "_":
            match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", source[i:])
            assert match
            text = match.group(0); tokens.append(Token(text if text in KEYWORDS else "IDENT", text, line + 1, start_col)); i += len(text); column += len(text); continue
        raise SotlasBootstrapError(f"caractere léxico inválido: {ch!r}", line + 1, column, filename, source)
    tokens.append(Token("EOF", "", line + 1, column))
    return tokens


@dataclass
class Type:
    name: str
    pointer: bool = False
    mutable: bool = False
    is_array: bool = False
    array_size: int | str = 0
    elem_type: Type | None = None

    def base_c(self) -> str:
        if self.is_array and self.elem_type:
            return self.elem_type.base_c()
        base = C_TYPES.get(self.name, self.name)
        if self.pointer:
            prefix = "" if self.mutable else "const "
            return f"{prefix}{base} *"
        return base

    def array_dims(self) -> str:
        if not self.is_array:
            return ""
        child_dims = self.elem_type.array_dims() if self.elem_type else ""
        return f"[{self.array_size}]{child_dims}"

    def c(self) -> str:
        if self.is_array:
            return f"{self.base_c()} *"
        base = C_TYPES.get(self.name, self.name)
        if self.pointer:
            prefix = "" if self.mutable else "const "
            return f"{prefix}{base} *"
        return base

    def c_decl(self, var_name: str) -> str:
        if self.is_array:
            return f"{self.base_c()} {var_name}{self.array_dims()}"
        return f"{self.c()} {var_name}"


@dataclass
class Expr: token: Token
@dataclass
class Number(Expr): value: str
@dataclass
class Boolean(Expr): value: bool
@dataclass
class StringLit(Expr): value: str
@dataclass
class CharLit(Expr): value: str
@dataclass
class NullLit(Expr): pass
@dataclass
class Name(Expr): value: str
@dataclass
class EnumAccess(Expr): enum_name: str; variant: str
@dataclass
class Unary(Expr): op: str; value: Expr
@dataclass
class Binary(Expr): left: Expr; op: str; right: Expr
@dataclass
class Call(Expr): callee: str; args: list[Expr]
@dataclass
class Index(Expr): target: Expr; index: Expr
@dataclass
class Member(Expr): target: Expr; field: str; is_pointer_target: bool = False
@dataclass
class MethodCall(Expr):
    target: Expr
    method: str
    args: list[Expr]
    target_type: Type | None = None
    pass_by_ref: bool = False
@dataclass
class Cast(Expr): expr: Expr; target_type: Type
@dataclass
class ArrayLit(Expr):
    elements: list[Expr]
    is_repeat: bool = False
    repeat_size: int | str = 0
@dataclass
class StructLit(Expr):
    struct_name: str
    fields: list[tuple[str, Expr]]
@dataclass
class IfExpr(Expr):
    condition: Expr
    then_expr: Expr
    else_expr: Expr

@dataclass
class Stmt: token: Token
@dataclass
class Let(Stmt): name: str; type: Type | None; value: Expr
@dataclass
class Assign(Stmt): target: Expr; value: Expr
@dataclass
class Return(Stmt): value: Expr | None
@dataclass
class Break(Stmt): pass
@dataclass
class Continue(Stmt): pass
@dataclass
class Loop(Stmt): body: list[Stmt]
@dataclass
class If(Stmt): condition: Expr; then_body: list[Stmt]; else_body: list[Stmt]
@dataclass
class While(Stmt): condition: Expr; body: list[Stmt]
@dataclass
class For(Stmt):
    var_name: str
    start: Expr
    end: Expr
    body: list[Stmt]
    is_mut: bool = False
@dataclass
class Unsafe(Stmt): body: list[Stmt]
@dataclass
class Expression(Stmt): value: Expr
@dataclass
class Defer(Stmt):
    value: Expr | None = None
    body: list[Stmt] | None = None

    def __post_init__(self):
        if self.value is None and self.body is None:
            raise ValueError("Defer must have either value or body")
        if self.value is not None and self.body is not None:
            raise ValueError("Defer cannot have both value and body")

@dataclass
class FieldDef: name: str; type: Type
@dataclass
class Struct:
    name: str
    fields: list[FieldDef]
    public: bool = False
    attributes: list[str] = field(default_factory=list)

@dataclass
class Class:
    name: str
    fields: list[FieldDef]
    methods: list[Function]
    public: bool = False
    attributes: list[str] = field(default_factory=list)

@dataclass
class EnumVariant:
    name: str
    value: int | None = None

@dataclass
class Enum:
    name: str
    variants: list[EnumVariant]
    public: bool = False

@dataclass
class Global:
    name: str
    type: Type
    value: Expr
    is_const: bool = False
    is_mut: bool = False
    public: bool = False

@dataclass
class Function:
    name: str
    params: list[tuple[str, Type]]
    result: Type
    body: list[Stmt]
    public: bool = False
    attributes: list[str] = field(default_factory=list)

@dataclass
class Module:
    name: str
    imports: list[str] = field(default_factory=list)
    structs: list[Struct] = field(default_factory=list)
    classes: list[Class] = field(default_factory=list)
    enums: list[Enum] = field(default_factory=list)
    globals: list[Global] = field(default_factory=list)
    functions: list[Function] = field(default_factory=list)
    filename: str | None = None
    source: str | None = None


class Parser:
    def __init__(self, tokens: list[Token], filename: str | None = None, source: str | None = None):
        self.tokens = tokens
        self.at = 0
        self.filename = filename
        self.source = source

    @property
    def current(self) -> Token: return self.tokens[self.at]

    def accept(self, kind: str) -> Token | None:
        if self.current.kind == kind:
            token = self.current; self.at += 1; return token
        return None

    def expect(self, kind: str) -> Token:
        token = self.accept(kind)
        if token: return token
        raise SotlasBootstrapError(f"esperado {kind}, encontrado {self.current.kind}",
                        self.current.line, self.current.column, self.filename, self.source)

    def ident(self) -> str: return self.expect("IDENT").text

    def path(self) -> str:
        parts = [self.ident()]
        while self.current.kind == "::" and self.tokens[self.at + 1].kind == "IDENT":
            self.at += 1; parts.append(self.ident())
        return "::".join(parts)

    def type(self) -> Type:
        if self.accept("!"):
            return Type("void")
        # Array fixo: [T; N]
        if self.accept("["):
            elem_type = self.type()
            self.expect(";")
            if self.current.kind == "NUMBER":
                size_tok = self.expect("NUMBER")
                size = int(size_tok.text, 0)
            else:
                size_tok = self.expect("IDENT")
                size = size_tok.text
            self.expect("]")
            return Type(name=elem_type.name, pointer=elem_type.pointer, mutable=elem_type.mutable, is_array=True, array_size=size, elem_type=elem_type)
        if self.accept("&"):
            is_mut = bool(self.accept("mut"))
            inner = self.type()
            return Type(name=inner.name, pointer=True, mutable=is_mut, is_array=inner.is_array, array_size=inner.array_size, elem_type=inner.elem_type)
        pointer = False; mutable = False
        if self.accept("*"):
            pointer = True
            if self.accept("mut"): mutable = True
            elif self.accept("const"): mutable = False
            elif self.current.kind == "IDENT" and self.current.text in ("const", "mut"):
                mutable = (self.current.text == "mut")
                self.at += 1
            inner = self.type()
            return Type(name=inner.name, pointer=True, mutable=mutable, is_array=inner.is_array, array_size=inner.array_size, elem_type=inner.elem_type)
        return Type(self.ident(), pointer, mutable)

    def parse(self) -> Module:
        self.expect("module")
        module = Module(self.path(), filename=self.filename, source=self.source)
        self.expect(";")
        while self.current.kind != "EOF":
            if self.accept("import"):
                module.imports.append(self.path())
                self.expect("::"); self.expect("*"); self.expect(";")
                continue

            # Coleta atributos opcionais antes de declarações
            attributes: list[str] = []
            while self.current.kind == "ATTR":
                attributes.append(self.accept("ATTR").text)

            public = bool(self.accept("pub"))

            if self.accept("struct"):
                name = self.ident(); self.expect("{"); fields = []
                while not self.accept("}"):
                    self.accept("pub")
                    fields.append(FieldDef(self.ident(), self._field_type()))
                    self.expect(";")
                module.structs.append(Struct(name, fields, public, attributes))
                continue

            if self.accept("class"):
                name = self.ident()
                self.expect("{")
                fields = []
                methods = []
                while not self.accept("}"):
                    member_attrs: list[str] = []
                    while self.current.kind == "ATTR":
                        member_attrs.append(self.accept("ATTR").text)
                    member_pub = bool(self.accept("pub"))
                    if self.accept("fn"):
                        mname = self.ident()
                        self.expect("(")
                        mparams = []
                        if not self.accept(")"):
                            while True:
                                pname = self.ident()
                                self.expect(":")
                                ptype = self.type()
                                mparams.append((pname, ptype))
                                if self.accept(")"):
                                    break
                                self.expect(",")
                        mresult = self.type() if self.accept("->") else Type("void")
                        mbody = self.block()
                        fn_name = f"{name}_{mname}"
                        methods.append(Function(fn_name, mparams, mresult, mbody, member_pub, member_attrs))
                    else:
                        fields.append(FieldDef(self.ident(), self._field_type()))
                        self.expect(";")
                cls = Class(name, fields, methods, public, attributes)
                module.classes.append(cls)
                module.structs.append(Struct(name, fields, public, attributes))
                for m in methods:
                    module.functions.append(m)
                continue

            if self.accept("enum"):
                name = self.ident(); self.expect("{"); variants = []
                while not self.accept("}"):
                    vname = self.ident()
                    vval = None
                    if self.accept("="):
                        val_tok = self.expect("NUMBER")
                        vval = int(val_tok.text, 0)
                    variants.append(EnumVariant(vname, vval))
                    if not self.accept(","):
                        if self.current.kind != "}":
                            self.expect(",")
                module.enums.append(Enum(name, variants, public))
                continue

            if self.accept("const"):
                name = self.ident(); self.expect(":"); typ = self.type()
                self.expect("="); val = self.expression(); self.expect(";")
                module.globals.append(Global(name, typ, val, is_const=True, is_mut=False, public=public))
                continue

            if self.accept("static"):
                is_mut = bool(self.accept("mut"))
                name = self.ident(); self.expect(":"); typ = self.type()
                self.expect("="); val = self.expression(); self.expect(";")
                module.globals.append(Global(name, typ, val, is_const=False, is_mut=is_mut, public=public))
                continue

            if self.accept("fn"):
                module.functions.append(self.function(public, attributes))
                continue

            raise SotlasBootstrapError("declaração de topo Sotlas Bootstrap inválida", self.current.line, self.current.column, self.filename, self.source)
        return module

    def _field_type(self) -> Type: self.expect(":"); return self.type()

    def function(self, public: bool, attributes: list[str] | None = None) -> Function:
        name = self.ident(); self.expect("("); params = []
        if not self.accept(")"):
            while True:
                pname = self.ident(); self.expect(":"); params.append((pname, self.type()))
                if self.accept(")"): break
                self.expect(",")
        result = Type("void")
        if self.accept("->"): result = self.type()
        return Function(name, params, result, self.block(), public, attributes or [])

    def block(self) -> list[Stmt]:
        self.expect("{"); body = []
        while not self.accept("}"): body.append(self.statement())
        return body

    def statement(self) -> Stmt:
        token = self.current
        if self.accept("let"):
            is_mut = bool(self.accept("mut"))
            name = self.ident(); typ = None
            if self.accept(":"): typ = self.type()
            self.expect("="); value = self.expression(); self.expect(";")
            return Let(token, name, typ, value)
        if self.accept("const"):
            name = self.ident(); typ = None
            if self.accept(":"): typ = self.type()
            self.expect("="); value = self.expression(); self.expect(";")
            return Let(token, name, typ, value)
        if self.accept("static"):
            self.accept("const")
            self.accept("mut")
            name = self.ident(); typ = None
            if self.accept(":"): typ = self.type()
            self.expect("="); value = self.expression(); self.expect(";")
            return Let(token, name, typ, value)
        if self.accept("return"):
            value = None if self.current.kind == ";" else self.expression()
            self.expect(";"); return Return(token, value)
        if self.accept("break"):
            self.expect(";")
            return Break(token)
        if self.accept("continue"):
            self.expect(";")
            return Continue(token)
        if self.accept("if"):
            condition = self.expression()
            then_body = self.block()
            else_body = []
            if self.accept("else"):
                if self.current.kind == "if":
                    else_body = [self.statement()]
                else:
                    else_body = self.block()
            return If(token, condition, then_body, else_body)
        if self.accept("while"): return While(token, self.expression(), self.block())
        if self.accept("loop"): return Loop(token, self.block())
        if self.accept("for"):
            is_mut = bool(self.accept("mut"))
            var_name = self.ident()
            self.expect("in")
            start_expr = self.expression()
            self.expect("..")
            end_expr = self.expression()
            body = self.block()
            return For(token, var_name, start_expr, end_expr, body, is_mut)
        if self.accept("unsafe"): return Unsafe(token, self.block())
        if self.accept("defer"):
            if self.accept("{"):
                body = self.block()
                self.expect("}")
                return Defer(token, body=body)
            else:
                expr = self.expression()
                if self.accept("="):
                    value = self.expression()
                    self.expect(";")
                    return Defer(token, Assign(token, expr, value))
                self.expect(";")
                return Defer(token, expr)

        # Expressão ou Atribuição
        expr = self.expression()
        if self.accept("="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, value)
        if self.accept("+="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, Binary(token, expr, "+", value))
        if self.accept("-="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, Binary(token, expr, "-", value))
        if self.accept("*="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, Binary(token, expr, "*", value))
        if self.accept("/="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, Binary(token, expr, "/", value))
        if self.accept("&="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, Binary(token, expr, "&", value))
        if self.accept("|="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, Binary(token, expr, "|", value))
        self.expect(";")
        return Expression(token, expr)

    PRECEDENCE = {"||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "<": 7, "<=": 7, ">": 7, ">=": 7, "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10}

    def expression(self, minimum: int = 1) -> Expr:
        left = self.prefix()
        while self.current.kind in self.PRECEDENCE and self.PRECEDENCE[self.current.kind] >= minimum:
            op = self.current; self.at += 1
            right = self.expression(self.PRECEDENCE[op.kind] + 1)
            left = Binary(op, left, op.kind, right)
        return left

    def primary(self) -> Expr:
        token = self.current
        if self.accept("NUMBER"): expr = Number(token, token.text)
        elif self.accept("STRING"): expr = StringLit(token, token.text)
        elif self.accept("CHAR"): expr = CharLit(token, token.text)
        elif self.accept("null"): expr = NullLit(token)
        elif self.accept("true"): expr = Boolean(token, True)
        elif self.accept("false"): expr = Boolean(token, False)
        elif self.accept("unsafe"):
            self.expect("{")
            expr = self.expression()
            self.expect("}")
        elif self.accept("["):
            elements = []
            if not self.accept("]"):
                first = self.expression()
                if self.accept(";"):
                    if self.current.kind == "NUMBER":
                        size_tok = self.expect("NUMBER")
                        size = int(size_tok.text, 0)
                    else:
                        size_tok = self.expect("IDENT")
                        size = size_tok.text
                    self.expect("]")
                    expr = ArrayLit(token, [first], is_repeat=True, repeat_size=size)
                else:
                    elements.append(first)
                    while self.accept(","):
                        if self.current.kind == "]":
                            break
                        elements.append(self.expression())
                    self.expect("]")
                    expr = ArrayLit(token, elements)
            else:
                expr = ArrayLit(token, [])
        elif self.accept("if"):
            cond = self.expression()
            self.expect("{")
            then_expr = self.expression()
            self.expect("}")
            self.expect("else")
            if self.accept("{"):
                else_expr = self.expression()
                self.expect("}")
            elif self.current.kind == "if":
                else_expr = self.primary()
            else:
                else_expr = self.expression()
            expr = IfExpr(token, cond, then_expr, else_expr)
        elif self.accept("("):
            expr = self.expression()
            self.expect(")")
        elif self.accept("IDENT"):
            name = token.text
            # Struct literal: IDENT { field: val, ... }
            if (self.current.kind == "{" and self.at + 2 < len(self.tokens) and
                    self.tokens[self.at + 1].kind == "IDENT" and self.tokens[self.at + 2].kind == ":"):
                self.expect("{")
                fields = []
                while not self.accept("}"):
                    fname = self.ident()
                    self.expect(":")
                    fval = self.expression()
                    fields.append((fname, fval))
                    if not self.accept(","):
                        if self.current.kind != "}":
                            self.expect(",")
                expr = StructLit(token, name, fields)
            elif self.accept("::"):
                variant_name = self.ident()
                if self.accept("("):
                    args = []
                    if not self.accept(")"):
                        while True:
                            args.append(self.expression())
                            if self.accept(")"): break
                            self.expect(",")
                    expr = Call(token, f"{name}_{variant_name}", args)
                else:
                    expr = EnumAccess(token, name, variant_name)
            elif self.accept("("):
                args = []
                if not self.accept(")"):
                    while True:
                        args.append(self.expression())
                        if self.accept(")"): break
                        self.expect(",")
                expr = Call(token, name, args)
            else:
                expr = Name(token, name)
        else:
            raise SotlasBootstrapError(f"expressão inválida: {self.current.text!r}", token.line, token.column, self.filename, self.source)

        # Postfix parsing: chamadas adicionais, índices, membros/métodos, casts
        while True:
            if self.accept("["):
                idx = self.expression()
                self.expect("]")
                expr = Index(expr.token, expr, idx)
            elif self.accept("."):
                field_name = self.ident()
                if self.accept("("):
                    args = []
                    if not self.accept(")"):
                        while True:
                            args.append(self.expression())
                            if self.accept(")"): break
                            self.expect(",")
                    expr = MethodCall(expr.token, expr, field_name, args)
                else:
                    expr = Member(expr.token, expr, field_name)
            elif self.accept("as"):
                target_type = self.type()
                expr = Cast(expr.token, expr, target_type)
            else:
                break
        return expr

    def prefix(self) -> Expr:
        token = self.current
        if self.current.kind in ("!", "-", "*", "&", "~"):
            op = self.current.kind
            self.at += 1
            if op == "&":
                self.accept("mut")
            return Unary(token, op, self.prefix())
        return self.primary()


def parse(source: str, filename: str | None = None) -> Module:
    return Parser(lex(source, filename), filename=filename, source=source).parse()


def same_type(left: Type, right: Type) -> bool:
    return (left.name == right.name and
            left.pointer == right.pointer and
            left.is_array == right.is_array and
            (not left.is_array or str(left.array_size) == str(right.array_size)))


def assignable(actual: Type, expected: Type) -> bool:
    """Literais inteiros são polimórficos entre os inteiros fixos em Sotlas Bootstrap."""
    integers = {"u8", "u16", "u32", "u64", "usize", "i8", "i16", "i32", "i64", "isize"}
    if same_type(actual, expected):
        return True
    if not actual.pointer and not expected.pointer:
        if actual.name in integers and expected.name in integers:
            return True
        if actual.name in integers and (expected.is_array or expected.name not in PRIMITIVES):
            return True
        if actual.name in {"f32", "f64"} and expected.name in {"f32", "f64"}:
            return True
    if actual.name == "null" and expected.pointer:
        return True
    if actual.pointer and expected.pointer and (actual.name == expected.name or actual.name == "void" or expected.name == "void"):
        return True
    return False


BUILTIN_FUNCTIONS: dict[str, Function] = {
    "__outb": Function("__outb", [("port", Type("u16")), ("val", Type("u8"))], Type("void"), [], public=True, attributes=["@system"]),
    "__inb": Function("__inb", [("port", Type("u16"))], Type("u8"), [], public=True, attributes=["@system"]),
    "__cli": Function("__cli", [], Type("void"), [], public=True, attributes=["@system"]),
    "__sti": Function("__sti", [], Type("void"), [], public=True, attributes=["@system"]),
    "__hlt": Function("__hlt", [], Type("void"), [], public=True, attributes=["@system"]),
    "baken_runtime_init_assets": Function("baken_runtime_init_assets", [], Type("void"), [], public=True, attributes=["@system"]),
    "baken_runtime_run": Function("baken_runtime_run", [("boot_info", Type("void", pointer=True)), ("width", Type("u32")), ("height", Type("u32"))], Type("void"), [], public=True, attributes=["@system"]),
}


def check(module: Module, imported_fns: dict[str, Function] | None = None,
          imported_types: dict[str, Struct] | None = None,
          imported_enums: dict[str, Enum] | None = None,
          imported_globals: dict[str, Global] | None = None) -> None:
    source = module.source
    filename = module.filename

    struct_map: dict[str, Struct] = {s.name: s for s in module.structs}
    if imported_types: struct_map.update(imported_types)

    enum_map: dict[str, Enum] = {e.name: e for e in module.enums}
    if imported_enums: enum_map.update(imported_enums)

    global_map: dict[str, Global] = {g.name: g for g in module.globals}
    if imported_globals: global_map.update(imported_globals)

    functions = dict(BUILTIN_FUNCTIONS)
    user_funcs = {item.name: item for item in module.functions}
    functions.update(user_funcs)
    if imported_fns: functions.update(imported_fns)

    def expr_type(expr: Expr, scope: dict[str, Type], in_unsafe: bool, is_system_fn: bool) -> Type:
        if isinstance(expr, Number):
            return Type("f64" if "." in expr.value else "i64")
        if isinstance(expr, Boolean):
            return Type("bool")
        if isinstance(expr, StringLit):
            return Type("u8", pointer=True)
        if isinstance(expr, CharLit):
            return Type("u8")
        if isinstance(expr, NullLit):
            return Type("null", pointer=True)
        if isinstance(expr, ArrayLit):
            for element in expr.elements:
                expr_type(element, scope, in_unsafe, is_system_fn)
            if expr.is_repeat:
                inner = expr_type(expr.elements[0], scope, in_unsafe, is_system_fn)
                return Type(inner.name, pointer=inner.pointer, is_array=True, array_size=expr.repeat_size, elem_type=inner)
            inner = expr_type(expr.elements[0], scope, in_unsafe, is_system_fn) if expr.elements else Type("void")
            return Type(inner.name, pointer=inner.pointer, is_array=True, array_size=len(expr.elements), elem_type=inner)
        if isinstance(expr, StructLit):
            for _, value in expr.fields:
                expr_type(value, scope, in_unsafe, is_system_fn)
            return Type(expr.struct_name)
        if isinstance(expr, IfExpr):
            expr_type(expr.condition, scope, in_unsafe, is_system_fn)
            expr_type(expr.else_expr, scope, in_unsafe, is_system_fn)
            return expr_type(expr.then_expr, scope, in_unsafe, is_system_fn)
        if isinstance(expr, Name):
            if expr.value in scope:
                return scope[expr.value]
            if expr.value in global_map:
                return global_map[expr.value].type
            raise SotlasBootstrapError(
                f"símbolo não declarado: {expr.value}", expr.token.line,
                expr.token.column, filename, source,
            )
        if isinstance(expr, EnumAccess):
            return Type(expr.enum_name)
        if isinstance(expr, Unary):
            inner = expr_type(expr.value, scope, in_unsafe, is_system_fn)
            if expr.op == "*":
                if not in_unsafe and not is_system_fn:
                    raise SotlasBootstrapError(
                        "desreferenciamento de ponteiro exige bloco unsafe ou função @system",
                        expr.token.line, expr.token.column, filename, source,
                    )
                return Type(inner.name, pointer=False, mutable=inner.mutable)
            if expr.op == "&":
                return Type(inner.name, pointer=True, mutable=inner.mutable)
            if expr.op == "!":
                return Type("bool")
            return inner
        if isinstance(expr, Binary):
            left = expr_type(expr.left, scope, in_unsafe, is_system_fn)
            expr_type(expr.right, scope, in_unsafe, is_system_fn)
            return Type("bool") if expr.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||") else left
        if isinstance(expr, Call):
            for argument in expr.args:
                expr_type(argument, scope, in_unsafe, is_system_fn)
            function = functions.get(expr.callee)
            if function:
                return function.result
            raise SotlasBootstrapError(
                f"função não declarada: {expr.callee}", expr.token.line,
                expr.token.column, filename, source,
            )
        if isinstance(expr, Index):
            target_t = expr_type(expr.target, scope, in_unsafe, is_system_fn)
            expr_type(expr.index, scope, in_unsafe, is_system_fn)
            if target_t.is_array and target_t.elem_type:
                return target_t.elem_type
            return Type(target_t.name, pointer=False, mutable=target_t.mutable)
        if isinstance(expr, Member):
            target_t = expr_type(expr.target, scope, in_unsafe, is_system_fn)
            expr.is_pointer_target = target_t.pointer
            struct_def = struct_map.get(target_t.name)
            if struct_def:
                fld = next((f for f in struct_def.fields if f.name == expr.field), None)
                if fld: return fld.type
            return Type("u32")
        if isinstance(expr, MethodCall):
            target_t = expr_type(expr.target, scope, in_unsafe, is_system_fn)
            for argument in expr.args:
                expr_type(argument, scope, in_unsafe, is_system_fn)
            expr.target_type = target_t
            if expr.method == "as_ptr":
                return Type(target_t.name if not target_t.is_array else (target_t.elem_type.name if target_t.elem_type else "u8"), pointer=True)
            if expr.method == "abs":
                return target_t
            if expr.method == "add":
                return target_t
            method = functions.get(f"{target_t.name}_{expr.method}")
            if method:
                expr.pass_by_ref = bool(method.params and method.params[0][1].pointer and not target_t.pointer)
                return method.result
            raise SotlasBootstrapError(
                f"método não declarado: {target_t.name}.{expr.method}",
                expr.token.line, expr.token.column, filename, source,
            )
        if isinstance(expr, Cast):
            expr_type(expr.expr, scope, in_unsafe, is_system_fn)
            return expr.target_type
        raise AssertionError(type(expr))

    def statements(items: list[Stmt], scope: dict[str, Type], expected_return: Type, in_unsafe: bool, is_system_fn: bool) -> None:
        for item in items:
            if isinstance(item, Let):
                actual = expr_type(item.value, scope, in_unsafe, is_system_fn)
                declared = item.type or actual
                scope[item.name] = declared
            elif isinstance(item, Assign):
                target_type = expr_type(item.target, scope, in_unsafe, is_system_fn)
                value_type = expr_type(item.value, scope, in_unsafe, is_system_fn)
                if not assignable(value_type, target_type):
                    raise SotlasBootstrapError(
                        "atribuição incompatível", item.token.line,
                        item.token.column, filename, source,
                    )
            elif isinstance(item, Return):
                if item.value is not None:
                    actual = expr_type(item.value, scope, in_unsafe, is_system_fn)
                    if not assignable(actual, expected_return):
                        raise SotlasBootstrapError(
                            "retorno incompatível", item.token.line,
                            item.token.column, filename, source,
                        )
            elif isinstance(item, (Break, Continue)):
                continue
            elif isinstance(item, (If, While)):
                expr_type(item.condition, scope, in_unsafe, is_system_fn)
                statements(item.then_body if isinstance(item, If) else item.body, dict(scope), expected_return, in_unsafe, is_system_fn)
                if isinstance(item, If) and item.else_body:
                    statements(item.else_body, dict(scope), expected_return, in_unsafe, is_system_fn)
            elif isinstance(item, Loop):
                statements(item.body, dict(scope), expected_return, in_unsafe, is_system_fn)
            elif isinstance(item, For):
                expr_type(item.start, scope, in_unsafe, is_system_fn)
                expr_type(item.end, scope, in_unsafe, is_system_fn)
                for_scope = dict(scope)
                for_scope[item.var_name] = Type("usize")
                statements(item.body, for_scope, expected_return, in_unsafe, is_system_fn)
            elif isinstance(item, Unsafe):
                statements(item.body, scope, expected_return, in_unsafe=True, is_system_fn=is_system_fn)
            elif isinstance(item, Expression):
                expr_type(item.value, scope, in_unsafe, is_system_fn)
            elif isinstance(item, Defer):
                if item.body is not None:
                    statements(item.body, dict(scope), expected_return, in_unsafe, is_system_fn)
                elif isinstance(item.value, Assign):
                    expr_type(item.value.target, scope, in_unsafe, is_system_fn)
                    expr_type(item.value.value, scope, in_unsafe, is_system_fn)
                elif item.value is not None:
                    expr_type(item.value, scope, in_unsafe, is_system_fn)

    for function in module.functions:
        is_system = "@system" in function.attributes or "@inline" in function.attributes
        statements(function.body, dict(function.params), function.result, in_unsafe=False, is_system_fn=is_system)


def _c_ident(name: str) -> str:
    return name.replace("::", "__").replace("-", "_")


def _emit_expr(expr: Expr, mod_prefix: str = "") -> str:
    if isinstance(expr, Number): return expr.value
    if isinstance(expr, Boolean): return "1" if expr.value else "0"
    if isinstance(expr, StringLit): return f"((const uint8_t *){expr.value})"
    if isinstance(expr, CharLit): return expr.value
    if isinstance(expr, NullLit): return "NULL"
    if isinstance(expr, Name): return expr.value
    if isinstance(expr, EnumAccess): return f"{expr.enum_name}_{expr.variant}"
    if isinstance(expr, Unary):
        if expr.op == "&":
            return f"(&{_emit_expr(expr.value, mod_prefix)})"
        return f"({expr.op}{_emit_expr(expr.value, mod_prefix)})"
    if isinstance(expr, Binary): return f"({_emit_expr(expr.left, mod_prefix)} {expr.op} {_emit_expr(expr.right, mod_prefix)})"
    if isinstance(expr, Call):
        callee = expr.callee
        return f"{callee}(" + ", ".join(_emit_expr(item, mod_prefix) for item in expr.args) + ")"
    if isinstance(expr, MethodCall):
        if expr.method == "as_ptr":
            return _emit_expr(expr.target, mod_prefix)
        if expr.method == "abs":
            target_str = _emit_expr(expr.target, mod_prefix)
            return f"((int32_t)({target_str}) < 0 ? -(int32_t)({target_str}) : (int32_t)({target_str}))"
        if expr.method == "add":
            target_str = _emit_expr(expr.target, mod_prefix)
            arg_str = _emit_expr(expr.args[0], mod_prefix) if expr.args else "0"
            return f"(({target_str}) + ({arg_str}))"
        target_str = _emit_expr(expr.target, mod_prefix)
        if getattr(expr, "pass_by_ref", False):
            target_str = f"&({target_str})"
        fn_name = f"{expr.target_type.name}_{expr.method}" if expr.target_type else expr.method
        all_args = [target_str] + [_emit_expr(item, mod_prefix) for item in expr.args]
        return f"{fn_name}(" + ", ".join(all_args) + ")"
    if isinstance(expr, Index):
        return f"{_emit_expr(expr.target, mod_prefix)}[{_emit_expr(expr.index, mod_prefix)}]"
    if isinstance(expr, Member):
        arrow = "->" if getattr(expr, "is_pointer_target", False) else "."
        return f"{_emit_expr(expr.target, mod_prefix)}{arrow}{expr.field}"
    if isinstance(expr, Cast):
        return f"(({expr.target_type.c()})({_emit_expr(expr.expr, mod_prefix)}))"
    if isinstance(expr, ArrayLit):
        if expr.is_repeat:
            if isinstance(expr.elements[0], Number) and expr.elements[0].value == "0":
                return "{0}"
            val_s = _emit_expr(expr.elements[0], mod_prefix)
            if isinstance(expr.repeat_size, int):
                return "{" + ", ".join([val_s] * expr.repeat_size) + "}"
            return "{" + val_s + "}"
        return "{" + ", ".join(_emit_expr(e, mod_prefix) for e in expr.elements) + "}"
    if isinstance(expr, StructLit):
        field_strs = [f".{f} = {_emit_expr(v, mod_prefix)}" for f, v in expr.fields]
        return f"({expr.struct_name}){{" + ", ".join(field_strs) + "}"
    if isinstance(expr, IfExpr):
        cond_s = _emit_expr(expr.condition, mod_prefix)
        then_s = _emit_expr(expr.then_expr, mod_prefix)
        else_s = _emit_expr(expr.else_expr, mod_prefix)
        return f"(({cond_s}) ? ({then_s}) : ({else_s}))"
    raise AssertionError(type(expr))


PREAMBLE = """/* Gerado pelo frontend Sotlas Bootstrap. */
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

extern void baken_runtime_init_assets(void);
extern void baken_runtime_run(const void *boot_info, uint32_t width, uint32_t height);

static inline void __outb(uint16_t port, uint8_t val) {
#if defined(__x86_64__) || defined(__i386__)
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
#else
    (void)port; (void)val;
#endif
}

static inline uint8_t __inb(uint16_t port) {
#if defined(__x86_64__) || defined(__i386__)
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
#else
    (void)port; return 0;
#endif
}

static inline void __cli(void) {
#if defined(__x86_64__) || defined(__i386__)
    __asm__ volatile ("cli");
#endif
}

static inline void __sti(void) {
#if defined(__x86_64__) || defined(__i386__)
    __asm__ volatile ("sti");
#endif
}

static inline void __hlt(void) {
#if defined(__x86_64__) || defined(__i386__)
    __asm__ volatile ("hlt");
#endif
}
"""


def emit_c(module: Module, mangle: bool = False, include_preamble: bool = True,
           include_import_headers: bool = False) -> str:
    prefix = f"{_c_ident(module.name)}__" if mangle else ""
    lines = [PREAMBLE] if include_preamble else []
    if include_import_headers:
        lines.extend(f'#include "{_c_ident(name)}.h"' for name in module.imports)
        if module.imports:
            lines.append("")

    # Constantes escalares precisam existir antes de tipos que as usam como
    # tamanho de array (em C, static const não é uma expressão integral constante).
    for g in module.globals:
        if g.is_const and not g.type.is_array:
            lines.append(f"#define {g.name} (({g.type.c()})({_emit_expr(g.value, prefix)}))")
    if any(g.is_const and not g.type.is_array for g in module.globals):
        lines.append("")

    # Enums
    for enum_obj in module.enums:
        lines.append(f"typedef enum {enum_obj.name} {{")
        for v in enum_obj.variants:
            val_str = f" = {v.value}" if v.value is not None else ""
            lines.append(f"    {enum_obj.name}_{v.name}{val_str},")
        lines.append(f"}} {enum_obj.name};\n")

    # Structs
    for struct in module.structs:
        pack_attr = " __attribute__((packed))" if "@packed" in struct.attributes else ""
        lines.append(f"typedef struct{pack_attr} {struct.name} {{")
        for fld in struct.fields:
            lines.append(f"    {fld.type.c_decl(fld.name)};")
        lines.append(f"}} {struct.name};\n")

    # Globals / Consts
    for g in module.globals:
        if g.is_const and not g.type.is_array:
            continue
        specifier = "static const" if g.is_const else "static"
        if g.type.is_array and not g.type.pointer and isinstance(g.value, Number) and g.value.value == "0":
            lines.append(f"{specifier} {g.type.c_decl(g.name)} = {{0}};")
        elif isinstance(g.value, ArrayLit) and g.value.is_repeat:
            lines.append(f"{specifier} {g.type.c_decl(g.name)} = {_emit_expr(g.value, prefix)};")
        else:
            lines.append(f"{specifier} {g.type.c_decl(g.name)} = {_emit_expr(g.value, prefix)};")
    if module.globals: lines.append("")

    def _emit_defer_action(d: Defer, pad: str) -> str:
        if isinstance(d.value, Assign):
            target_str = _emit_expr(d.value.target, prefix) if isinstance(d.value.target, Expr) else str(d.value.target)
            return f"{pad}{target_str} = {_emit_expr(d.value.value, prefix)};"
        return f"{pad}{_emit_expr(d.value, prefix)};"

    def emit_statements(
        items: list[Stmt],
        depth: int,
        defer_scopes: list[list[Defer]],
        loop_scope_depth: int | None = None,
        ret_type: Type | None = None,
    ) -> list[str]:
        pad = "    " * depth; out: list[str] = []
        defer_scopes.append([])
        for item in items:
            if isinstance(item, Let):
                if item.type is not None:
                    typ = item.type
                    if (typ.is_array or typ.name not in PRIMITIVES) and not typ.pointer and isinstance(item.value, Number) and item.value.value == "0":
                        out.append(f"{pad}{typ.c_decl(item.name)} = {{0}};")
                    elif typ.is_array:
                        decl = typ.c_decl(item.name)
                        prefix_spec = "static " if decl.startswith("const ") else "static const "
                        out.append(f"{pad}{prefix_spec}{decl} = {_emit_expr(item.value, prefix)};")
                    else:
                        out.append(f"{pad}{typ.c_decl(item.name)} = {_emit_expr(item.value, prefix)};")
                else:
                    if isinstance(item.value, ArrayLit) and not item.value.is_repeat:
                        first_e = item.value.elements[0] if item.value.elements else None
                        if first_e and isinstance(first_e, Number):
                            out.append(f"{pad}uint32_t {item.name}[] = {_emit_expr(item.value, prefix)};")
                        else:
                            out.append(f"{pad}const uint8_t *{item.name}[] = {_emit_expr(item.value, prefix)};")
                    else:
                        out.append(f"{pad}__auto_type {item.name} = {_emit_expr(item.value, prefix)};")
            elif isinstance(item, Assign):
                target_str = _emit_expr(item.target, prefix) if isinstance(item.target, Expr) else str(item.target)
                if (isinstance(item.value, ArrayLit) and item.value.is_repeat and
                        isinstance(item.value.elements[0], Number) and item.value.elements[0].value == "0"):
                    out.append(f"{pad}__builtin_memset(&({target_str}), 0, sizeof({target_str}));")
                else:
                    out.append(f"{pad}{target_str} = {_emit_expr(item.value, prefix)};")
            elif isinstance(item, Defer):
                defer_scopes[-1].append(item)
            elif isinstance(item, Return):
                all_defers = [d for scope in reversed(defer_scopes) for d in reversed(scope)]
                if item.value:
                    val_str = _emit_expr(item.value, prefix)
                    if all_defers:
                        c_ret_type = ret_type.c() if ret_type else "int64_t"
                        out.append(f"{pad}{c_ret_type} _st_ret = {val_str};")
                        for d in all_defers:
                            out.append(_emit_defer_action(d, pad))
                        out.append(f"{pad}return _st_ret;")
                    else:
                        out.append(f"{pad}return {val_str};")
                else:
                    for d in all_defers:
                        if d.body is not None:
                            out.extend(emit_statements(d.body, depth, defer_scopes, loop_scope_depth, ret_type))
                        else:
                            out.append(_emit_defer_action(d, pad))
                    out.append(f"{pad}return;")
            elif isinstance(item, Break):
                if loop_scope_depth is not None:
                    loop_defers = [d for scope in reversed(defer_scopes[loop_scope_depth:]) for d in reversed(scope)]
                    for d in loop_defers:
                        if d.body is not None:
                            out.extend(emit_statements(d.body, depth, defer_scopes, loop_scope_depth, ret_type))
                        else:
                            out.append(_emit_defer_action(d, pad))
                out.append(f"{pad}break;")
            elif isinstance(item, Continue):
                if loop_scope_depth is not None:
                    loop_defers = [d for scope in reversed(defer_scopes[loop_scope_depth:]) for d in reversed(scope)]
                    for d in loop_defers:
                        if d.body is not None:
                            out.extend(emit_statements(d.body, depth, defer_scopes, loop_scope_depth, ret_type))
                        else:
                            out.append(_emit_defer_action(d, pad))
                out.append(f"{pad}continue;")
            elif isinstance(item, Expression):
                out.append(f"{pad}{_emit_expr(item.value, prefix)};")
            elif isinstance(item, Unsafe):
                out.extend(emit_statements(item.body, depth, defer_scopes, loop_scope_depth, ret_type))
            elif isinstance(item, While):
                out.append(f"{pad}while ({_emit_expr(item.condition, prefix)}) {{")
                out.extend(emit_statements(item.body, depth + 1, defer_scopes, loop_scope_depth=len(defer_scopes), ret_type=ret_type))
                out.append(f"{pad}}}")
            elif isinstance(item, Loop):
                out.append(f"{pad}for (;;) {{")
                out.extend(emit_statements(item.body, depth + 1, defer_scopes, loop_scope_depth=len(defer_scopes), ret_type=ret_type))
                out.append(f"{pad}}}")
            elif isinstance(item, For):
                start_str = _emit_expr(item.start, prefix)
                end_str = _emit_expr(item.end, prefix)
                out.append(f"{pad}for (size_t {item.var_name} = {start_str}; {item.var_name} < {end_str}; ++{item.var_name}) {{")
                out.extend(emit_statements(item.body, depth + 1, defer_scopes, loop_scope_depth=len(defer_scopes), ret_type=ret_type))
                out.append(f"{pad}}}")
            elif isinstance(item, If):
                out.append(f"{pad}if ({_emit_expr(item.condition, prefix)}) {{")
                out.extend(emit_statements(item.then_body, depth + 1, defer_scopes, loop_scope_depth, ret_type))
                out.append(f"{pad}}}")
                if item.else_body:
                    out.append(f"{pad}else {{")
                    out.extend(emit_statements(item.else_body, depth + 1, defer_scopes, loop_scope_depth, ret_type))
                    out.append(f"{pad}}}")
        current_defers = defer_scopes.pop()
        for d in reversed(current_defers):
            if d.body is not None:
                out.extend(emit_statements(d.body, depth, defer_scopes, loop_scope_depth, ret_type))
            else:
                out.append(_emit_defer_action(d, pad))
        return out

    # Forward declarations das funções
    for function in module.functions:
        is_export = "@export" in function.attributes or function.public
        fname = function.name if (is_export or not mangle) else f"{prefix}{function.name}"
        parameters = ", ".join(f"{typ.c_decl(name)}" for name, typ in function.params) or "void"
        inline_attr = "static inline " if "@inline" in function.attributes and not is_export else ""
        lines.append(f"{inline_attr}{function.result.c()} {fname}({parameters});")
    if module.functions: lines.append("")

    for function in module.functions:
        is_export = "@export" in function.attributes or function.public
        fname = function.name if (is_export or not mangle) else f"{prefix}{function.name}"
        parameters = ", ".join(f"{typ.c_decl(name)}" for name, typ in function.params) or "void"
        inline_attr = "static inline " if "@inline" in function.attributes and not is_export else ""
        lines.append(f"{inline_attr}{function.result.c()} {fname}({parameters}) {{")
        lines.extend(emit_statements(function.body, 1, defer_scopes=[], loop_scope_depth=None, ret_type=function.result))
        lines.append("}\n")
    return "\n".join(lines)


def _public_import_maps(imported_modules: list[Module] | None) -> tuple[dict, dict, dict, dict]:
    functions: dict[str, Function] = {}
    structs: dict[str, Struct] = {}
    enums: dict[str, Enum] = {}
    globals_: dict[str, Global] = {}
    for dependency in imported_modules or []:
        functions.update({fn.name: fn for fn in dependency.functions if fn.public})
        structs.update({item.name: item for item in dependency.structs if item.public})
        enums.update({item.name: item for item in dependency.enums if item.public})
        globals_.update({item.name: item for item in dependency.globals if item.public})
    return functions, structs, enums, globals_


def emit_header(module: Module) -> str:
    """Emite a ABI C pública de um módulo, derivada apenas do AST Sotlas."""
    module_id = _c_ident(module.name)
    guard = f"SOTLAS_GENERATED_{module_id.upper()}_H"
    lines = [
        "/* Interface gerada do AST Sotlas. Não edite. */",
        f"#ifndef {guard}",
        f"#define {guard}",
        "#include <stdint.h>",
        "#include <stddef.h>",
        "#include <stdbool.h>",
    ]
    lines.extend(f'#include "{_c_ident(name)}.h"' for name in module.imports)

    for global_ in module.globals:
        if global_.public and global_.is_const and not global_.type.is_array:
            lines.append(f"#define {global_.name} (({global_.type.c()})({_emit_expr(global_.value)}))")

    for enum_obj in module.enums:
        if not enum_obj.public:
            continue
        lines.append(f"typedef enum {enum_obj.name} {{")
        for variant in enum_obj.variants:
            value = f" = {variant.value}" if variant.value is not None else ""
            lines.append(f"    {enum_obj.name}_{variant.name}{value},")
        lines.append(f"}} {enum_obj.name};")

    for struct in module.structs:
        if not struct.public:
            continue
        pack_attr = " __attribute__((packed))" if "@packed" in struct.attributes else ""
        lines.append(f"typedef struct{pack_attr} {struct.name} {{")
        lines.extend(f"    {field.type.c_decl(field.name)};" for field in struct.fields)
        lines.append(f"}} {struct.name};")

    for function in module.functions:
        if not function.public and "@export" not in function.attributes:
            continue
        parameters = ", ".join(typ.c_decl(name) for name, typ in function.params) or "void"
        lines.append(f"{function.result.c()} {function.name}({parameters});")
    lines.extend(("", f"#endif /* {guard} */", ""))
    return "\n".join(lines)


def compile_module(module: Module, imported_modules: list[Module] | None = None,
                   include_import_headers: bool = False) -> str:
    imported = _public_import_maps(imported_modules)
    check(module, *imported)
    return emit_c(module, include_import_headers=include_import_headers)


def compile_source(source: str, filename: str | None = None,
                   imported_modules: list[Module] | None = None,
                   include_import_headers: bool = False) -> str:
    module = parse(source, filename=filename)
    return compile_module(module, imported_modules, include_import_headers)


def compile_file(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(compile_source(text, filename=str(source)), encoding="utf-8")


def compile_project(entry: Path) -> list[Module]:
    root = entry.parent
    while root.parent != root and not (root / "core").is_dir():
        root = root.parent
    units: dict[str, Module] = {}
    for path in list(root.rglob("*.sotlas")) + list(root.rglob("*.sth")) + list(root.rglob("*.st")):
        if "tests" in path.parts or "fixtures" in path.parts or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            unit = parse(text, filename=str(path))
            if unit.name in units and units[unit.name].filename != str(path):
                raise SotlasBootstrapError(f"módulo duplicado: {unit.name}", 1, 1, str(path), text)
            units[unit.name] = unit
        except SotlasBootstrapError as e:
            if "módulo duplicado" in e.message:
                raise
            continue
        except Exception:
            continue

    start_text = entry.read_text(encoding="utf-8")
    start = parse(start_text, filename=str(entry)).name
    order: list[Module] = []; visiting: list[str] = []; visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise SotlasBootstrapError("import circular: " + " -> ".join(visiting + [name]), 1, 1)
        if name in visited: return
        unit = units.get(name)
        if not unit:
            raise SotlasBootstrapError(f"import não resolvido: {name}", 1, 1)
        visiting.append(name)
        for dependency in unit.imports:
            visit(dependency)
        visiting.pop(); visited.add(name)
        imported_fns: dict[str, Function] = {}
        imported_types: dict[str, Struct] = {}
        imported_enums: dict[str, Enum] = {}
        imported_globals: dict[str, Global] = {}
        for dependency in unit.imports:
            dep = units[dependency]
            imported_fns.update({fn.name: fn for fn in dep.functions if fn.public})
            imported_types.update({s.name: s for s in dep.structs if s.public})
            imported_enums.update({e.name: e for e in dep.enums if e.public})
            imported_globals.update({g.name: g for g in dep.globals if g.public})
        check(unit, imported_fns, imported_types, imported_enums, imported_globals)
        order.append(unit)

    visit(start)
    return order


def emit_c_project(entry: Path, output: Path) -> None:
    modules = compile_project(entry)
    fragments = [PREAMBLE]
    for module in modules:
        fragments.append(emit_c(module, mangle=False, include_preamble=False))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(fragments), encoding="utf-8")
