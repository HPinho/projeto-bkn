/*
 * Baken OS - Camada de Compatibilidade C/C++ Nativa (Baken LibC v1.0)
 * Implementação das funções padrão da Biblioteca C (stdio, stdlib, string, math, unistd).
 */

#ifndef BAKEN_LIBC_H
#define BAKEN_LIBC_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

// =============================================================================
// 1. TIPOS BÁSICOS E DEFINIÇÕES POSIX / C99
// =============================================================================

typedef int64_t  bkn_ssize_t;
typedef uint64_t bkn_size_t;
typedef int32_t  bkn_pid_t;
typedef int32_t  bkn_mode_t;
typedef int64_t  bkn_off_t;

#define BKN_SEEK_SET 0
#define BKN_SEEK_CUR 1
#define BKN_SEEK_END 2

#define BKN_O_RDONLY 0x0000
#define BKN_O_WRONLY 0x0001
#define BKN_O_RDWR   0x0002
#define BKN_O_CREAT  0x0040
#define BKN_O_TRUNC  0x0200

// Estrutura de Arquivo FILE
typedef struct {
    int32_t fd;
    uint32_t flags;
    bkn_off_t position;
    bkn_size_t size;
    char buffer[512];
    uint32_t buf_pos;
} BKN_FILE;

// =============================================================================
// 2. FUNÇÕES DA BIBLIOTECA PADRÃO C (LIBC)
// =============================================================================

// Memória (stdlib.h)
void* bkn_malloc(size_t size);
void* bkn_calloc(size_t num, size_t size);
void* bkn_realloc(void* ptr, size_t size);
void  bkn_free(void* ptr);

// Strings e Memória (string.h)
size_t bkn_strlen(const char* s);
char*  bkn_strcpy(char* dest, const char* src);
char*  bkn_strncpy(char* dest, const char* src, size_t n);
int    bkn_strcmp(const char* s1, const char* s2);
int    bkn_strncmp(const char* s1, const char* s2, size_t n);
char*  bkn_strcat(char* dest, const char* src);
void*  bkn_memcpy(void* dest, const void* src, size_t n);
void*  bkn_memset(void* s, int c, size_t n);
int    bkn_memcmp(const void* s1, const void* s2, size_t n);

// Entrada e Saída (stdio.h)
int bkn_printf(const char* format, ...);
int bkn_snprintf(char* str, size_t size, const char* format, ...);
BKN_FILE* bkn_fopen(const char* filename, const char* mode);
size_t    bkn_fread(void* ptr, size_t size, size_t count, BKN_FILE* stream);
size_t    bkn_fwrite(const void* ptr, size_t size, size_t count, BKN_FILE* stream);
int       bkn_fclose(BKN_FILE* stream);

// Chamadas de Sistema (unistd.h / Syscalls)
int32_t bkn_sys_write(int32_t fd, const void* buf, size_t count);
int32_t bkn_sys_read(int32_t fd, void* buf, size_t count);
int32_t bkn_sys_open(const char* pathname, int32_t flags, bkn_mode_t mode);
int32_t bkn_sys_close(int32_t fd);
bkn_pid_t bkn_sys_getpid(void);

#endif // BAKEN_LIBC_H
