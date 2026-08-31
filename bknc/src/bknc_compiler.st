/*
 * BKNC - prototipo hospedeiro do frontend da linguagem Baken.
 *
 * Este arquivo e C de ferramenta, mantido com extensao .st pela migracao
 * historica. Ele NAO e um modulo Sotlas do kernel e ainda nao e o compilador
 * oficial: reconhece funcoes de forma limitada e emite apenas LLVM IR textual.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include "../include/bknc_ast.sth"

typedef enum {
    TOK_EOF,
    TOK_FN,
    TOK_LET,
    TOK_MUT,
    TOK_STRUCT,
    TOK_PUB,
    TOK_RETURN,
    TOK_IF,
    TOK_ELSE,
    TOK_WHILE,
    TOK_FOR,
    TOK_MODULE,
    TOK_IMPORT,
    TOK_SYSTEM_ATTR,
    TOK_IDENTIFIER,
    TOK_NUMBER,
    TOK_STRING,
    TOK_LBRACE, TOK_RBRACE,
    TOK_LPAREN, TOK_RPAREN,
    TOK_LBRACKET, TOK_RBRACKET,
    TOK_SEMICOLON,
    TOK_COLON,
    TOK_COMMA,
    TOK_DOT,
    TOK_ARROW,
    TOK_EQUALS,
    TOK_PLUS, TOK_MINUS, TOK_STAR, TOK_SLASH
} BknTokenKind;

typedef struct {
    BknTokenKind kind;
    char text[64];
    int line;
} BknToken;

typedef struct {
    const char* source;
    size_t cursor;
    int line;
    BknToken current_tok;
} BknParser;

// ========================================================================
// LEXER
// ========================================================================

BknToken bknc_next_token(BknParser* parser) {
    BknToken tok;
    tok.kind = TOK_EOF;
    tok.text[0] = '\0';
    tok.line = parser->line;

    while (parser->source[parser->cursor] != '\0') {
        char c = parser->source[parser->cursor];

        if (c == ' ' || c == '\t' || c == '\r') {
            parser->cursor++;
            continue;
        }
        if (c == '\n') {
            parser->line++;
            parser->cursor++;
            continue;
        }

        // Comentarios de linha //
        if (c == '/' && parser->source[parser->cursor + 1] == '/') {
            while (parser->source[parser->cursor] != '\0' && parser->source[parser->cursor] != '\n') {
                parser->cursor++;
            }
            continue;
        }

        // Numeros
        if (c >= '0' && c <= '9') {
            size_t start = parser->cursor;
            while ((parser->source[parser->cursor] >= '0' && parser->source[parser->cursor] <= '9') ||
                   parser->source[parser->cursor] == '.' || parser->source[parser->cursor] == 'x' ||
                   (parser->source[parser->cursor] >= 'a' && parser->source[parser->cursor] <= 'f') ||
                   (parser->source[parser->cursor] >= 'A' && parser->source[parser->cursor] <= 'F')) {
                parser->cursor++;
            }
            size_t len = parser->cursor - start;
            if (len >= sizeof(tok.text)) len = sizeof(tok.text) - 1;
            strncpy(tok.text, &parser->source[start], len);
            tok.text[len] = '\0';
            tok.kind = TOK_NUMBER;
            return tok;
        }

        // Strings
        if (c == '"') {
            parser->cursor++;
            size_t start = parser->cursor;
            while (parser->source[parser->cursor] != '\0' && parser->source[parser->cursor] != '"') {
                parser->cursor++;
            }
            size_t len = parser->cursor - start;
            if (len >= sizeof(tok.text)) len = sizeof(tok.text) - 1;
            strncpy(tok.text, &parser->source[start], len);
            tok.text[len] = '\0';
            if (parser->source[parser->cursor] == '"') parser->cursor++;
            tok.kind = TOK_STRING;
            return tok;
        }

        // Identificadores e atributos do subconjunto MVP.
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_' || c == '@') {
            size_t start = parser->cursor;
            while ((parser->source[parser->cursor] >= 'a' && parser->source[parser->cursor] <= 'z') ||
                   (parser->source[parser->cursor] >= 'A' && parser->source[parser->cursor] <= 'Z') ||
                   (parser->source[parser->cursor] >= '0' && parser->source[parser->cursor] <= '9') ||
                   parser->source[parser->cursor] == '_' || parser->source[parser->cursor] == '@') {
                parser->cursor++;
            }
            size_t len = parser->cursor - start;
            if (len >= sizeof(tok.text)) len = sizeof(tok.text) - 1;
            strncpy(tok.text, &parser->source[start], len);
            tok.text[len] = '\0';

            if (strcmp(tok.text, "fn") == 0) tok.kind = TOK_FN;
            else if (strcmp(tok.text, "let") == 0) tok.kind = TOK_LET;
            else if (strcmp(tok.text, "mut") == 0) tok.kind = TOK_MUT;
            else if (strcmp(tok.text, "struct") == 0) tok.kind = TOK_STRUCT;
            else if (strcmp(tok.text, "pub") == 0) tok.kind = TOK_PUB;
            else if (strcmp(tok.text, "return") == 0) tok.kind = TOK_RETURN;
            else if (strcmp(tok.text, "if") == 0) tok.kind = TOK_IF;
            else if (strcmp(tok.text, "else") == 0) tok.kind = TOK_ELSE;
            else if (strcmp(tok.text, "while") == 0) tok.kind = TOK_WHILE;
            else if (strcmp(tok.text, "for") == 0) tok.kind = TOK_FOR;
            else if (strcmp(tok.text, "module") == 0) tok.kind = TOK_MODULE;
            else if (strcmp(tok.text, "import") == 0) tok.kind = TOK_IMPORT;
            else if (strcmp(tok.text, "@system") == 0) tok.kind = TOK_SYSTEM_ATTR;
            else tok.kind = TOK_IDENTIFIER;

            return tok;
        }

        parser->cursor++;
        tok.text[0] = c;
        tok.text[1] = '\0';

        switch (c) {
            case '{': tok.kind = TOK_LBRACE; return tok;
            case '}': tok.kind = TOK_RBRACE; return tok;
            case '(': tok.kind = TOK_LPAREN; return tok;
            case ')': tok.kind = TOK_RPAREN; return tok;
            case '[': tok.kind = TOK_LBRACKET; return tok;
            case ']': tok.kind = TOK_RBRACKET; return tok;
            case ';': tok.kind = TOK_SEMICOLON; return tok;
            case ':': tok.kind = TOK_COLON; return tok;
            case ',': tok.kind = TOK_COMMA; return tok;
            case '.': tok.kind = TOK_DOT; return tok;
            case '=': tok.kind = TOK_EQUALS; return tok;
            case '+': tok.kind = TOK_PLUS; return tok;
            case '*': tok.kind = TOK_STAR; return tok;
            case '/': tok.kind = TOK_SLASH; return tok;
            case '-':
                if (parser->source[parser->cursor] == '>') {
                    parser->cursor++;
                    strcpy(tok.text, "->");
                    tok.kind = TOK_ARROW;
                } else {
                    tok.kind = TOK_MINUS;
                }
                return tok;
        }
    }

    return tok;
}

void bknc_advance(BknParser* parser) {
    parser->current_tok = bknc_next_token(parser);
}

bool bknc_match(BknParser* parser, BknTokenKind kind) {
    if (parser->current_tok.kind == kind) {
        bknc_advance(parser);
        return true;
    }
    return false;
}

// ========================================================================
// PARSER E CONSTRUTOR DE AST
// ========================================================================

BknType bknc_parse_type(BknParser* parser) {
    BknType t;
    memset(&t, 0, sizeof(BknType));
    t.kind = TYPE_VOID;

    if (parser->current_tok.kind == TOK_STAR) {
        bknc_advance(parser);
        if (bknc_match(parser, TOK_MUT)) t.is_mutable = true;
        t.kind = TYPE_POINTER;
        t.inner_type = (BknType*)malloc(sizeof(BknType));
        *t.inner_type = bknc_parse_type(parser);
        return t;
    }

    const char* txt = parser->current_tok.text;
    if (strcmp(txt, "u8") == 0) t.kind = TYPE_U8;
    else if (strcmp(txt, "u16") == 0) t.kind = TYPE_U16;
    else if (strcmp(txt, "u32") == 0) t.kind = TYPE_U32;
    else if (strcmp(txt, "u64") == 0) t.kind = TYPE_U64;
    else if (strcmp(txt, "usize") == 0) t.kind = TYPE_USIZE;
    else if (strcmp(txt, "i8") == 0) t.kind = TYPE_I8;
    else if (strcmp(txt, "i16") == 0) t.kind = TYPE_I16;
    else if (strcmp(txt, "i32") == 0) t.kind = TYPE_I32;
    else if (strcmp(txt, "i64") == 0) t.kind = TYPE_I64;
    else if (strcmp(txt, "isize") == 0) t.kind = TYPE_ISIZE;
    else if (strcmp(txt, "f32") == 0) t.kind = TYPE_F32;
    else if (strcmp(txt, "f64") == 0) t.kind = TYPE_F64;
    else if (strcmp(txt, "bool") == 0) t.kind = TYPE_BOOL;
    else {
        t.kind = TYPE_CUSTOM;
        t.custom_name = strdup(txt);
    }

    bknc_advance(parser);
    return t;
}

BknFunction* bknc_parse_function(BknParser* parser, bool is_system, bool is_pub) {
    BknFunction* fn = (BknFunction*)calloc(1, sizeof(BknFunction));
    fn->is_system_mode = is_system;
    fn->is_public = is_pub;

    if (parser->current_tok.kind == TOK_IDENTIFIER) {
        fn->name = strdup(parser->current_tok.text);
        bknc_advance(parser);
    }

    bknc_match(parser, TOK_LPAREN);
    // Parse params...
    while (parser->current_tok.kind != TOK_RPAREN && parser->current_tok.kind != TOK_EOF) {
        bknc_advance(parser);
    }
    bknc_match(parser, TOK_RPAREN);

    if (bknc_match(parser, TOK_ARROW)) {
        fn->return_type = bknc_parse_type(parser);
    } else {
        fn->return_type.kind = TYPE_VOID;
    }

    if (bknc_match(parser, TOK_LBRACE)) {
        int depth = 1;
        while (depth > 0 && parser->current_tok.kind != TOK_EOF) {
            if (parser->current_tok.kind == TOK_LBRACE) depth++;
            else if (parser->current_tok.kind == TOK_RBRACE) depth--;
            bknc_advance(parser);
        }
    }

    return fn;
}

// ========================================================================
// GERADOR DE LLVM IR TEXTUAL (.ll)
// ========================================================================

typedef enum {
    TARGET_X86_64,
    TARGET_AARCH64,
    TARGET_RISCV64
} BknTargetArch;

static BknTargetArch g_target_arch = TARGET_X86_64;

void bknc_emit_llvm_ir(BknModule* mod, FILE* out) {
    fprintf(out, "; ModuleID = '%s'\n", mod->name ? mod->name : "bkn_module");
    fprintf(out, "source_filename = \"%s\"\n", mod->name ? mod->name : "bkn_module");
    
    if (g_target_arch == TARGET_AARCH64) {
        fprintf(out, "target datalayout = \"e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128\"\n");
        fprintf(out, "target triple = \"aarch64-unknown-none-elf\"\n\n");
    } else if (g_target_arch == TARGET_RISCV64) {
        fprintf(out, "target datalayout = \"e-m:e-p:64:64-i64:64-i128:128-n32:64-S128\"\n");
        fprintf(out, "target triple = \"riscv64-unknown-none-elf\"\n\n");
    } else {
        fprintf(out, "target datalayout = \"e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128\"\n");
        fprintf(out, "target triple = \"x86_64-pc-none-elf\"\n\n");
    }

    BknFunction* fn = mod->functions;
    while (fn) {
        const char* ret_type_str = "void";
        if (fn->return_type.kind == TYPE_U32 || fn->return_type.kind == TYPE_I32) ret_type_str = "i32";
        else if (fn->return_type.kind == TYPE_U64 || fn->return_type.kind == TYPE_I64 || fn->return_type.kind == TYPE_USIZE) ret_type_str = "i64";
        else if (fn->return_type.kind == TYPE_BOOL) ret_type_str = "i1";

        fprintf(out, "define %s @%s() {\n", ret_type_str, fn->name);
        fprintf(out, "entry:\n");
        if (fn->return_type.kind == TYPE_VOID) {
            fprintf(out, "  ret void\n");
        } else {
            fprintf(out, "  ret %s 0\n", ret_type_str);
        }
        fprintf(out, "}\n\n");
        fn = fn->next;
    }
}

// ========================================================================
// MAIN DRIVER DO COMPILADOR
// ========================================================================

int main(int argc, char** argv) {
    printf("BKNC experimental: analisador parcial e emissor LLVM textual\n\n");

    if (argc < 2) {
        printf("Uso: bknc <arquivo.st> [--emit-llvm]\n");
        return 2;
    }
    if (argc > 3 || (argc == 3 && strcmp(argv[2], "--emit-llvm") != 0)) {
        printf("[ERRO] Este prototipo so aceita --emit-llvm; nao gera executaveis, assinaturas ou imagens EFI.\n");
        return 2;
    }

    const char* filepath = argv[1];
    FILE* f = fopen(filepath, "rb");
    if (!f) {
        printf("[ERRO] Nao foi possivel abrir o arquivo: %s\n", filepath);
        return 1;
    }

    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        printf("[ERRO] Nao foi possivel medir o arquivo: %s\n", filepath);
        return 1;
    }
    long size = ftell(f);
    if (size < 0 || fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        printf("[ERRO] Nao foi possivel ler o arquivo: %s\n", filepath);
        return 1;
    }

    char* buffer = (char*)malloc(size + 1);
    if (!buffer) {
        fclose(f);
        printf("[ERRO] Memoria insuficiente para ler: %s\n", filepath);
        return 1;
    }
    if (fread(buffer, 1, (size_t)size, f) != (size_t)size) {
        fclose(f);
        free(buffer);
        printf("[ERRO] Leitura incompleta: %s\n", filepath);
        return 1;
    }
    buffer[size] = '\0';
    fclose(f);

    printf("[1/2] Analisando declaracoes de funcao...\n");
    BknParser parser;
    parser.source = buffer;
    parser.cursor = 0;
    parser.line = 1;
    bknc_advance(&parser);

    BknModule mod;
    memset(&mod, 0, sizeof(BknModule));
    mod.name = strdup(filepath);

    bool is_system = false;
    bool is_pub = false;

    while (parser.current_tok.kind != TOK_EOF) {
        if (parser.current_tok.kind == TOK_SYSTEM_ATTR) {
            is_system = true;
            bknc_advance(&parser);
        } else if (parser.current_tok.kind == TOK_PUB) {
            is_pub = true;
            bknc_advance(&parser);
        } else if (parser.current_tok.kind == TOK_FN) {
            bknc_advance(&parser);
            BknFunction* fn = bknc_parse_function(&parser, is_system, is_pub);
            fn->next = mod.functions;
            mod.functions = fn;
            is_system = false; is_pub = false;
        } else {
            bknc_advance(&parser);
        }
    }

    // Conta funcoes
    int fn_count = 0;
    BknFunction* cur = mod.functions;
    while (cur) { fn_count++; cur = cur->next; }
    printf("  -> %d funcoes detectadas.\n", fn_count);

    printf("[2/2] Gerando LLVM IR textual preliminar (.ll)...\n");
    char ll_path[256];
    snprintf(ll_path, sizeof(ll_path), "%s.ll", filepath);
    FILE* ll_out = fopen(ll_path, "w");
    if (ll_out) {
        bknc_emit_llvm_ir(&mod, ll_out);
        fclose(ll_out);
        printf("  -> IR preliminar salvo em: %s\n", ll_path);
    } else {
        printf("[ERRO] Nao foi possivel criar: %s\n", ll_path);
        free(buffer);
        return 1;
    }

    printf("Aviso: nao ha verificacao de tipos, linker, geracao de objeto ou assinatura nesta versao.\n");

    free(buffer);
    return 0;
}
