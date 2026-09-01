"""Sotlas Lexer — Tokenização de passagem única com rastreamento line:col."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from .token_types import TK, KEYWORDS, COMPOUND_KEYWORDS


class SotlasLexError(Exception):
    """Erro léxico com localização precisa."""
    def __init__(self, message: str, filename: str, line: int, col: int) -> None:
        super().__init__(f"{filename}:{line}:{col}: {message}")
        self.filename = filename
        self.line = line
        self.col = col


@dataclass(slots=True)
class Token:
    kind: TK
    value: str        # texto original do token
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.value!r}, {self.line}:{self.col})"


class Lexer:
    """Converte texto-fonte Sotlas em lista de Tokens.

    Suporta:
      - Comentários de linha  // ...
      - Comentários de bloco  (* ... *)
      - Literais: inteiro, hexadecimal (0x), binário (0b), float, string, char
      - Todos os operadores e delimitadores da gramática Sotlas
      - Palavra-chave composta 'co-owned' resolvida em pós-processamento
    """

    def __init__(self, source: str, filename: str = "<stdin>") -> None:
        self._src = source
        self._fn = filename
        self._pos = 0
        self._line = 1
        self._col = 1

    # ------------------------------------------------------------------
    # Interface Pública
    # ------------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.kind == TK.EOF:
                break
        return self._resolve_compound(tokens)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        i = self._pos + offset
        return self._src[i] if i < len(self._src) else "\0"

    def _advance(self) -> str:
        ch = self._src[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _skip_whitespace_and_comments(self) -> None:
        while self._pos < len(self._src):
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                while self._pos < len(self._src) and self._peek() != "\n":
                    self._advance()
            elif ch == "/" and self._peek(1) == "*":
                self._advance(); self._advance()  # consume /*
                while self._pos < len(self._src):
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance(); self._advance()  # consume */
                        break
                    self._advance()
            elif ch == "(" and self._peek(1) == "*":
                end_pos = self._src.find("*)", self._pos + 2)
                if end_pos != -1 and ")" not in self._src[self._pos + 2 : end_pos]:
                    inner = self._src[self._pos + 2 : end_pos]
                    self._pos = end_pos + 2
                    self._line += inner.count("\n")
                    if "\n" in inner:
                        self._col = len(inner) - inner.rfind("\n") + 1
                    else:
                        self._col += len(inner) + 4
                else:
                    break
            else:
                break

    def _next_token(self) -> Token:
        self._skip_whitespace_and_comments()
        if self._pos >= len(self._src):
            return Token(TK.EOF, "", self._line, self._col)

        line, col = self._line, self._col
        ch = self._peek()

        # Literais numéricos e identificadores/palavras-chave
        if ch.isdigit():
            return self._lex_number(line, col)
        if ch.isalpha() or ch == "_":
            return self._lex_ident_or_keyword(line, col)

        # String
        if ch == '"':
            return self._lex_string(line, col)

        # Char
        if ch == "'":
            return self._lex_char(line, col)

        # Operadores e delimitadores
        self._advance()
        ch2 = self._peek()

        match ch:
            case "{": return Token(TK.LBRACE,    "{",  line, col)
            case "}": return Token(TK.RBRACE,    "}",  line, col)
            case "(": return Token(TK.LPAREN,    "(",  line, col)
            case ")": return Token(TK.RPAREN,    ")",  line, col)
            case "[": return Token(TK.LBRACKET,  "[",  line, col)
            case "]": return Token(TK.RBRACKET,  "]",  line, col)
            case ";": return Token(TK.SEMICOLON, ";",  line, col)
            case ",": return Token(TK.COMMA,     ",",  line, col)
            case "@": return Token(TK.AT,        "@",  line, col)
            case "~": return Token(TK.TILDE,     "~",  line, col)

            case ".":
                if ch2 == ".":
                    self._advance()
                    return Token(TK.DOTDOT, "..", line, col)
                return Token(TK.DOT, ".", line, col)

            case ":":
                if ch2 == ":":
                    self._advance()
                    return Token(TK.DCOLON, "::", line, col)
                return Token(TK.COLON, ":", line, col)

            case "=":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.EQ, "==", line, col)
                if ch2 == ">":
                    self._advance()
                    return Token(TK.FAT_ARROW, "=>", line, col)
                return Token(TK.ASSIGN, "=", line, col)

            case "!":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.NEQ, "!=", line, col)
                return Token(TK.NOT, "!", line, col)

            case "&":
                if ch2 == "&":
                    self._advance()
                    return Token(TK.AND, "&&", line, col)
                if ch2 == "=":
                    self._advance()
                    return Token(TK.AND_EQ, "&=", line, col)
                return Token(TK.LAND, "&", line, col)

            case "|":
                if ch2 == "|":
                    self._advance()
                    return Token(TK.OR, "||", line, col)
                if ch2 == "=":
                    self._advance()
                    return Token(TK.OR_EQ, "|=", line, col)
                return Token(TK.LOR, "|", line, col)

            case "^":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.XOR_EQ, "^=", line, col)
                return Token(TK.XOR, "^", line, col)

            case "<":
                if ch2 == "<":
                    self._advance()
                    if self._peek() == "=":
                        self._advance()
                        return Token(TK.SHL_EQ, "<<=", line, col)
                    return Token(TK.SHL, "<<", line, col)
                if ch2 == "=":
                    self._advance()
                    return Token(TK.LTE, "<=", line, col)
                return Token(TK.LT, "<", line, col)

            case ">":
                if ch2 == ">":
                    self._advance()
                    if self._peek() == "=":
                        self._advance()
                        return Token(TK.SHR_EQ, ">>=", line, col)
                    return Token(TK.SHR, ">>", line, col)
                if ch2 == "=":
                    self._advance()
                    return Token(TK.GTE, ">=", line, col)
                return Token(TK.GT, ">", line, col)

            case "+":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.PLUS_EQ, "+=", line, col)
                return Token(TK.PLUS, "+", line, col)

            case "-":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.MINUS_EQ, "-=", line, col)
                if ch2 == ">":
                    self._advance()
                    return Token(TK.ARROW, "->", line, col)
                return Token(TK.MINUS, "-", line, col)

            case "*":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.STAR_EQ, "*=", line, col)
                return Token(TK.STAR, "*", line, col)

            case "/":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.SLASH_EQ, "/=", line, col)
                return Token(TK.SLASH, "/", line, col)

            case "%":
                if ch2 == "=":
                    self._advance()
                    return Token(TK.PCT_EQ, "%=", line, col)
                return Token(TK.PERCENT, "%", line, col)

            case "?":
                if ch2 == "?":
                    self._advance()
                    return Token(TK.NIL_COAL, "??", line, col)
                return Token(TK.QMARK, "?", line, col)

        raise SotlasLexError(
            f"caractere léxico inválido: {ch!r}", self._fn, line, col
        )

    def _lex_number(self, line: int, col: int) -> Token:
        start = self._pos - 1  # _advance não foi chamado ainda para o primeiro dígito
        # Refaz: _advance só foi chamado no loop interno, então aqui ainda temos o char.
        buf = []
        ch = self._peek()

        # Prefixo 0x ou 0b
        if ch == "0" and self._peek(1) in ("x", "X"):
            buf.append(self._advance())  # '0'
            buf.append(self._advance())  # 'x'
            if not self._peek().lower() in "0123456789abcdef":
                raise SotlasLexError("literal hex inválido", self._fn, line, col)
            while self._peek().lower() in "0123456789abcdef" or self._peek() == "_":
                c = self._advance()
                if c != "_": buf.append(c)
            return Token(TK.INT_LIT, "".join(buf), line, col)

        if ch == "0" and self._peek(1) in ("b", "B"):
            buf.append(self._advance())  # '0'
            buf.append(self._advance())  # 'b'
            if self._peek() not in ("0", "1"):
                raise SotlasLexError("literal binário inválido", self._fn, line, col)
            while self._peek() in ("0", "1", "_"):
                c = self._advance()
                if c != "_": buf.append(c)
            return Token(TK.INT_LIT, "".join(buf), line, col)

        # Inteiro ou float
        while self._peek().isdigit() or self._peek() == "_":
            c = self._advance()
            if c != "_": buf.append(c)

        if self._peek() == "." and self._peek(1).isdigit():
            buf.append(self._advance())  # '.'
            while self._peek().isdigit():
                buf.append(self._advance())
            return Token(TK.FLOAT_LIT, "".join(buf), line, col)

        return Token(TK.INT_LIT, "".join(buf), line, col)

    def _lex_ident_or_keyword(self, line: int, col: int) -> Token:
        buf = []
        while self._peek().isalnum() or self._peek() == "_":
            buf.append(self._advance())
        text = "".join(buf)
        kind = KEYWORDS.get(text, TK.IDENT)
        return Token(kind, text, line, col)

    def _lex_string(self, line: int, col: int) -> Token:
        self._advance()  # consume abre-aspas
        buf = []
        while self._pos < len(self._src) and self._peek() != '"':
            if self._peek() == "\\":
                self._advance()
                esc = self._advance()
                buf.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}.get(esc, esc))
            else:
                buf.append(self._advance())
        if self._pos >= len(self._src):
            raise SotlasLexError("string não terminada", self._fn, line, col)
        self._advance()  # consume fecha-aspas
        return Token(TK.STR_LIT, "".join(buf), line, col)

    def _lex_char(self, line: int, col: int) -> Token:
        self._advance()  # consume abre-aspas simples
        if self._peek() == "\\":
            self._advance()
            ch = self._advance()
        else:
            ch = self._advance()
        if self._peek() != "'":
            raise SotlasLexError("literal char inválido", self._fn, line, col)
        self._advance()  # consume fecha-aspas simples
        return Token(TK.CHAR_LIT, ch, line, col)

    @staticmethod
    def _resolve_compound(tokens: List[Token]) -> List[Token]:
        """Resolve 'co' '-' 'owned' → TK.KW_CO_OWNED em pós-processamento."""
        result: List[Token] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if (tok.kind == TK.IDENT and tok.value == "co"
                    and i + 2 < len(tokens)
                    and tokens[i + 1].kind == TK.MINUS
                    and tokens[i + 2].kind == TK.IDENT
                    and tokens[i + 2].value == "owned"):
                result.append(Token(TK.KW_CO_OWNED, "co-owned", tok.line, tok.col))
                i += 3
            else:
                result.append(tok)
                i += 1
        return result
