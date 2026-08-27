/*
 * Baken OS - Dynamic Executable Loader (bkn_exec_loader.c)
 * Carregador de Binários PE32+ (Windows x86_64) e ELF64 para Execução no Kernel BKN.
 */

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define PE_MAGIC_MZ 0x5A4D
#define PE_MAGIC_NT 0x00004550

typedef struct {
    uint16_t e_magic;    // "MZ"
    uint8_t  e_cblp[58];
    uint32_t e_lfanew;   // Offset do cabeçalho PE
} DOS_Header;

typedef struct {
    uint16_t Machine;
    uint16_t NumberOfSections;
    uint32_t TimeDateStamp;
    uint32_t PointerToSymbolTable;
    uint32_t NumberOfSymbols;
    uint16_t SizeOfOptionalHeader;
    uint16_t Characteristics;
} File_Header;

typedef struct {
    uint16_t Magic; // 0x020B para PE32+ (64-bit)
    uint8_t  MajorLinkerVersion;
    uint8_t  MinorLinkerVersion;
    uint32_t SizeOfCode;
    uint32_t SizeOfInitializedData;
    uint32_t SizeOfUninitializedData;
    uint32_t AddressOfEntryPoint;
    uint32_t BaseOfCode;
    uint64_t ImageBase;
    uint32_t SectionAlignment;
    uint32_t FileAlignment;
} Optional_Header64;

typedef struct {
    uint8_t  Name[8];
    uint32_t VirtualSize;
    uint32_t VirtualAddress;
    uint32_t SizeOfRawData;
    uint32_t PointerToRawData;
    uint32_t PointerToRelocations;
    uint32_t PointerToLinenumbers;
    uint16_t NumberOfRelocations;
    uint16_t NumberOfLinenumbers;
    uint32_t Characteristics;
} Section_Header;

extern void* bkn_kernel_mmap(void *addr, size_t length, int prot, int flags);

// Mapeia e carrega um binário PE32+ na memória virtual do kernel
void* bkn_load_pe_executable(const uint8_t *raw_data, size_t data_size, uint64_t *entry_point_out) {
    if (!raw_data || data_size < sizeof(DOS_Header)) return NULL;

    const DOS_Header *dos = (const DOS_Header*)raw_data;
    if (dos->e_magic != PE_MAGIC_MZ) return NULL;

    if (dos->e_lfanew + sizeof(File_Header) + 4 > data_size) return NULL;

    const uint32_t *pe_sig = (const uint32_t*)(raw_data + dos->e_lfanew);
    if (*pe_sig != PE_MAGIC_NT) return NULL;

    const File_Header *file_hdr = (const File_Header*)(raw_data + dos->e_lfanew + 4);
    const Optional_Header64 *opt_hdr = (const Optional_Header64*)(raw_data + dos->e_lfanew + 4 + sizeof(File_Header));

    // Aloca espaço contíguo de memória virtual para o executável
    size_t image_size = 64 * 1024 * 1024; // 64 MB reservado
    uint8_t *image_base = (uint8_t*)bkn_kernel_mmap((void*)opt_hdr->ImageBase, image_size, 7, 0);
    if (!image_base) return NULL;

    // Copia os Headers PE
    for (size_t i = 0; i < opt_hdr->SizeOfCode && i < data_size; i++) {
        image_base[i] = raw_data[i];
    }

    // Mapeia cada Seção (.text, .rdata, .data, .pdata)
    const Section_Header *sections = (const Section_Header*)(raw_data + dos->e_lfanew + 4 + sizeof(File_Header) + file_hdr->SizeOfOptionalHeader);

    for (uint16_t i = 0; i < file_hdr->NumberOfSections; i++) {
        const Section_Header *sec = &sections[i];
        if (sec->PointerToRawData + sec->SizeOfRawData <= data_size) {
            uint8_t *dest = image_base + sec->VirtualAddress;
            const uint8_t *src = raw_data + sec->PointerToRawData;
            for (uint32_t b = 0; b < sec->SizeOfRawData; b++) {
                dest[b] = src[b];
            }
        }
    }

    if (entry_point_out) {
        *entry_point_out = (uint64_t)(image_base + opt_hdr->AddressOfEntryPoint);
    }

    return image_base;
}
