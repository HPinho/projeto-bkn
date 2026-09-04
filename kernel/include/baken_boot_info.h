#ifndef BAKEN_BOOT_INFO_H
#define BAKEN_BOOT_INFO_H

/* Contrato de handoff entre bootstrap UEFI e kernel Baken.
 *
 * V2 é deliberadamente um ENVELOPE DE TRANSIÇÃO: os primeiros 80 bytes
 * preservam o ABI usado pelo runtime atual para não deslocar ponteiros em uma
 * migração incremental. Os metadados bare-metal são anexados após esse bloco.
 *
 * Os ponteiros UEFI abaixo são LEGADO e não fazem parte do ABI pós-cutover.
 * Nenhum código novo pode depender deles. Depois de input/storage/timers
 * nativos, o próximo ABI removerá esses campos e ExitBootServices ocorrerá
 * antes da entrada normal do kernel.
 */

#include <stdint.h>
#include <stddef.h>

#define BAKEN_BOOT_INFO_VERSION 2U
#define BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE       (1ULL << 0)
#define BAKEN_BOOT_INFO_FLAG_MEMORY_MAP_VALID          (1ULL << 1)
#define BAKEN_BOOT_INFO_FLAG_ACPI_RSDP_VALID           (1ULL << 2)
#define BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID    (1ULL << 3)
#define BAKEN_BOOT_INFO_FLAG_LOADED_IMAGE_VALID        (1ULL << 4)
#define BAKEN_BOOT_INFO_FLAG_TRANSITION_STACK_VALID    (1ULL << 5)

typedef struct {
    /* ABI legado congelado (offsets 0..79). */
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
    void *install_target_block_io_protocol;

    /* Extensão v2: dados necessários ao futuro handoff pós-Boot Services. */
    uint32_t version;
    uint32_t struct_size;
    uint64_t flags;
    uint64_t memory_descriptor_size;
    uint32_t memory_descriptor_version;
    uint32_t pixel_format;
    void *acpi_rsdp;

    /* Reserva bootstrap page-aligned para page tables próprias. */
    uint64_t page_table_arena_physical_base;
    void *page_table_arena_virtual_base;
    uint64_t page_table_arena_page_count;

    /* Endereço real da imagem PE/COFF entregue pelo Loaded Image Protocol.
     * Mantemos PA e alias temporário separados mesmo enquanto seus valores
     * coincidem no address space de bootstrap. */
    uint64_t loaded_image_physical_base;
    void *loaded_image_virtual_base;
    uint64_t loaded_image_size;

    /* Stack pertencente ao Baken e reservada antes do Memory Map final. */
    uint64_t transition_stack_physical_base;
    void *transition_stack_virtual_base;
    uint64_t transition_stack_page_count;
} BakenBootInfo;

_Static_assert(offsetof(BakenBootInfo, framebuffer_base) == 0, "handoff framebuffer deslocado");
_Static_assert(offsetof(BakenBootInfo, framebuffer_size) == 8, "handoff tamanho deslocado");
_Static_assert(offsetof(BakenBootInfo, screen_width) == 16, "handoff largura deslocada");
_Static_assert(offsetof(BakenBootInfo, memory_map_base) == 32, "handoff mapa deslocado");
_Static_assert(offsetof(BakenBootInfo, system_table) == 48, "handoff tabela UEFI deslocada");
_Static_assert(offsetof(BakenBootInfo, block_io_protocol) == 64, "handoff Block I/O deslocado");
_Static_assert(offsetof(BakenBootInfo, install_target_block_io_protocol) == 72, "handoff alvo deslocado");
_Static_assert(offsetof(BakenBootInfo, version) == 80, "extensão v2 deslocada");
_Static_assert(offsetof(BakenBootInfo, memory_descriptor_size) == 96, "descritor de mapa deslocado");
_Static_assert(offsetof(BakenBootInfo, acpi_rsdp) == 112, "ACPI RSDP deslocada");
_Static_assert(offsetof(BakenBootInfo, page_table_arena_physical_base) == 120, "PA da arena deslocado");
_Static_assert(offsetof(BakenBootInfo, page_table_arena_virtual_base) == 128, "VA da arena deslocado");
_Static_assert(offsetof(BakenBootInfo, page_table_arena_page_count) == 136, "contagem da arena deslocada");
_Static_assert(offsetof(BakenBootInfo, loaded_image_physical_base) == 144, "PA da imagem deslocado");
_Static_assert(offsetof(BakenBootInfo, loaded_image_virtual_base) == 152, "VA da imagem deslocado");
_Static_assert(offsetof(BakenBootInfo, loaded_image_size) == 160, "tamanho da imagem deslocado");
_Static_assert(offsetof(BakenBootInfo, transition_stack_physical_base) == 168, "PA da stack deslocado");
_Static_assert(offsetof(BakenBootInfo, transition_stack_virtual_base) == 176, "VA da stack deslocado");
_Static_assert(offsetof(BakenBootInfo, transition_stack_page_count) == 184, "contagem da stack deslocada");
_Static_assert(sizeof(BakenBootInfo) == 192, "handoff BakenBootInfo v2 x86_64 inválido");

#endif
