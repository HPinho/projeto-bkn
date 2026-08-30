"""Frontend Cq 0.1: lexer, parser recursivo, tipagem, verificação unsafe e emissor C11.

Este módulo é deliberadamente independente do shell legado do Baken OS. Ele é
o contrato executável do subconjunto procedural da linguagem Cq:
módulos, structs com atributos, enums, globais/constantes, funções, tipos fixos,
arrays fixos [T; N], ponteiros unsafe, casts ('as'), expressões, fluxo e mangling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


class Cq01Error(Exception):
    def __init__(self, message: str, line: int, column: int, file: str | None = None, source: str | None = None):
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


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


KEYWORDS = {"module", "import", "pub", "struct", "class", "enum", "fn", "let", "mut",
            "const", "static", "return", "break", "continue", "if", "else", "while", "unsafe",
            "true", "false", "as", "null", "defer"}
MULTI = ("::", "->", "==", "!=", "<=", ">=", "&&", "||", "<<", ">>")
SINGLE = set(";,:{}()[]=+-*/%!<>&|^~.")
PRIMITIVES = {"void", "bool", "u8", "u16", "u32", "u64", "usize",
              "i8", "i16", "i32", "i64", "isize", "f32", "f64"}
C_TYPES = {"void": "void", "bool": "_Bool", "u8": "uint8_t", "u16": "uint16_t",
           "u32": "uint32_t", "u64": "uint64_t", "usize": "size_t",
           "i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
           "isize": "intptr_t", "f32": "float", "f64": "double"}


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
                raise Cq01Error("comentário de bloco não finalizado", line + 1, column, filename, source)
            # Conta quebras de linha dentro do comentário de bloco
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
        # Strings literais
        if ch == '"':
            end = source.find('"', i + 1)
            if end < 0:
                raise Cq01Error("string literal não terminada", line + 1, start_col, filename, source)
            text = source[i:end + 1]
            tokens.append(Token("STRING", text, line + 1, start_col))
            i = end + 1; column += len(text); continue
        # Char literais
        if ch == "'":
            end = source.find("'", i + 1)
            if end < 0:
                raise Cq01Error("caractere literal não terminado", line + 1, start_col, filename, source)
            text = source[i:end + 1]
            tokens.append(Token("CHAR", text, line + 1, start_col))
            i = end + 1; column += len(text); continue
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
        raise Cq01Error(f"caractere léxico inválido: {ch!r}", line + 1, column, filename, source)
    tokens.append(Token("EOF", "", line + 1, column))
    return tokens


@dataclass
class Type:
    name: str
    pointer: bool = False
    mutable: bool = False
    is_array: bool = False
    array_size: int = 0

    def c(self) -> str:
        if self.is_array:
            base = C_TYPES.get(self.name, self.name)
            return f"{base}"
        base = C_TYPES.get(self.name, self.name)
        return f"{base} *" if self.pointer else base

    def c_decl(self, var_name: str) -> str:
        if self.is_array:
            base = C_TYPES.get(self.name, self.name)
            return f"{base} {var_name}[{self.array_size}]"
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
class Member(Expr): target: Expr; field: str
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
class If(Stmt): condition: Expr; then_body: list[Stmt]; else_body: list[Stmt]
@dataclass
class While(Stmt): condition: Expr; body: list[Stmt]
@dataclass
class Unsafe(Stmt): body: list[Stmt]
@dataclass
class Expression(Stmt): value: Expr
@dataclass
class Defer(Stmt): value: Expr

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
        raise Cq01Error(f"esperado {kind}, encontrado {self.current.kind}",
                        self.current.line, self.current.column, self.filename, self.source)

    def ident(self) -> str: return self.expect("IDENT").text

    def path(self) -> str:
        parts = [self.ident()]
        while self.current.kind == "::" and self.tokens[self.at + 1].kind == "IDENT":
            self.at += 1; parts.append(self.ident())
        return "::".join(parts)

    def type(self) -> Type:
        # Array fixo: [T; N]
        if self.accept("["):
            elem_type = self.type()
            self.expect(";")
            size_tok = self.expect("NUMBER")
            size = int(size_tok.text, 0)
            self.expect("]")
            return Type(name=elem_type.name, pointer=elem_type.pointer, mutable=elem_type.mutable, is_array=True, array_size=size)
        pointer = False; mutable = False
        if self.accept("*"):
            pointer = True
            if self.accept("mut"): mutable = True
            elif self.accept("const"): mutable = False
            elif self.current.kind == "IDENT" and self.current.text in ("const", "mut"):
                mutable = (self.current.text == "mut")
                self.at += 1
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

            raise Cq01Error("declaração de topo Cq 0.1 inválida", self.current.line, self.current.column, self.filename, self.source)
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
        if self.accept("unsafe"): return Unsafe(token, self.block())
        if self.accept("defer"):
            expr = self.expression()
            if self.accept("="):
                value = self.expression()
                self.expect(";")
                return Defer(token, Assign(token, expr, value))
            self.expect(";")
            return Defer(token, expr)

        # Expressão ou Atribuição (pode ser atribuição a identificador ou membro/índice)
        expr = self.expression()
        if self.accept("="):
            value = self.expression(); self.expect(";")
            return Assign(token, expr, value)
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
        elif self.accept("("):
            expr = self.expression()
            self.expect(")")
        elif self.accept("IDENT"):
            name = token.text
            if self.accept("::"):
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
            raise Cq01Error(f"expressão inválida: {self.current.text!r}", token.line, token.column, self.filename, self.source)

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
            self.at += 1
            return Unary(token, token.kind, self.prefix())
        return self.primary()


def parse(source: str, filename: str | None = None) -> Module:
    return Parser(lex(source, filename), filename=filename, source=source).parse()


def same_type(left: Type, right: Type) -> bool:
    return (left.name == right.name and
            left.pointer == right.pointer and
            left.is_array == right.is_array and
            (not left.is_array or left.array_size == right.array_size))


def assignable(actual: Type, expected: Type) -> bool:
    """Literais inteiros são polimórficos entre os inteiros fixos em Cq 0.1."""
    integers = {"u8", "u16", "u32", "u64", "usize", "i8", "i16", "i32", "i64", "isize"}
    if same_type(actual, expected):
        return True
    if not actual.pointer and not expected.pointer:
        if actual.name in integers and expected.name in integers:
            return True
        if actual.name in integers and (expected.is_array or expected.name not in PRIMITIVES):
            return True
    # Null literal é compatível com qualquer ponteiro
    if actual.name == "null" and expected.pointer:
        return True
    # Ponteiro mutável pode ser passado como ponteiro constante
    if actual.pointer and expected.pointer and actual.name == expected.name:
        return True
    return False


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

    known_types = set(PRIMITIVES) | set(struct_map.keys()) | set(enum_map.keys())

    # 1. Validação de Structs
    for struct in module.structs:
        for fld in struct.fields:
            if fld.type.name not in known_types:
                raise Cq01Error(f"tipo desconhecido: {fld.type.name}", 1, 1, filename, source)

BUILTIN_FUNCTIONS: dict[str, Function] = {
    "__outb": Function("__outb", [("port", Type("u16")), ("val", Type("u8"))], Type("void"), [], public=True, attributes=["@system"]),
    "__inb": Function("__inb", [("port", Type("u16"))], Type("u8"), [], public=True, attributes=["@system"]),
    "__cli": Function("__cli", [], Type("void"), [], public=True, attributes=["@system"]),
    "__sti": Function("__sti", [], Type("void"), [], public=True, attributes=["@system"]),
    "__hlt": Function("__hlt", [], Type("void"), [], public=True, attributes=["@system"]),
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

    known_types = set(PRIMITIVES) | set(struct_map.keys()) | set(enum_map.keys())

    # 1. Validação de Structs
    for struct in module.structs:
        for fld in struct.fields:
            if fld.type.name not in known_types:
                raise Cq01Error(f"tipo desconhecido: {fld.type.name}", 1, 1, filename, source)

    # 2. Validação de Funções
    functions = dict(BUILTIN_FUNCTIONS)
    user_funcs = {item.name: item for item in module.functions}
    if len(user_funcs) != len(module.functions):
        raise Cq01Error("função duplicada no módulo", 1, 1, filename, source)
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
        if isinstance(expr, Name):
            if expr.value in scope:
                return scope[expr.value]
            if expr.value in global_map:
                return global_map[expr.value].type
            raise Cq01Error(f"símbolo não declarado: {expr.value}", expr.token.line, expr.token.column, filename, source)
        if isinstance(expr, EnumAccess):
            enum_obj = enum_map.get(expr.enum_name)
            if not enum_obj:
                raise Cq01Error(f"enum não declarado: {expr.enum_name}", expr.token.line, expr.token.column, filename, source)
            variant = next((v for v in enum_obj.variants if v.name == expr.variant), None)
            if not variant:
                raise Cq01Error(f"variante '{expr.variant}' não existe no enum '{expr.enum_name}'", expr.token.line, expr.token.column, filename, source)
            return Type(expr.enum_name)
        if isinstance(expr, Unary):
            inner = expr_type(expr.value, scope, in_unsafe, is_system_fn)
            if expr.op == "*":
                # Dereferenciamento de ponteiro exige contexto unsafe ou função @system
                if not (in_unsafe or is_system_fn):
                    raise Cq01Error("desreferenciamento de ponteiro exige bloco unsafe ou função @system", expr.token.line, expr.token.column, filename, source)
                if not inner.pointer:
                    raise Cq01Error("operador '*' exige tipo ponteiro", expr.token.line, expr.token.column, filename, source)
                return Type(inner.name, pointer=False, mutable=inner.mutable)
            if expr.op == "&":
                return Type(inner.name, pointer=True, mutable=inner.mutable)
            if expr.op == "!":
                if inner.name != "bool":
                    raise Cq01Error("operador '!' exige bool", expr.token.line, expr.token.column, filename, source)
                return Type("bool")
            return inner
        if isinstance(expr, Binary):
            left = expr_type(expr.left, scope, in_unsafe, is_system_fn)
            right = expr_type(expr.right, scope, in_unsafe, is_system_fn)
            if not (assignable(left, right) or assignable(right, left)):
                raise Cq01Error(f"operandos com tipos incompatíveis ({left.name} e {right.name})", expr.token.line, expr.token.column, filename, source)
            return Type("bool") if expr.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||") else left
        if isinstance(expr, Call):
            function = functions.get(expr.callee)
            if not function:
                raise Cq01Error(f"função não declarada: {expr.callee}", expr.token.line, expr.token.column, filename, source)
            if len(expr.args) != len(function.params):
                raise Cq01Error(f"aridade inválida em {expr.callee} (esperados {len(function.params)}, recebidos {len(expr.args)})", expr.token.line, expr.token.column, filename, source)
            for argument, (_, expected) in zip(expr.args, function.params):
                actual = expr_type(argument, scope, in_unsafe, is_system_fn)
                if not assignable(actual, expected):
                    raise Cq01Error(f"argumento incompatível em {expr.callee} (esperado {expected.c()}, recebido {actual.c()})", expr.token.line, expr.token.column, filename, source)
            return function.result
        if isinstance(expr, Index):
            target_t = expr_type(expr.target, scope, in_unsafe, is_system_fn)
            idx_t = expr_type(expr.index, scope, in_unsafe, is_system_fn)
            if idx_t.name not in ("u8", "u16", "u32", "u64", "usize", "i8", "i16", "i32", "i64", "isize"):
                raise Cq01Error("índice de array deve ser inteiro", expr.token.line, expr.token.column, filename, source)
            if target_t.is_array:
                return Type(target_t.name, pointer=target_t.pointer, mutable=target_t.mutable)
            if target_t.pointer:
                if not (in_unsafe or is_system_fn):
                    raise Cq01Error("indexação de ponteiro bruto exige bloco unsafe ou função @system", expr.token.line, expr.token.column, filename, source)
                return Type(target_t.name, pointer=False, mutable=target_t.mutable)
            raise Cq01Error(f"tipo {target_t.name} não suporta indexação", expr.token.line, expr.token.column, filename, source)
        if isinstance(expr, Member):
            target_t = expr_type(expr.target, scope, in_unsafe, is_system_fn)
            expr.is_pointer_target = target_t.pointer
            struct_name = target_t.name
            if target_t.pointer and not (in_unsafe or is_system_fn):
                raise Cq01Error("acesso a campo de ponteiro exige bloco unsafe ou função @system", expr.token.line, expr.token.column, filename, source)
            struct_def = struct_map.get(struct_name)
            if not struct_def:
                raise Cq01Error(f"tipo '{struct_name}' não é uma struct", expr.token.line, expr.token.column, filename, source)
            fld = next((f for f in struct_def.fields if f.name == expr.field), None)
            if not fld:
                raise Cq01Error(f"campo '{expr.field}' não existe na struct '{struct_name}'", expr.token.line, expr.token.column, filename, source)
            return fld.type
        if isinstance(expr, MethodCall):
            target_t = expr_type(expr.target, scope, in_unsafe, is_system_fn)
            struct_name = target_t.name
            method_fn_name = f"{struct_name}_{expr.method}"
            function = functions.get(method_fn_name)
            if not function:
                raise Cq01Error(f"método '{expr.method}' não existe no tipo '{struct_name}'", expr.token.line, expr.token.column, filename, source)
            expr.target_type = target_t
            first_param = function.params[0] if function.params else None
            if first_param and first_param[1].pointer and not target_t.pointer:
                expr.pass_by_ref = True
            expected_args = function.params[1:] if first_param else []
            if len(expr.args) != len(expected_args):
                raise Cq01Error(f"aridade inválida no método {expr.method} (esperados {len(expected_args)}, recebidos {len(expr.args)})", expr.token.line, expr.token.column, filename, source)
            for argument, (_, expected) in zip(expr.args, expected_args):
                actual = expr_type(argument, scope, in_unsafe, is_system_fn)
                if not assignable(actual, expected):
                    raise Cq01Error(f"argumento incompatível no método {expr.method} (esperado {expected.c()}, recebido {actual.c()})", expr.token.line, expr.token.column, filename, source)
            return function.result
        if isinstance(expr, Cast):
            inner = expr_type(expr.expr, scope, in_unsafe, is_system_fn)
            if expr.target_type.name not in known_types:
                raise Cq01Error(f"tipo de cast desconhecido: {expr.target_type.name}", expr.token.line, expr.token.column, filename, source)
            if expr.target_type.pointer and not (in_unsafe or is_system_fn):
                raise Cq01Error("conversão explícita para ponteiro exige bloco unsafe ou função @system", expr.token.line, expr.token.column, filename, source)
            return expr.target_type
        raise AssertionError(type(expr))

    def statements(items: list[Stmt], scope: dict[str, Type], expected_return: Type, in_unsafe: bool, is_system_fn: bool) -> None:
        for item in items:
            if isinstance(item, Let):
                actual = expr_type(item.value, scope, in_unsafe, is_system_fn)
                declared = item.type or actual
                if not assignable(actual, declared):
                    raise Cq01Error(f"inicialização incompatível de '{item.name}'", item.token.line, item.token.column, filename, source)
                scope[item.name] = declared
            elif isinstance(item, Assign):
                if isinstance(item.target, Name):
                    if item.target.value not in scope and item.target.value not in global_map:
                        raise Cq01Error(f"atribuição a símbolo desconhecido: {item.target.value}", item.token.line, item.token.column, filename, source)
                    target_t = scope[item.target.value] if item.target.value in scope else global_map[item.target.value].type
                else:
                    target_t = expr_type(item.target, scope, in_unsafe, is_system_fn)
                val_t = expr_type(item.value, scope, in_unsafe, is_system_fn)
                if not assignable(val_t, target_t):
                    raise Cq01Error("atribuição incompatível", item.token.line, item.token.column, filename, source)
            elif isinstance(item, Return):
                actual = Type("void") if item.value is None else expr_type(item.value, scope, in_unsafe, is_system_fn)
                if not assignable(actual, expected_return):
                    raise Cq01Error("retorno incompatível", item.token.line, item.token.column, filename, source)
            elif isinstance(item, (Break, Continue)):
                continue
            elif isinstance(item, (If, While)):
                cond_t = expr_type(item.condition, scope, in_unsafe, is_system_fn)
                if cond_t.name != "bool":
                    raise Cq01Error("condição deve ser bool", item.token.line, item.token.column, filename, source)
                statements(item.then_body if isinstance(item, If) else item.body, dict(scope), expected_return, in_unsafe, is_system_fn)
                if isinstance(item, If) and item.else_body:
                    statements(item.else_body, dict(scope), expected_return, in_unsafe, is_system_fn)
            elif isinstance(item, Unsafe):
                statements(item.body, scope, expected_return, in_unsafe=True, is_system_fn=is_system_fn)
            elif isinstance(item, Expression):
                expr_type(item.value, scope, in_unsafe, is_system_fn)
            elif isinstance(item, Defer):
                if isinstance(item.value, Assign):
                    if isinstance(item.value.target, Name):
                        if item.value.target.value not in scope and item.value.target.value not in global_map:
                            raise Cq01Error(f"atribuição a símbolo desconhecido: {item.value.target.value}", item.token.line, item.token.column, filename, source)
                        target_t = scope[item.value.target.value] if item.value.target.value in scope else global_map[item.value.target.value].type
                    else:
                        target_t = expr_type(item.value.target, scope, in_unsafe, is_system_fn)
                    val_t = expr_type(item.value.value, scope, in_unsafe, is_system_fn)
                    if not assignable(val_t, target_t):
                        raise Cq01Error("atribuição incompatível", item.token.line, item.token.column, filename, source)
                else:
                    expr_type(item.value, scope, in_unsafe, is_system_fn)

    # 3. Validação dos Corpos de Função
    for function in module.functions:
        is_system = "@system" in function.attributes
        statements(function.body, dict(function.params), function.result, in_unsafe=False, is_system_fn=is_system)


def _c_ident(name: str) -> str:
    return name.replace("::", "__").replace("-", "_")


def _emit_expr(expr: Expr, mod_prefix: str = "") -> str:
    if isinstance(expr, Number): return expr.value
    if isinstance(expr, Boolean): return "1" if expr.value else "0"
    if isinstance(expr, StringLit): return f"((uint8_t *){expr.value})"
    if isinstance(expr, CharLit): return expr.value
    if isinstance(expr, NullLit): return "NULL"
    if isinstance(expr, Name): return expr.value
    if isinstance(expr, EnumAccess): return f"{expr.enum_name}_{expr.variant}"
    if isinstance(expr, Unary): return f"({expr.op}{_emit_expr(expr.value, mod_prefix)})"
    if isinstance(expr, Binary): return f"({_emit_expr(expr.left, mod_prefix)} {expr.op} {_emit_expr(expr.right, mod_prefix)})"
    if isinstance(expr, Call):
        callee = expr.callee
        return f"{callee}(" + ", ".join(_emit_expr(item, mod_prefix) for item in expr.args) + ")"
    if isinstance(expr, MethodCall):
        target_str = _emit_expr(expr.target, mod_prefix)
        if getattr(expr, "pass_by_ref", False):
            target_str = f"&({target_str})"
        fn_name = f"{expr.target_type.name}_{expr.method}"
        all_args = [target_str] + [_emit_expr(item, mod_prefix) for item in expr.args]
        return f"{fn_name}(" + ", ".join(all_args) + ")"
    if isinstance(expr, Index):
        return f"{_emit_expr(expr.target, mod_prefix)}[{_emit_expr(expr.index, mod_prefix)}]"
    if isinstance(expr, Member):
        arrow = "->" if getattr(expr, "is_pointer_target", False) else "."
        return f"{_emit_expr(expr.target, mod_prefix)}{arrow}{expr.field}"
    if isinstance(expr, Cast):
        return f"(({expr.target_type.c()})({_emit_expr(expr.expr, mod_prefix)}))"
    raise AssertionError(type(expr))


PREAMBLE = """/* Gerado pelo frontend Cq 0.1. */
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

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


