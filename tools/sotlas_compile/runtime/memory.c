/* Freestanding compiler ABI support, not a hosted libc dependency.
 * Volatile byte accesses prevent optimizing these loops into self-calls.
 * Byte-only implementation is safe before SIMD context management exists.
 */
#include <stddef.h>
#include <stdint.h>

void *memset(void *destination, int value, size_t count) {
    volatile unsigned char *out = (volatile unsigned char *)destination;
    for (size_t i = 0; i < count; ++i) out[i] = (unsigned char)value;
    return destination;
}

void *memcpy(void *destination, const void *source, size_t count) {
    volatile unsigned char *out = (volatile unsigned char *)destination;
    const volatile unsigned char *in = (const volatile unsigned char *)source;
    for (size_t i = 0; i < count; ++i) out[i] = in[i];
    return destination;
}

void *memmove(void *destination, const void *source, size_t count) {
    volatile unsigned char *out = (volatile unsigned char *)destination;
    const volatile unsigned char *in = (const volatile unsigned char *)source;
    if ((uintptr_t)destination < (uintptr_t)source) {
        for (size_t i = 0; i < count; ++i) out[i] = in[i];
    } else if (destination != source) {
        while (count != 0) { --count; out[count] = in[count]; }
    }
    return destination;
}

int memcmp(const void *left, const void *right, size_t count) {
    const volatile unsigned char *a = (const volatile unsigned char *)left;
    const volatile unsigned char *b = (const volatile unsigned char *)right;
    for (size_t i = 0; i < count; ++i) {
        unsigned char x = a[i], y = b[i];
        if (x != y) return (int)x - (int)y;
    }
    return 0;
}
