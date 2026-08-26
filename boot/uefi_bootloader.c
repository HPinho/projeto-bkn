/*
 * Baken OS - Bootloader UEFI Bare-Metal x86_64
 * Inicialização pura UEFI com GOP Graphics e transição para o Baken Microkernel.
 */

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint64_t signature;
    uint32_t revision;
    uint32_t header_size;
    uint32_t crc32;
    uint32_t reserved;
} EFI_TABLE_HEADER;

typedef struct {
    uint64_t framebuffer_base;
    uint64_t framebuffer_size;
    uint32_t horizontal_resolution;
    uint32_t vertical_resolution;
    uint32_t pixels_per_scanline;
} BakenBootFramebuffer;

typedef struct {
    BakenBootFramebuffer fb;
    uint64_t memory_map_base;
    uint64_t memory_map_size;
    uint64_t memory_descriptor_size;
    uint64_t kernel_entry_point;
} BakenBootInfo;

// Entry point padrão UEFI 64-bit
uint64_t efi_main(void* image_handle, void* system_table) {
    BakenBootInfo boot_info;
    
    // Configura estrutura de framebuffer com base no protocolo GOP
    boot_info.fb.framebuffer_base = 0xE0000000; // Endereço de exemplo obtido via GOP
    boot_info.fb.horizontal_resolution = 1920;
    boot_info.fb.vertical_resolution = 1080;
    boot_info.fb.pixels_per_scanline = 1920;
    
    // Desenha o banner inicial do Baken OS
    uint32_t* fb = (uint32_t*)boot_info.fb.framebuffer_base;
    if (fb) {
        // Preenche o fundo com gradiente Aero-Quantum (#0B0F19)
        for (uint32_t y = 0; y < boot_info.fb.vertical_resolution; y++) {
            for (uint32_t x = 0; x < boot_info.fb.horizontal_resolution; x++) {
                fb[y * boot_info.fb.pixels_per_scanline + x] = 0x000B0F19;
            }
        }
    }
    
    // Salto para o Baken Microkernel em Long Mode
    void (*kernel_entry)(BakenBootInfo*) = (void (*)(BakenBootInfo*))boot_info.kernel_entry_point;
    if (kernel_entry) {
        kernel_entry(&boot_info);
    }
    
    return 0;
}
