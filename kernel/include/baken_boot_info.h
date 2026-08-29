#ifndef BAKEN_BOOT_INFO_H
#define BAKEN_BOOT_INFO_H

/* Contrato de handoff entre o bootloader UEFI e o kernel gráfico.
 * Este cabeçalho é compilado pelos dois lados; não replique esta estrutura em
 * arquivos locais, pois qualquer divergência desloca ponteiros críticos. */

#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint32_t *framebuffer_base;
    uint64_t framebuffer_size;
    uint32_t screen_width;
    uint32_t screen_height;
    uint32_t pixels_per_scanline;
    void *memory_map_base;
    uint64_t memory_map_size;
    void *system_table;
    void *pointer_protocol;
    void *block_io_protocol;
    /* Segundo disco bruto gravável, quando o bootloader encontra um alvo
     * distinto da mídia de boot. Nunca é inferido por caminho de host. */
    void *install_target_block_io_protocol;
} BakenBootInfo;

_Static_assert(offsetof(BakenBootInfo, framebuffer_base) == 0, "handoff framebuffer deslocado");
_Static_assert(offsetof(BakenBootInfo, framebuffer_size) == 8, "handoff tamanho deslocado");
_Static_assert(offsetof(BakenBootInfo, screen_width) == 16, "handoff largura deslocada");
_Static_assert(offsetof(BakenBootInfo, memory_map_base) == 32, "handoff mapa deslocado");
_Static_assert(offsetof(BakenBootInfo, system_table) == 48, "handoff tabela UEFI deslocada");
_Static_assert(offsetof(BakenBootInfo, block_io_protocol) == 64, "handoff Block I/O deslocado");
_Static_assert(offsetof(BakenBootInfo, install_target_block_io_protocol) == 72, "handoff alvo de instalacao deslocado");
_Static_assert(sizeof(BakenBootInfo) == 80, "handoff UEFI x86_64 inválido");

#endif