def emit_c(module: Module, mangle: bool = False, include_preamble: bool = True) -> str:
    prefix = f"{_c_ident(module.name)}__" if mangle else ""
    lines = [PREAMBLE] if include_preamble else []

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
        specifier = "static const" if g.is_const else "static"
        if g.type.is_array and not g.type.pointer and isinstance(g.value, Number) and g.value.value == "0":
            lines.append(f"{specifier} {g.type.c_decl(g.name)} = {{0}};")
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
                typ = item.type or Type("i64")
                if (typ.is_array or typ.name not in PRIMITIVES) and not typ.pointer and isinstance(item.value, Number) and item.value.value == "0":
                    out.append(f"{pad}{typ.c_decl(item.name)} = {{0}};")
                else:
                    out.append(f"{pad}{typ.c_decl(item.name)} = {_emit_expr(item.value, prefix)};")
            elif isinstance(item, Assign):
                target_str = _emit_expr(item.target, prefix) if isinstance(item.target, Expr) else str(item.target)
                out.append(f"{pad}{target_str} = {_emit_expr(item.value, prefix)};")
            elif isinstance(item, Defer):
                defer_scopes[-1].append(item)
            elif isinstance(item, Return):
                all_defers = [d for scope in reversed(defer_scopes) for d in reversed(scope)]
                if item.value:
                    val_str = _emit_expr(item.value, prefix)
                    if all_defers:
                        c_ret_type = ret_type.c() if ret_type else "int64_t"
                        out.append(f"{pad}{c_ret_type} _cq_ret = {val_str};")
                        for d in all_defers:
                            out.append(_emit_defer_action(d, pad))
                        out.append(f"{pad}return _cq_ret;")
                    else:
                        out.append(f"{pad}return {val_str};")
                else:
                    for d in all_defers:
                        out.append(_emit_defer_action(d, pad))
                    out.append(f"{pad}return;")
            elif isinstance(item, Break):
                if loop_scope_depth is not None:
                    loop_defers = [d for scope in reversed(defer_scopes[loop_scope_depth:]) for d in reversed(scope)]
                    for d in loop_defers:
                        out.append(_emit_defer_action(d, pad))
                out.append(f"{pad}break;")
            elif isinstance(item, Continue):
                if loop_scope_depth is not None:
                    loop_defers = [d for scope in reversed(defer_scopes[loop_scope_depth:]) for d in reversed(scope)]
                    for d in loop_defers:
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
            out.append(_emit_defer_action(d, pad))
        return out

    # Forward declarations das funções
    for function in module.functions:
        is_export = "@export" in function.attributes
        fname = function.name if (is_export or not mangle) else f"{prefix}{function.name}"
        parameters = ", ".join(f"{typ.c()} {name}" for name, typ in function.params) or "void"
        lines.append(f"{function.result.c()} {fname}({parameters});")
    if module.functions: lines.append("")

    for function in module.functions:
        is_export = "@export" in function.attributes
        fname = function.name if (is_export or not mangle) else f"{prefix}{function.name}"
        parameters = ", ".join(f"{typ.c()} {name}" for name, typ in function.params) or "void"
        lines.append(f"{function.result.c()} {fname}({parameters}) {{")
        lines.extend(emit_statements(function.body, 1, defer_scopes=[], loop_scope_depth=None, ret_type=function.result))
        lines.append("}\n")
    return "\n".join(lines)


def compile_source(source: str, filename: str | None = None) -> str:
    module = parse(source, filename=filename)
    check(module)
    return emit_c(module)


def compile_file(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(compile_source(text, filename=str(source)), encoding="utf-8")


def compile_project(entry: Path) -> list[Module]:
    """Resolve um projeto Cq 0.1 multi-módulo sem depender do Baken OS legado."""
    root = entry.parent
    while root.parent != root and not (root / "core").is_dir():
        root = root.parent
    units: dict[str, Module] = {}
    for path in root.rglob("*.cq"):
        if "tests" in path.parts or "fixtures" in path.parts or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            unit = parse(text, filename=str(path))
            if unit.name in units and units[unit.name].filename != str(path):
                raise Cq01Error(f"módulo duplicado: {unit.name}", 1, 1, str(path), text)
            units[unit.name] = unit
        except Cq01Error as e:
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
            raise Cq01Error("import circular: " + " -> ".join(visiting + [name]), 1, 1)
        if name in visited: return
        unit = units.get(name)
        if not unit:
            raise Cq01Error(f"import não resolvido: {name}", 1, 1)
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

