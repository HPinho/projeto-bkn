#ifndef BAKEN_UEFI_EXIT_BOOT_SERVICES_H
#define BAKEN_UEFI_EXIT_BOOT_SERVICES_H

/*
 * Baken OS - algoritmo de handoff final UEFI.
 *
 * Este header pertence exclusivamente ao bootstrap UEFI. O Memory Map final
 * alimenta uma callback pura de preparação imediatamente antes de cada
 * tentativa de ExitBootServices(). A callback pode escrever RAM/page tables,
 * mas não pode chamar firmware nem realizar qualquer alocação UEFI.
 *
 * Invariantes:
 *  1. o buffer do memory map é alocado enquanto Boot Services ainda vive;
 *  2. GetMemoryMap() é a última operação de firmware antes da callback pura;
 *  3. a callback reconstrói o cutover para o MapKey que será usado;
 *  4. EFI_INVALID_PARAMETER exige novo mapa, novo preparo e nova tentativa;
 *  5. EFI_BUFFER_TOO_SMALL permite crescer o buffer e reiniciar a sequência;
 *  6. após EFI_SUCCESS nenhum Boot Service pode ser chamado novamente.
 */

#ifndef EFI_SUCCESS
#error "uefi_exit_boot_services.h deve ser incluído após as definições UEFI do bootloader"
#endif

#ifndef BAKEN_UEFI_EXIT_MAX_ATTEMPTS
#define BAKEN_UEFI_EXIT_MAX_ATTEMPTS 8U
#endif

#ifndef BAKEN_UEFI_PAGE_SIZE
#define BAKEN_UEFI_PAGE_SIZE 4096ULL
#endif

typedef EFI_STATUS (*BAKEN_EFI_EXIT_BOOT_SERVICES)(EFI_HANDLE, UINTN);

typedef struct BAKEN_FINAL_MEMORY_MAP {
    void *memory_map;
    UINTN memory_map_size;
    UINTN memory_map_capacity;
    UINTN map_key;
    UINTN descriptor_size;
    uint32_t descriptor_version;
} BAKEN_FINAL_MEMORY_MAP;

typedef EFI_STATUS (*BAKEN_PRE_EXIT_CALLBACK)(
    const BAKEN_FINAL_MEMORY_MAP *state,
    void *context
);

/* Layout mínimo comum dos EFI_MEMORY_DESCRIPTOR x86-64. descriptor_size pode
 * ser maior; por isso a iteração sempre usa o stride entregue pelo firmware. */
typedef struct {
    uint32_t type;
    uint32_t pad;
    uint64_t physical_start;
    uint64_t virtual_start;
    uint64_t number_of_pages;
    uint64_t attribute;
} BAKEN_EFI_MEMORY_DESCRIPTOR_PREFIX;

/*
 * Traduz um endereço observado antes do cutover para o endereço físico que o
 * Memory Map final descreve. Cobre tanto firmware identity-mapped quanto um
 * VirtualStart explícito. Zero significa que o endereço não foi localizado.
 */
static uint64_t baken_final_map_physical_address(
    const BAKEN_FINAL_MEMORY_MAP *state,
    uint64_t address
) {
    if (!state || !state->memory_map || state->descriptor_size < 40 ||
        state->memory_map_size < state->descriptor_size || address == 0) {
        return 0;
    }

    const uint8_t *base = (const uint8_t*)state->memory_map;
    for (UINTN offset = 0;
         offset + state->descriptor_size <= state->memory_map_size;
         offset += state->descriptor_size) {
        const BAKEN_EFI_MEMORY_DESCRIPTOR_PREFIX *descriptor =
            (const BAKEN_EFI_MEMORY_DESCRIPTOR_PREFIX*)(base + offset);
        if (descriptor->number_of_pages == 0) continue;

        uint64_t bytes = descriptor->number_of_pages * BAKEN_UEFI_PAGE_SIZE;
        if (bytes / BAKEN_UEFI_PAGE_SIZE != descriptor->number_of_pages) continue;
        uint64_t physical_end = descriptor->physical_start + bytes;
        if (physical_end <= descriptor->physical_start) continue;

        if (address >= descriptor->physical_start && address < physical_end) {
            return address;
        }

        if (descriptor->virtual_start != 0) {
            uint64_t virtual_end = descriptor->virtual_start + bytes;
            if (virtual_end > descriptor->virtual_start &&
                address >= descriptor->virtual_start && address < virtual_end) {
                return descriptor->physical_start +
                    (address - descriptor->virtual_start);
            }
        }
    }
    return 0;
}

