module vortexc::emitter;
import core::mem::*;
import core::fmt::*;
import vortexc::token::*;

pub fn type_to_c(cq_type: *const u8, dest: *mut u8, max_len: usize) -> usize {
    if str_eq(cq_type, "u8") { return str_copy(dest, "uint8_t", max_len); }
    if str_eq(cq_type, "u16") { return str_copy(dest, "uint16_t", max_len); }
    if str_eq(cq_type, "u32") { return str_copy(dest, "uint32_t", max_len); }
    if str_eq(cq_type, "u64") { return str_copy(dest, "uint64_t", max_len); }
    if str_eq(cq_type, "usize") { return str_copy(dest, "size_t", max_len); }
    if str_eq(cq_type, "i8") { return str_copy(dest, "int8_t", max_len); }
    if str_eq(cq_type, "i16") { return str_copy(dest, "int16_t", max_len); }
    if str_eq(cq_type, "i32") { return str_copy(dest, "int32_t", max_len); }
    if str_eq(cq_type, "i64") { return str_copy(dest, "int64_t", max_len); }
    if str_eq(cq_type, "isize") { return str_copy(dest, "intptr_t", max_len); }
    if str_eq(cq_type, "bool") { return str_copy(dest, "_Bool", max_len); }
    if str_eq(cq_type, "void") { return str_copy(dest, "void", max_len); }
    return str_copy(dest, cq_type, max_len);
}

@system
pub fn emit_c_from_tokens(tokens: *const Token, tok_count: usize, out_buf: *mut u8, max_len: usize) -> usize {
    if tokens == null || out_buf == null || max_len == 0 {
        return 0;
    }
    str_copy(out_buf, "/* Gerado pelo VortexC-lite em Cq 0.1 */\n#include <stdint.h>\n#include <stddef.h>\n#include <stdbool.h>\n\n", max_len);

    let mut i: usize = 0;
    unsafe {
        while i < tok_count {
            let tok: *const Token = &tokens[i];
            let txt: *const u8 = tok.text as *const u8;

            if tok.kind == TokenKind::Eof {
                break;
            }

            // Ignora declarações de 'module' e 'import' (resolvidas estaticamente)
            if str_eq(txt, "module") || str_eq(txt, "import") {
                while i < tok_count && !str_eq(tokens[i].text as *const u8, ";") {
                    i = i + 1;
                }
                if i < tok_count {
                    i = i + 1;
                }
                continue;
            }

            // Ignora 'pub', 'unsafe', '@system', '@export', '@inline'
            if str_eq(txt, "pub") || str_eq(txt, "unsafe") || str_eq(txt, "@system") || str_eq(txt, "@export") || str_eq(txt, "@inline") {
                i = i + 1;
                continue;
            }

            // @packed struct -> typedef struct __attribute__((packed))
            if str_eq(txt, "@packed") {
                str_concat(out_buf, "__attribute__((packed)) ", max_len);
                i = i + 1;
                continue;
            }

            // struct -> typedef struct
            if str_eq(txt, "struct") {
                str_concat(out_buf, "typedef struct ", max_len);
                i = i + 1;
                continue;
            }

            // enum -> typedef enum
            if str_eq(txt, "enum") {
                str_concat(out_buf, "typedef enum ", max_len);
                i = i + 1;
                continue;
            }

            // null -> NULL
            if str_eq(txt, "null") {
                str_concat(out_buf, "NULL", max_len);
                str_concat(out_buf, " ", max_len);
                i = i + 1;
                continue;
            }

            // let -> declaração de variável
            if str_eq(txt, "let") {
                i = i + 1;
                if i < tok_count && str_eq(tokens[i].text as *const u8, "mut") {
                    i = i + 1;
                }
                let var_name: *const u8 = tokens[i].text as *const u8;
                i = i + 1;
                if i < tok_count && str_eq(tokens[i].text as *const u8, ":") {
                    i = i + 1;
                    let type_name: *const u8 = tokens[i].text as *const u8;
                    let mut c_type: [u8; 32] = 0;
                    type_to_c(type_name, c_type as *mut u8, 32);
                    str_concat(out_buf, c_type as *const u8, max_len);
                    str_concat(out_buf, " ", max_len);
                    str_concat(out_buf, var_name, max_len);
                    i = i + 1;
                } else {
                    str_concat(out_buf, "int64_t ", max_len);
                    str_concat(out_buf, var_name, max_len);
                }
                str_concat(out_buf, " ", max_len);
                continue;
            }

            // Conversão de tipos primitivos isolados
            let mut c_type: [u8; 32] = 0;
            if type_to_c(txt, c_type as *mut u8, 32) > 0 && !str_eq(txt, c_type as *const u8) {
                str_concat(out_buf, c_type as *const u8, max_len);
            } else {
                str_concat(out_buf, txt, max_len);
            }

            str_concat(out_buf, " ", max_len);
            i = i + 1;
        }
    }
    return str_len(out_buf as *const u8);
}
