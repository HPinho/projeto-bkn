module vortexc::token;

pub enum TokenKind {
    Eof = 0,
    Ident = 1,
    Number = 2,
    StringLit = 3,
    Keyword = 4,
    Symbol = 5,
    Attr = 6
}

@repr(C)
pub struct Token {
    kind: TokenKind;
    text: [u8; 64];
    line: u32;
    col: u32;
}

pub fn is_whitespace(ch: u8) -> bool {
    return ch == 32 || ch == 9 || ch == 13 || ch == 10;
}

pub fn is_alpha(ch: u8) -> bool {
    return (ch >= 65 && ch <= 90) || (ch >= 97 && ch <= 122) || ch == 95;
}

pub fn is_digit(ch: u8) -> bool {
    return ch >= 48 && ch <= 57;
}

pub fn is_alphanumeric(ch: u8) -> bool {
    return is_alpha(ch) || is_digit(ch);
}
