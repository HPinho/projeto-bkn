/*
 * Baken OS - Implementação da Camada de Compatibilidade C/C++ (Baken LibC)
 * Suporte a malloc, printf, manipulação de arquivos no BakenFS, strings e syscalls.
 */

#include "../include/bkn_libc.h"
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

// =============================================================================
// 1. GERENCIADOR DE MEMÓRIA DINÂMICA (STDLIB)
// =============================================================================

void* bkn_malloc(size_t size) {
    if (size == 0) return NULL;
    return malloc(size);
}

void* bkn_calloc(size_t num, size_t size) {
    size_t total = num * size;
    void* ptr = bkn_malloc(total);
    if (ptr) {
        bkn_memset(ptr, 0, total);
    }
    return ptr;
}

void* bkn_realloc(void* ptr, size_t size) {
    return realloc(ptr, size);
}

void bkn_free(void* ptr) {
    if (ptr) {
        free(ptr);
    }
}

// =============================================================================
// 2. STRINGS E MEMÓRIA (STRING.H)
// =============================================================================

size_t bkn_strlen(const char* s) {
    if (!s) return 0;
    size_t len = 0;
    while (s[len] != '\0') len++;
    return len;
}

char* bkn_strcpy(char* dest, const char* src) {
    if (!dest || !src) return dest;
    char* d = dest;
    while ((*d++ = *src++) != '\0');
    return dest;
}

char* bkn_strncpy(char* dest, const char* src, size_t n) {
    if (!dest || !src || n == 0) return dest;
    size_t i;
    for (i = 0; i < n && src[i] != '\0'; i++) {
        dest[i] = src[i];
    }
    for (; i < n; i++) {
        dest[i] = '\0';
    }
    return dest;
}

int bkn_strcmp(const char* s1, const char* s2) {
    if (!s1 && !s2) return 0;
    if (!s1) return -1;
    if (!s2) return 1;
    while (*s1 && (*s1 == *s2)) {
        s1++;
        s2++;
    }
    return *(const unsigned char*)s1 - *(const unsigned char*)s2;
}

int bkn_strncmp(const char* s1, const char* s2, size_t n) {
    if (n == 0) return 0;
    while (n-- && *s1 && *s2 && (*s1 == *s2)) {
        s1++;
        s2++;
    }
    return (n == (size_t)-1) ? 0 : (*(const unsigned char*)s1 - *(const unsigned char*)s2);
}

char* bkn_strcat(char* dest, const char* src) {
    char* d = dest;
    while (*d) d++;
    while ((*d++ = *src++) != '\0');
    return dest;
}

void* bkn_memcpy(void* dest, const void* src, size_t n) {
    char* d = (char*)dest;
    const char* s = (const char*)src;
    while (n--) *d++ = *s++;
    return dest;
}

void* bkn_memset(void* s, int c, size_t n) {
    unsigned char* p = (unsigned char*)s;
    while (n--) *p++ = (unsigned char)c;
    return s;
}

int bkn_memcmp(const void* s1, const void* s2, size_t n) {
    const unsigned char *p1 = (const unsigned char*)s1;
    const unsigned char *p2 = (const unsigned char*)s2;
    while (n--) {
        if (*p1 != *p2) {
            return *p1 - *p2;
        }
        p1++;
        p2++;
    }
    return 0;
}

// =============================================================================
// 3. ENTRADA E SAÍDA FORMATADA (STDIO)
// =============================================================================

int bkn_snprintf(char* str, size_t size, const char* format, ...) {
    va_list args;
    va_start(args, format);
    int res = vsnprintf(str, size, format, args);
    va_end(args);
    return res;
}

int bkn_printf(const char* format, ...) {
    char buffer[1024];
    va_list args;
    va_start(args, format);
    int res = vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);
    bkn_sys_write(1, buffer, (res > 0) ? res : 0);
    return res;
}

// =============================================================================
// 4. CHAMADAS DE SISTEMA DO MICROKERNEL (SYSCALLS POSIX)
// =============================================================================

int32_t bkn_sys_write(int32_t fd, const void* buf, size_t count) {
    if (fd == 1 || fd == 2) {
        // Saída Padrão (Stdout / Stderr)
        return (int32_t)fwrite(buf, 1, count, (fd == 1) ? stdout : stderr);
    }
    return -1;
}

int32_t bkn_sys_read(int32_t fd, void* buf, size_t count) {
    if (fd == 0) {
        return (int32_t)fread(buf, 1, count, stdin);
    }
    return -1;
}

int32_t bkn_sys_open(const char* pathname, int32_t flags, bkn_mode_t mode) {
    (void)flags; (void)mode;
    if (!pathname) return -1;
    return 3; // File descriptor virtual do BakenFS
}

int32_t bkn_sys_close(int32_t fd) {
    if (fd >= 3) return 0;
    return -1;
}

bkn_pid_t bkn_sys_getpid(void) {
    return 100; // PID do processo C
}
