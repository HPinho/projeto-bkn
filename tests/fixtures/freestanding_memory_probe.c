#include <stddef.h>
#include <string.h>

int main(void) {
    unsigned char bytes[80], copy[80];
    for (size_t size = 0; size <= 64; ++size) {
        for (size_t i = 0; i < 80; ++i) { bytes[i] = 0xA5; copy[i] = 0; }
        if (memset(bytes + 1, 0x1FF, size) != bytes + 1) return 1;
        if (bytes[0] != 0xA5 || bytes[size + 1] != 0xA5) return 2;
        for (size_t i = 1; i <= size; ++i) if (bytes[i] != 0xFF) return 3;
        if (memcpy(copy + 3, bytes + 1, size) != copy + 3) return 4;
        if (memcmp(copy + 3, bytes + 1, size) != 0) return 5;
        if (copy[2] != 0 || copy[size + 3] != 0) return 6;
        for (size_t i = 0; i < 80; ++i) bytes[i] = (unsigned char)i;
        if (memmove(bytes + 3, bytes, size) != bytes + 3) return 7;
        for (size_t i = 0; i < size; ++i) if (bytes[i + 3] != i) return 8;
        for (size_t i = 0; i < 80; ++i) bytes[i] = (unsigned char)i;
        if (memmove(bytes, bytes + 3, size) != bytes) return 9;
        for (size_t i = 0; i < size; ++i) if (bytes[i] != i + 3) return 10;
        if (memmove(bytes, bytes, size) != bytes) return 11;
    }
    bytes[0] = 0x80; copy[0] = 0x7F;
    if (memcmp(bytes, copy, 1) <= 0 || memcmp(copy, bytes, 1) >= 0) return 12;
    if (memcmp(bytes, copy, 0) != 0) return 13;
    return 0;
}
