module sotlas_compile::main;
import core::mem::*;
import core::fmt::*;
import sotlas_compile::token::*;
import sotlas_compile::lexer::*;
import sotlas_compile::emitter::*;

pub const MAX_TOKENS: usize = 512;

@export
@system
pub fn sotlas_compile(source: *const u8, out_buf: *mut u8, max_len: usize) -> usize {
    if source == null || out_buf == null || max_len == 0 {
        return 0;
    }
    let mut tokens: [Token; 512] = 0;
    let tok_count: usize = lex_source(source, tokens as *mut Token, MAX_TOKENS);
    if tok_count == 0 {
        return 0;
    }
    return emit_c_from_tokens(tokens as *const Token, tok_count, out_buf, max_len);
}
