module sotlas_compile::lexer;
import core::mem::*;
import core::fmt::*;
import sotlas_compile::token::*;

@system
pub fn lex_source(src: *const u8, tokens: *mut Token, max_tokens: usize) -> usize {
    if src == null || tokens == null || max_tokens == 0 {
        return 0;
    }
    let mut i: usize = 0;
    let mut tok_count: usize = 0;
    let mut line: u32 = 1;
    let mut col: u32 = 1;

    unsafe {
        while src[i] != 0 && tok_count < (max_tokens - 1) {
            let ch: u8 = src[i];

            // Whitespace
            if ch == 32 || ch == 9 || ch == 13 {
                i = i + 1;
                col = col + 1;
            } else if ch == 10 {
                i = i + 1;
                line = line + 1;
                col = 1;
            }
            // Comentário de linha //
            else if ch == 47 && src[i + 1] == 47 {
                i = i + 2;
                while src[i] != 0 && src[i] != 10 {
                    i = i + 1;
                }
            }
            // Comentário de bloco /* ... */
            else if ch == 47 && src[i + 1] == 42 {
                i = i + 2;
                while src[i] != 0 && !(src[i] == 42 && src[i + 1] == 47) {
                    if src[i] == 10 {
                        line = line + 1;
                        col = 1;
                    } else {
                        col = col + 1;
                    }
                    i = i + 1;
                }
                if src[i] != 0 {
                    i = i + 2;
                }
            }
            // Atributo @...
            else if ch == 64 {
                let start_i: usize = i;
                let start_col: u32 = col;
                i = i + 1;
                col = col + 1;
                while is_alphanumeric(src[i]) || src[i] == 40 || src[i] == 41 {
                    i = i + 1;
                    col = col + 1;
                }
                let len: usize = i - start_i;
                let mut tok: Token = 0;
                tok.kind = TokenKind::Attr;
                tok.line = line;
                tok.col = start_col;
                let mut k: usize = 0;
                while k < len && k < 63 {
                    tok.text[k] = src[start_i + k];
                    k = k + 1;
                }
                tok.text[k] = 0;
                tokens[tok_count] = tok;
                tok_count = tok_count + 1;
            }
            // String literal "..."
            else if ch == 34 {
                let start_col: u32 = col;
                i = i + 1;
                col = col + 1;
                let start_i: usize = i;
                while src[i] != 0 && src[i] != 34 {
                    i = i + 1;
                    col = col + 1;
                }
                let len: usize = i - start_i;
                if src[i] == 34 {
                    i = i + 1;
                    col = col + 1;
                }
                let mut tok: Token = 0;
                tok.kind = TokenKind::StringLit;
                tok.line = line;
                tok.col = start_col;
                let mut k: usize = 0;
                while k < len && k < 63 {
                    tok.text[k] = src[start_i + k];
                    k = k + 1;
                }
                tok.text[k] = 0;
                tokens[tok_count] = tok;
                tok_count = tok_count + 1;
            }
            // Identificador ou Palavra-chave
            else if is_alpha(ch) {
                let start_i: usize = i;
                let start_col: u32 = col;
                while is_alphanumeric(src[i]) {
                    i = i + 1;
                    col = col + 1;
                }
                let len: usize = i - start_i;
                let mut tok: Token = 0;
                tok.kind = TokenKind::Ident;
                tok.line = line;
                tok.col = start_col;
                let mut k: usize = 0;
                while k < len && k < 63 {
                    tok.text[k] = src[start_i + k];
                    k = k + 1;
                }
                tok.text[k] = 0;
                // Detecta keywords
                let txt_ptr: *const u8 = tok.text as *const u8;
                if str_eq(txt_ptr, "module") || str_eq(txt_ptr, "import") ||
                   str_eq(txt_ptr, "pub") || str_eq(txt_ptr, "struct") ||
                   str_eq(txt_ptr, "enum") || str_eq(txt_ptr, "fn") ||
                   str_eq(txt_ptr, "let") || str_eq(txt_ptr, "mut") ||
                   str_eq(txt_ptr, "return") || str_eq(txt_ptr, "if") ||
                   str_eq(txt_ptr, "else") || str_eq(txt_ptr, "while") ||
                   str_eq(txt_ptr, "unsafe") || str_eq(txt_ptr, "const") ||
                   str_eq(txt_ptr, "static") || str_eq(txt_ptr, "as") ||
                   str_eq(txt_ptr, "null") || str_eq(txt_ptr, "true") || str_eq(txt_ptr, "false") {
                    tok.kind = TokenKind::Keyword;
                }
                tokens[tok_count] = tok;
                tok_count = tok_count + 1;
            }
            // Número (dec ou hex)
            else if is_digit(ch) {
                let start_i: usize = i;
                let start_col: u32 = col;
                if ch == 48 && (src[i + 1] == 120 || src[i + 1] == 88) {
                    i = i + 2;
                    col = col + 2;
                    while is_alphanumeric(src[i]) {
                        i = i + 1;
                        col = col + 1;
                    }
                } else {
                    while is_digit(src[i]) || src[i] == 46 {
                        i = i + 1;
                        col = col + 1;
                    }
                }
                let len: usize = i - start_i;
                let mut tok: Token = 0;
                tok.kind = TokenKind::Number;
                tok.line = line;
                tok.col = start_col;
                let mut k: usize = 0;
                while k < len && k < 63 {
                    tok.text[k] = src[start_i + k];
                    k = k + 1;
                }
                tok.text[k] = 0;
                tokens[tok_count] = tok;
                tok_count = tok_count + 1;
            }
            // Símbolos multi-char (:: -> == != <= >= && || << >>)
            else if (ch == 58 && src[i + 1] == 58) || (ch == 45 && src[i + 1] == 62) ||
                    (ch == 61 && src[i + 1] == 61) || (ch == 33 && src[i + 1] == 61) ||
                    (ch == 60 && src[i + 1] == 61) || (ch == 62 && src[i + 1] == 61) ||
                    (ch == 38 && src[i + 1] == 38) || (ch == 124 && src[i + 1] == 124) ||
                    (ch == 60 && src[i + 1] == 60) || (ch == 62 && src[i + 1] == 62) {
                let mut tok: Token = 0;
                tok.kind = TokenKind::Symbol;
                tok.line = line;
                tok.col = col;
                tok.text[0] = src[i];
                tok.text[1] = src[i + 1];
                tok.text[2] = 0;
                tokens[tok_count] = tok;
                tok_count = tok_count + 1;
                i = i + 2;
                col = col + 2;
            }
            // Símbolos single-char
            else {
                let mut tok: Token = 0;
                tok.kind = TokenKind::Symbol;
                tok.line = line;
                tok.col = col;
                tok.text[0] = src[i];
                tok.text[1] = 0;
                tokens[tok_count] = tok;
                tok_count = tok_count + 1;
                i = i + 1;
                col = col + 1;
            }
        }

        // Token EOF
        let mut eof_tok: Token = 0;
        eof_tok.kind = TokenKind::Eof;
        eof_tok.line = line;
        eof_tok.col = col;
        eof_tok.text[0] = 0;
        tokens[tok_count] = eof_tok;
        tok_count = tok_count + 1;
    }
    return tok_count;
}
