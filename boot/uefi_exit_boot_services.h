#ifndef BAKEN_UEFI_EXIT_BOOT_SERVICES_H
#define BAKEN_UEFI_EXIT_BOOT_SERVICES_H

/*
 * Baken OS - algoritmo de handoff final UEFI.
 *
 * Este header pertence exclusivamente ao bootstrap UEFI. Ele NÃO é incluído
 * pelo kernel Sotlas e, nesta etapa, ainda não é chamado por efi_main.
 *
 * Invariantes:
 *  1. o buffer do memory map é alocado enquanto Boot Services ainda vive;
 *  2. GetMemoryMap() é a última operação que pode alterar o map key antes da
 *     tentativa de ExitBootServices();
 *  3. EFI_INVALID_PARAMETER exige adquirir um novo map key e tentar de novo;
 *  4. EFI_BUFFER_TOO_SMALL permite crescer o buffer e reiniciar a sequência;
 *  5. após EFI_SUCCESS nenhum Boot Service pode ser chamado novamente.
 */

#ifndef EFI_SUCCESS
#error "uefi_exit_boot_services.h deve ser incluído após as definições UEFI do bootloader"
#endif

#ifndef BAKEN_UEFI_EXIT_MAX_ATTEMPTS
#define BAKEN_UEFI_EXIT_MAX_ATTEMPTS 8U
#endif

typedef EFI_STATUS (*BAKEN_EFI_EXIT_BOOT_SERVICES)(EFI_HANDLE, UINTN);

typedef struct {
    void *memory_map;
    UINTN memory_map_size;
    UINTN memory_map_capacity;
    UINTN map_key;
    UINTN descriptor_size;
    uint32_t descriptor_version;
} BAKEN_FINAL_MEMORY_MAP;

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

/*
 * Adquire o mapa dentro de um buffer já reservado. Esta função não aloca e
 * não libera memória, porque qualquer alocação depois do GetMemoryMap final
 * invalidaria o map key que acabou de ser obtido.
 */
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
 * Prepara e executa o corte. O caller só deve usar esta função quando TODAS
 * as dependências de Boot Services do kernel já tiverem sido removidas.
 *
 * Ao retornar EFI_SUCCESS, o firmware Boot Services acabou. O caller deve
 * atualizar BakenBootInfo com `state` antes da tentativa final ou garantir que
 * o kernel consuma este mesmo buffer depois do corte sem qualquer Boot Service.
 */
static EFI_STATUS baken_exit_boot_services_final(EFI_HANDLE image_handle,
                                                  EFI_BOOT_SERVICES *bs,
                                                  BAKEN_FINAL_MEMORY_MAP *state) {
    if (!bs || !state || !bs->ExitBootServices) return EFI_INVALID_PARAMETER;

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

        /* CRÍTICO: nenhuma chamada de Boot Service pode existir entre este
         * GetMemoryMap bem-sucedido e ExitBootServices. */
        status = exit_boot_services(image_handle, state->map_key);
        if (status == EFI_SUCCESS) {
            return EFI_SUCCESS;
        }
        if (status != EFI_INVALID_PARAMETER) {
            return status;
        }

        /* Map key mudou. Não aloca, não libera, não imprime: apenas refaz
         * GetMemoryMap no mesmo buffer e tenta novamente. */
    }

    return EFI_ABORTED;
}

#endif /* BAKEN_UEFI_EXIT_BOOT_SERVICES_H */
