#ifndef BAKEN_BOOT_INFO_H
#define BAKEN_BOOT_INFO_H

/* Contrato versionado entre o bootstrap UEFI e o kernel Baken.
 *
 * O prefixo v2 contém somente dados que continuam válidos depois de
 * ExitBootServices(). Os quatro ponteiros finais são uma extensão de
 * compatibilidade TEMPORÁRIA para o runtime UEFI atual e serão removidos no
 * cutover bare-metal. Nenhum código novo pode depender deles.
 */

#include <stdint.h>
#include <stddef.h>

#define BAKEN_BOOT_INFO_VERSION 2U
#define BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE (1ULL << 0)

typedef struct {
    /* Cabeçalho versionado. */
    uint32_t version;
    uint32_t struct_size;
    uint64_t flags;

    /* Framebuffer GOP: dados físicos/passivos, válidos pós-Boot Services. */
    uint32_t *framebuffer_base;
    uint64_t framebuffer_size;
    uint32_t screen_width;
    uint32_t screen_height;
    uint32_t pixels_per_scanline;
    uint32_t pixel_format;

    /* Snapshot final do mapa UEFI. O buffer deve permanecer reservado para o
     * kernel e ser interpretado usando descriptor_size/version. */
    void *memory_map_base;
    uint64_t memory_map_size;
    uint64_t memory_descriptor_size;
    uint32_t memory_descriptor_version;
    uint32_t reserved0;

    /* Endereço físico da RSDP ACPI 2.0 (ou 1.0 como fallback). */
    void *acpi_rsdp;

    /* ------------------------------------------------------------------
     * LEGACY TRANSITION EXTENSION
     * ------------------------------------------------------------------
     * Estes campos não fazem parte do contrato bare-metal final. Existem
     * apenas para manter a sessão atual bootável até i8042/USB/storage nativos
     * substituírem as pontes de firmware. O kernel pós-ExitBootServices nunca
     * poderá dereferenciá-los.
     */
    void *legacy_system_table;
    void *legacy_pointer_protocol;
    void *legacy_block_io_protocol;
    void *legacy_install_target_block_io_protocol;
} BakenBootInfo;

_Static_assert(offsetof(BakenBootInfo, version) == 0, "handoff version deslocado");
_Static_assert(offsetof(BakenBootInfo, flags) == 8, "handoff flags deslocado");
_Static_assert(offsetof(BakenBootInfo, framebuffer_base) == 16, "handoff framebuffer deslocado");
_Static_assert(offsetof(BakenBootInfo, framebuffer_size) == 24, "handoff tamanho deslocado");
_Static_assert(offsetof(BakenBootInfo, screen_width) == 32, "handoff largura deslocada");
_Static_assert(offsetof(BakenBootInfo, memory_map_base) == 48, "handoff mapa deslocado");
_Static_assert(offsetof(BakenBootInfo, memory_descriptor_size) == 64, "handoff descritor deslocado");
_Static_assert(offsetof(BakenBootInfo, acpi_rsdp) == 80, "handoff ACPI deslocado");
_Static_assert(offsetof(BakenBootInfo, legacy_system_table) == 88, "extensão legacy deslocada");
_Static_assert(sizeof(BakenBootInfo) == 120, "handoff BakenBootInfo v2 x86_64 inválido");

#endif