static EFI_STATUS baken_prepare_final_memory_map(EFI_BOOT_SERVICES *bs,
                                                  BAKEN_FINAL_MEMORY_MAP *state) {
    if (!bs || !state || !bs->GetMemoryMap || !bs->AllocatePool) {
        return EFI_INVALID_PARAMETER;
    }

    EFI_GET_MEMORY_MAP get_map = (EFI_GET_MEMORY_MAP)bs->GetMemoryMap;
    EFI_ALLOCATE_POOL allocate_pool = (EFI_ALLOCATE_POOL)bs->AllocatePool;
    EFI_FREE_POOL free_pool = (EFI_FREE_POOL)bs->FreePool;

    UINTN required = 0;
    UINTN key = 0;
    UINTN descriptor_size = 0;
    uint32_t descriptor_version = 0;
    EFI_STATUS status = get_map(&required, NULL, &key, &descriptor_size,
                                &descriptor_version);
    if (status != EFI_BUFFER_TOO_SMALL || descriptor_size == 0) return status;

    UINTN capacity = required + descriptor_size * 32U + 8192U;
    void *buffer = NULL;
    status = allocate_pool(EFI_LOADER_DATA, capacity, &buffer);
    if (status != EFI_SUCCESS || !buffer) {
        return status == EFI_SUCCESS ? EFI_OUT_OF_RESOURCES : status;
    }

    if (state->memory_map && free_pool) {
        (void)free_pool(state->memory_map);
    }

    state->memory_map = buffer;
    state->memory_map_capacity = capacity;
    state->memory_map_size = 0;
    state->map_key = 0;
    state->descriptor_size = descriptor_size;
    state->descriptor_version = descriptor_version;
    return EFI_SUCCESS;
}

/* Adquire o mapa em buffer já reservado. Não aloca nem libera memória. */
static EFI_STATUS baken_refresh_final_memory_map(EFI_BOOT_SERVICES *bs,
                                                  BAKEN_FINAL_MEMORY_MAP *state) {
    if (!bs || !state || !state->memory_map || state->memory_map_capacity == 0 ||
        !bs->GetMemoryMap) {
        return EFI_INVALID_PARAMETER;
    }

    EFI_GET_MEMORY_MAP get_map = (EFI_GET_MEMORY_MAP)bs->GetMemoryMap;
    UINTN size = state->memory_map_capacity;
    UINTN key = 0;
    UINTN descriptor_size = state->descriptor_size;
    uint32_t descriptor_version = state->descriptor_version;

    EFI_STATUS status = get_map(&size, state->memory_map, &key,
                                &descriptor_size, &descriptor_version);
    if (status != EFI_SUCCESS) {
        state->memory_map_size = size;
        return status;
    }

    state->memory_map_size = size;
    state->map_key = key;
    state->descriptor_size = descriptor_size;
    state->descriptor_version = descriptor_version;
    return EFI_SUCCESS;
}

/*
 * Executa o corte real. Entre o GetMemoryMap final e ExitBootServices existe
 * somente `prepare_cutover`: uma callback que não recebe EFI_BOOT_SERVICES e
 * deve ser estritamente livre de chamadas ao firmware.
 */
static EFI_STATUS baken_exit_boot_services_final(
    EFI_HANDLE image_handle,
    EFI_BOOT_SERVICES *bs,
    BAKEN_FINAL_MEMORY_MAP *state,
    BAKEN_PRE_EXIT_CALLBACK prepare_cutover,
    void *prepare_context
) {
    if (!bs || !state || !bs->ExitBootServices || !prepare_cutover) {
        return EFI_INVALID_PARAMETER;
    }

    BAKEN_EFI_EXIT_BOOT_SERVICES exit_boot_services =
        (BAKEN_EFI_EXIT_BOOT_SERVICES)bs->ExitBootServices;

    EFI_STATUS status = baken_prepare_final_memory_map(bs, state);
    if (status != EFI_SUCCESS) return status;

    for (UINTN attempt = 0; attempt < BAKEN_UEFI_EXIT_MAX_ATTEMPTS; ++attempt) {
        status = baken_refresh_final_memory_map(bs, state);

        if (status == EFI_BUFFER_TOO_SMALL) {
            /* O firmware cresceu o mapa além da folga. Crescemos o buffer
             * enquanto Boot Services ainda existe e reiniciamos a sequência. */
            status = baken_prepare_final_memory_map(bs, state);
            if (status != EFI_SUCCESS) return status;
            continue;
        }
        if (status != EFI_SUCCESS) return status;

        /* Nenhum Boot Service daqui até ExitBootServices. A callback recebe
         * apenas RAM + o snapshot final, e deve reconstruir PML4/contexto. */
        status = prepare_cutover(state, prepare_context);
        if (status != EFI_SUCCESS) return status;

        status = exit_boot_services(image_handle, state->map_key);
        if (status == EFI_SUCCESS) {
            return EFI_SUCCESS;
        }
        if (status != EFI_INVALID_PARAMETER) {
            return status;
        }

        /* MapKey mudou: refaz GetMemoryMap e a callback, sem cleanup/log. */
    }

    return EFI_ABORTED;
}

#endif /* BAKEN_UEFI_EXIT_BOOT_SERVICES_H */
