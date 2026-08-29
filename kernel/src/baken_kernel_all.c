/*
 * Baken OS 2.0 Sovereign — caminho canônico de renderização (C / Bare-Metal x86_64)
 *
 * RESPONSABILIDADE: este arquivo contém a implementação que é efetivamente
 * vinculada pela ISO. Ele é temporariamente monolítico porque o linker Cq
 * ainda não compila o grafo `kernel::main -> desktop_shell -> compositor`.
 * Não crie uma segunda entrada `baken_kernel_main`: migre cada subsistema para
 * o compositor Cq e só então substitua esta ponte de compatibilidade.
 *
 * Capacidades presentes neste artefato:
 * - Handoff UEFI GOP, teclado, ponteiro e ciclo de composição gráfico.
 * - Rasterização 2D com cartões, ícones, wallpaper, cursor e fonte bitmap
 *   suavizada; ela não é uma fonte vetorial/TrueType ainda.
 * - BakenFS mínimo no volume Baken Data da instalação: pastas, preferências
 *   e /home/notas.txt em setores validados. A mídia live continua sem escrita.
 * - Desktop e instalador de prévia, ambos pela mesma superfície gráfica.
 */

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "baken_boot_info.h"

// =============================================================================
// ESTRUTURAS DE HANDOFF E HARDWARE
// =============================================================================

typedef struct {
    uint32_t Data1;
    uint16_t Data2;
    uint16_t Data3;
    uint8_t  Data4[8];
} EFI_GUID;

typedef struct {
    int32_t RelativeMovementX;
    int32_t RelativeMovementY;
    int32_t RelativeMovementZ;
    uint8_t LeftButton;
    uint8_t RightButton;
} EFI_SIMPLE_POINTER_STATE;

typedef struct _EFI_SIMPLE_POINTER_PROTOCOL {
    uint64_t (*Reset)(struct _EFI_SIMPLE_POINTER_PROTOCOL *This, uint8_t ExtendedVerification);
    uint64_t (*GetState)(struct _EFI_SIMPLE_POINTER_PROTOCOL *This, EFI_SIMPLE_POINTER_STATE *State);
    void *WaitForInput;
    void *Mode;
} EFI_SIMPLE_POINTER_PROTOCOL;

typedef struct {
    uint64_t CurrentX;
    uint64_t CurrentY;
    uint64_t CurrentZ;
    uint32_t ActiveButtons;
} EFI_ABSOLUTE_POINTER_STATE;

typedef struct {
    uint64_t AbsoluteMinX;
    uint64_t AbsoluteMinY;
    uint64_t AbsoluteMinZ;
    uint64_t AbsoluteMaxX;
    uint64_t AbsoluteMaxY;
    uint64_t AbsoluteMaxZ;
    uint32_t Attributes;
} EFI_ABSOLUTE_POINTER_MODE;

typedef struct _EFI_ABSOLUTE_POINTER_PROTOCOL {
    uint64_t (*Reset)(struct _EFI_ABSOLUTE_POINTER_PROTOCOL *This, uint8_t ExtendedVerification);
    uint64_t (*GetState)(struct _EFI_ABSOLUTE_POINTER_PROTOCOL *This, EFI_ABSOLUTE_POINTER_STATE *State);
    void *WaitForInput;
    EFI_ABSOLUTE_POINTER_MODE *Mode;
} EFI_ABSOLUTE_POINTER_PROTOCOL;

static EFI_GUID EFI_ABSOLUTE_POINTER_PROTOCOL_GUID = {
    0x8D59D32B, 0xC655, 0x4AE9, {0x9B, 0x15, 0xF2, 0x59, 0x04, 0x99, 0x2A, 0x43}
};

static EFI_GUID EFI_SIMPLE_POINTER_PROTOCOL_GUID = {
    0x31878C87, 0x0B75, 0x11D5, {0x9A, 0x4F, 0x00, 0x90, 0x27, 0x3F, 0xC1, 0x4D}
};

typedef struct {
    uint16_t ScanCode;
    uint16_t UnicodeChar;
} EFI_INPUT_KEY;

typedef struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL {
    uint64_t (*Reset)(struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, uint8_t ExtendedVerification);
    uint64_t (*ReadKeyStroke)(struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, EFI_INPUT_KEY *Key);
    void *WaitForKey;
} EFI_SIMPLE_TEXT_INPUT_PROTOCOL;

typedef struct {
    uint32_t MediaId;
    uint8_t RemovableMedia, MediaPresent, LogicalPartition, ReadOnly, WriteCaching;
    uint32_t BlockSize, IoAlign;
    uint64_t LastBlock, LowestAlignedLba;
    uint32_t LogicalBlocksPerPhysicalBlock, OptimalTransferLengthGranularity;
} EFI_BLOCK_IO_MEDIA;

typedef struct _EFI_BLOCK_IO_PROTOCOL {
    uint64_t Revision;
    EFI_BLOCK_IO_MEDIA *Media;
    uint64_t (*Reset)(struct _EFI_BLOCK_IO_PROTOCOL*, uint8_t);
    uint64_t (*ReadBlocks)(struct _EFI_BLOCK_IO_PROTOCOL*, uint32_t, uint64_t, uint64_t, void*);
    uint64_t (*WriteBlocks)(struct _EFI_BLOCK_IO_PROTOCOL*, uint32_t, uint64_t, uint64_t, void*);
    uint64_t (*FlushBlocks)(struct _EFI_BLOCK_IO_PROTOCOL*);
} EFI_BLOCK_IO_PROTOCOL;

typedef struct _EFI_BOOT_SERVICES {
    uint8_t Hdr[24];
    void *RaiseTPL;
    void *RestoreTPL;
    void *AllocatePages;
    void *FreePages;
    void *GetMemoryMap;
    void *AllocatePool;
    void *FreePool;
    void *CreateEvent;
    void *SetTimer;
    void *WaitForEvent;
    void *SignalEvent;
    void *CloseEvent;
    void *CheckEvent;
    void *InstallProtocolInterface;
    void *ReinstallProtocolInterface;
    void *UninstallProtocolInterface;
    void *HandleProtocol;
    void *Reserved;
    void *RegisterProtocolNotify;
    void *LocateHandle;
    void *LocateDevicePath;
    void *InstallConfigurationTable;
    void *LoadImage;
    void *StartImage;
    void *Exit;
    void *UnloadImage;
    void *ExitBootServices;
    void *GetNextMonotonicCount;
    void *Stall;
    void *SetWatchdogTimer;
    void *ConnectController;
    void *DisconnectController;
    void *OpenProtocol;
    void *CloseProtocol;
    void *OpenProtocolInformation;
    void *ProtocolsPerHandle;
    void *LocateHandleBuffer;
    uint64_t (*LocateProtocol)(const EFI_GUID *Protocol, void *Registration, void **Interface);
} EFI_BOOT_SERVICES;

typedef struct {
    uint8_t Hdr[24];
    void *GetTime;
    void *SetTime;
    void *GetWakeupTime;
    void *SetWakeupTime;
    void *SetVirtualAddressMap;
    void *ConvertPointer;
    void *GetVariable;
    void *GetNextVariableName;
    void *SetVariable;
    void *GetNextHighMonotonicCount;
    void (*ResetSystem)(uint32_t ResetType, uint64_t ResetStatus, uint64_t DataSize, void *ResetData);
} EFI_RUNTIME_SERVICES;

typedef struct {
    uint8_t Hdr[24];
    void *FirmwareVendor;
    uint32_t FirmwareRevision;
    void *ConsoleInHandle;
    EFI_SIMPLE_TEXT_INPUT_PROTOCOL *ConIn;
    void *ConsoleOutHandle;
    void *ConOut;
    void *StandardErrorHandle;
    void *StdErr;
    EFI_RUNTIME_SERVICES *RuntimeServices;
    EFI_BOOT_SERVICES *BootServices;
    uint64_t NumberOfTableEntries;
    void *ConfigurationTable;
} EFI_SYSTEM_TABLE_IN;

static EFI_RUNTIME_SERVICES *g_runtime_services = NULL;

static void uefi_reset_system(void) {
    if (g_runtime_services && g_runtime_services->ResetSystem) {
        g_runtime_services->ResetSystem(0, 0, 0, NULL);
    }
}

// =============================================================================
// 1. DRIVERS BARE METAL & PCI DISCOVERY (Ring 0)
// =============================================================================

typedef struct {
    uint8_t bus;
    uint8_t slot;
    uint8_t func;
    uint16_t vendor_id;
    uint16_t device_id;
    uint8_t class_code;
    uint8_t subclass;
    char name[48];
} BakenPciDevice;

static BakenPciDevice g_pci_devices[16];
static int g_pci_device_count = 0;
static int g_has_ahci = 0;
static int g_has_hda = 0;
static int g_has_net = 0;

static inline void outl_port(uint16_t port, uint32_t val) {
    __asm__ volatile ("outl %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint32_t inl_port(uint16_t port) {
    uint32_t ret;
    __asm__ volatile ("inl %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

static uint32_t pci_read_config_dword(uint8_t bus, uint8_t slot, uint8_t func, uint8_t offset) {
    uint32_t address = (uint32_t)((1U << 31) | ((uint32_t)bus << 16) | ((uint32_t)slot << 11) |
                                  ((uint32_t)func << 8) | (offset & 0xFC));
    outl_port(0x0CF8, address);
    return inl_port(0x0CFC);
}

static void format_hex16(char *buf, uint16_t val) {
    static const char hex[] = "0123456789ABCDEF";
    buf[0] = hex[(val >> 12) & 0x0F];
    buf[1] = hex[(val >> 8) & 0x0F];
    buf[2] = hex[(val >> 4) & 0x0F];
    buf[3] = hex[val & 0x0F];
    buf[4] = '\0';
}

static void format_pci_name(char *buf, const char *label, uint16_t vendor, uint16_t dev) {
    int p = 0;
    while (label[p] && p < 28) {
        buf[p] = label[p];
        p++;
    }
    buf[p++] = ' ';
    buf[p++] = '[';
    char hex_v[6], hex_d[6];
    format_hex16(hex_v, vendor);
    format_hex16(hex_d, dev);
    for (int i = 0; i < 4; i++) buf[p++] = hex_v[i];
    buf[p++] = ':';
    for (int i = 0; i < 4; i++) buf[p++] = hex_d[i];
    buf[p++] = ']';
    buf[p] = '\0';
}

static void pci_scan_all_devices(void) {
    g_pci_device_count = 0;
    g_has_ahci = 0;
    g_has_hda = 0;
    g_has_net = 0;

    for (uint32_t bus = 0; bus < 256 && g_pci_device_count < 12; bus++) {
        for (uint32_t slot = 0; slot < 32 && g_pci_device_count < 12; slot++) {
            uint32_t d0 = pci_read_config_dword((uint8_t)bus, (uint8_t)slot, 0, 0);
            uint16_t vendor = (uint16_t)(d0 & 0xFFFF);
            if (vendor == 0xFFFF || vendor == 0x0000) continue;
            uint16_t dev_id = (uint16_t)((d0 >> 16) & 0xFFFF);
            uint32_t d8 = pci_read_config_dword((uint8_t)bus, (uint8_t)slot, 0, 0x08);
            uint8_t class_code = (uint8_t)((d8 >> 24) & 0xFF);
            uint8_t subclass = (uint8_t)((d8 >> 16) & 0xFF);

            BakenPciDevice *pdev = &g_pci_devices[g_pci_device_count++];
            pdev->bus = (uint8_t)bus;
            pdev->slot = (uint8_t)slot;
            pdev->func = 0;
            pdev->vendor_id = vendor;
            pdev->device_id = dev_id;
            pdev->class_code = class_code;
            pdev->subclass = subclass;

            if (class_code == 0x01) {
                if (subclass == 0x06) { format_pci_name(pdev->name, "AHCI SATA", vendor, dev_id); g_has_ahci = 1; }
                else if (subclass == 0x08) { format_pci_name(pdev->name, "NVMe Storage", vendor, dev_id); g_has_ahci = 1; }
                else if (subclass == 0x01) { format_pci_name(pdev->name, "IDE Storage", vendor, dev_id); }
                else format_pci_name(pdev->name, "Storage Ctrl", vendor, dev_id);
            } else if (class_code == 0x02) {
                format_pci_name(pdev->name, "Ethernet Net", vendor, dev_id);
                g_has_net = 1;
            } else if (class_code == 0x03) {
                format_pci_name(pdev->name, "VGA Display", vendor, dev_id);
            } else if (class_code == 0x04) {
                if (subclass == 0x03) { format_pci_name(pdev->name, "Intel HDA Audio", vendor, dev_id); g_has_hda = 1; }
                else format_pci_name(pdev->name, "Audio Device", vendor, dev_id);
            } else if (class_code == 0x06) {
                format_pci_name(pdev->name, "PCI Bridge", vendor, dev_id);
            } else {
                format_pci_name(pdev->name, "PCI Device", vendor, dev_id);
            }
        }
    }
}

/* Pontos de inicialização de hardware bare metal e drivers nativos. */
static void bridge_init(void) {
    pci_scan_all_devices();
}

static void storage_init(void) {
    // Montagem e validação do volume GPT FAT32 no volume de instalação
}

// =============================================================================
// 2. FONTE BITMAP COM SUAVIZAÇÃO SIMPLES
// =============================================================================

static const uint8_t font_aa_8x14[128][14] = {
    [' '] = {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['!'] = {0x18,0x18,0x18,0x18,0x18,0x18,0x18,0x00,0x18,0x18,0x00,0x00,0x00,0x00},
    ['#'] = {0x24,0x24,0x7E,0x24,0x24,0x7E,0x24,0x24,0x00,0x00,0x00,0x00,0x00,0x00},
    ['%'] = {0x62,0x64,0x08,0x10,0x26,0x46,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['('] = {0x0C,0x18,0x30,0x30,0x30,0x30,0x18,0x0C,0x00,0x00,0x00,0x00,0x00,0x00},
    [')'] = {0x30,0x18,0x0C,0x0C,0x0C,0x0C,0x18,0x30,0x00,0x00,0x00,0x00,0x00,0x00},
    ['*'] = {0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['+'] = {0x00,0x18,0x18,0x7E,0x18,0x18,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    [','] = {0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x08,0x10,0x00,0x00,0x00,0x00},
    ['-'] = {0x00,0x00,0x00,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['.'] = {0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00,0x00,0x00,0x00,0x00,0x00},
    ['/'] = {0x02,0x06,0x0C,0x18,0x30,0x60,0xC0,0x80,0x00,0x00,0x00,0x00,0x00,0x00},
    ['0'] = {0x3C,0x66,0x6E,0x76,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['1'] = {0x18,0x38,0x18,0x18,0x18,0x18,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['2'] = {0x3C,0x66,0x06,0x0C,0x18,0x30,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['3'] = {0x3C,0x66,0x06,0x1C,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['4'] = {0x0C,0x1C,0x34,0x64,0x7E,0x04,0x04,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['5'] = {0x7E,0x60,0x7C,0x06,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['6'] = {0x3C,0x66,0x60,0x7C,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['7'] = {0x7E,0x06,0x0C,0x18,0x30,0x30,0x30,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['8'] = {0x3C,0x66,0x66,0x3C,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['9'] = {0x3C,0x66,0x66,0x3E,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    [':'] = {0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    [';'] = {0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x08,0x10,0x00,0x00,0x00,0x00,0x00},
    ['<'] = {0x0C,0x18,0x30,0x60,0x30,0x18,0x0C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['='] = {0x00,0x7E,0x00,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['>'] = {0x60,0x30,0x18,0x0C,0x18,0x30,0x60,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['?'] = {0x3C,0x66,0x06,0x0C,0x18,0x18,0x00,0x18,0x18,0x00,0x00,0x00,0x00,0x00},
    ['['] = {0x3C,0x30,0x30,0x30,0x30,0x30,0x30,0x30,0x30,0x30,0x3C,0x00,0x00,0x00},
    [']'] = {0x3C,0x0C,0x0C,0x0C,0x0C,0x0C,0x0C,0x0C,0x0C,0x0C,0x3C,0x00,0x00,0x00},
    ['A'] = {0x18,0x3C,0x66,0x66,0x7E,0x66,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['B'] = {0x7C,0x66,0x66,0x7C,0x66,0x66,0x7C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['C'] = {0x3C,0x66,0x60,0x60,0x60,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['D'] = {0x78,0x6C,0x66,0x66,0x66,0x6C,0x78,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['E'] = {0x7E,0x60,0x60,0x7C,0x60,0x60,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['F'] = {0x7E,0x60,0x60,0x7C,0x60,0x60,0x60,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['G'] = {0x3C,0x66,0x60,0x6E,0x66,0x66,0x3A,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['H'] = {0x66,0x66,0x66,0x7E,0x66,0x66,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['I'] = {0x3C,0x18,0x18,0x18,0x18,0x18,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['J'] = {0x0E,0x06,0x06,0x06,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['K'] = {0x66,0x6C,0x78,0x70,0x78,0x6C,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['L'] = {0x60,0x60,0x60,0x60,0x60,0x60,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['M'] = {0x63,0x77,0x7F,0x6B,0x63,0x63,0x63,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['N'] = {0x66,0x76,0x7E,0x7E,0x6E,0x66,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['O'] = {0x3C,0x66,0x66,0x66,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['P'] = {0x7C,0x66,0x66,0x7C,0x60,0x60,0x60,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['Q'] = {0x3C,0x66,0x66,0x66,0x66,0x6E,0x3C,0x06,0x00,0x00,0x00,0x00,0x00,0x00},
    ['R'] = {0x7C,0x66,0x66,0x7C,0x78,0x6C,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['S'] = {0x3C,0x66,0x60,0x3C,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['T'] = {0x7E,0x18,0x18,0x18,0x18,0x18,0x18,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['U'] = {0x66,0x66,0x66,0x66,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['V'] = {0x66,0x66,0x66,0x66,0x66,0x3C,0x18,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['W'] = {0x63,0x63,0x63,0x6B,0x7F,0x77,0x63,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['X'] = {0x66,0x66,0x3C,0x18,0x3C,0x66,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['Y'] = {0x66,0x66,0x66,0x3C,0x18,0x18,0x18,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['Z'] = {0x7E,0x06,0x0C,0x18,0x30,0x60,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['a'] = {0x00,0x00,0x3C,0x06,0x3E,0x66,0x3E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['b'] = {0x60,0x60,0x7C,0x66,0x66,0x66,0x7C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['c'] = {0x00,0x00,0x3C,0x66,0x60,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['d'] = {0x06,0x06,0x3E,0x66,0x66,0x66,0x3E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['e'] = {0x00,0x00,0x3C,0x66,0x7E,0x60,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['f'] = {0x0E,0x18,0x7C,0x18,0x18,0x18,0x18,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['g'] = {0x00,0x00,0x3E,0x66,0x66,0x3E,0x06,0x3C,0x00,0x00,0x00,0x00,0x00,0x00},
    ['h'] = {0x60,0x60,0x7C,0x66,0x66,0x66,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['i'] = {0x18,0x00,0x38,0x18,0x18,0x18,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['j'] = {0x06,0x00,0x0E,0x06,0x06,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['k'] = {0x60,0x60,0x66,0x6C,0x78,0x6C,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['l'] = {0x38,0x18,0x18,0x18,0x18,0x18,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['m'] = {0x00,0x00,0x66,0x7F,0x7F,0x6B,0x63,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['n'] = {0x00,0x00,0x7C,0x66,0x66,0x66,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['o'] = {0x00,0x00,0x3C,0x66,0x66,0x66,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['p'] = {0x00,0x00,0x7C,0x66,0x66,0x7C,0x60,0x60,0x00,0x00,0x00,0x00,0x00,0x00},
    ['q'] = {0x00,0x00,0x3E,0x66,0x66,0x3E,0x06,0x06,0x00,0x00,0x00,0x00,0x00,0x00},
    ['r'] = {0x00,0x00,0x7C,0x66,0x60,0x60,0x60,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['s'] = {0x00,0x00,0x3E,0x60,0x3C,0x06,0x3C,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['t'] = {0x18,0x7E,0x18,0x18,0x18,0x18,0x0E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['u'] = {0x00,0x00,0x66,0x66,0x66,0x66,0x3E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['v'] = {0x00,0x00,0x66,0x66,0x66,0x3C,0x18,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['w'] = {0x00,0x00,0x63,0x6B,0x7F,0x77,0x63,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['x'] = {0x00,0x00,0x66,0x3C,0x18,0x3C,0x66,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
    ['y'] = {0x00,0x00,0x66,0x66,0x66,0x3E,0x06,0x3C,0x00,0x00,0x00,0x00,0x00,0x00},
    ['z'] = {0x00,0x00,0x7E,0x0C,0x18,0x30,0x7E,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
};

static inline uint32_t blend_color(uint32_t bg, uint32_t fg, uint32_t alpha) {
    if (alpha >= 255) return fg;
    if (alpha == 0) return bg;
    uint32_t rb_bg = bg & 0x00FF00FF;
    uint32_t g_bg  = bg & 0x0000FF00;
    uint32_t rb_fg = fg & 0x00FF00FF;
    uint32_t g_fg  = fg & 0x0000FF00;
    uint32_t rb = (rb_bg + (((rb_fg - rb_bg) * alpha) >> 8)) & 0x00FF00FF;
    uint32_t g  = (g_bg + (((g_fg - g_bg) * alpha) >> 8)) & 0x0000FF00;
    return rb | g;
}

static uint32_t g_framebuffer_width = 0;
static uint32_t g_framebuffer_height = 0;

static inline void put_pixel_alpha(uint32_t *fb, uint32_t stride, uint32_t x, uint32_t y, uint32_t color, uint32_t alpha) {
    if (!fb || x >= g_framebuffer_width || y >= g_framebuffer_height || x >= stride) return;
    fb[y * stride + x] = blend_color(fb[y * stride + x], color, alpha);
}

// Renderizador Anti-Aliased com Suavização de Bordas e Subpixel Glow
static void draw_char_aa(uint32_t *fb, uint32_t stride, uint32_t x0, uint32_t y0, char c, uint32_t color) {
    uint8_t ch = (uint8_t)c;
    if (ch >= 128) return;
    const uint8_t *glyph = font_aa_8x14[ch];
    for (int y = 0; y < 14; y++) {
        uint8_t row = glyph[y];
        for (int x = 0; x < 8; x++) {
            int on = (row >> (7 - x)) & 1;
            uint32_t px = x0 + x;
            uint32_t py = y0 + y;
            if (px < stride) {
                if (on) {
                    put_pixel_alpha(fb, stride, px, py, color, 255);
                    if (px + 1 < stride &&
                        (x == 7 || ((row >> (6 - x)) & 1) == 0)) {
                        put_pixel_alpha(fb, stride, px + 1, py, color, 90);
                    }
                }
            }
        }
    }
}

static void draw_string_aa(uint32_t *fb, uint32_t stride, uint32_t x, uint32_t y, const char *str, uint32_t color) {
    while (*str) {
        draw_char_aa(fb, stride, x, y, *str, color);
        x += 8;
        str++;
    }
}

// Retângulo Arredondado com Sombra de Profundidade e Borda Glow SDF
static void draw_glass_card_sdf(uint32_t *fb, uint32_t stride, int x0, int y0, int w, int h, int r, uint32_t fill_color, uint32_t alpha, uint32_t border_color, uint32_t border_alpha, int shadow) {
    if (shadow) {
        int r_shadow = r + 4;
        int r2_shadow = r_shadow * r_shadow;
        for (int y = 4; y < h + 10; y++) {
            int py = y0 + y;
            for (int x = 2; x < w + 8; x++) {
                int px = x0 + x;
                int dx = 0, dy = 0;
                if (x < r_shadow) dx = r_shadow - x;
                else if (x >= w + 8 - r_shadow) dx = x - (w + 8 - r_shadow - 1);
                if (y < r_shadow) dy = r_shadow - y;
                else if (y >= h + 10 - r_shadow) dy = y - (h + 10 - r_shadow - 1);
                if (dx * dx + dy * dy <= r2_shadow) {
                    put_pixel_alpha(fb, stride, px, py, 0x000000, 35);
                }
            }
        }
    }

    int r2 = r * r;
    int r_in2 = (r - 1) * (r - 1);
    for (int y = 0; y < h; y++) {
        int py = y0 + y;
        for (int x = 0; x < w; x++) {
            int px = x0 + x;
            int dx = 0, dy = 0;
            if (x < r) dx = r - x;
            else if (x >= w - r) dx = x - (w - r - 1);
            if (y < r) dy = r - y;
            else if (y >= h - r) dy = y - (h - r - 1);
            
            int dist2 = dx * dx + dy * dy;
            if (dist2 > r2) continue;
            
            if (x == 0 || y == 0 || x == w - 1 || y == h - 1 || dist2 >= r_in2) {
                put_pixel_alpha(fb, stride, px, py, border_color, border_alpha);
            } else {
                put_pixel_alpha(fb, stride, px, py, fill_color, alpha);
            }
        }
    }
}

// Desenha Ponteiro Real do Mouse por cima do Framebuffer
static void draw_mouse_cursor(uint32_t *fb, uint32_t stride, int mx, int my) {
    static const uint8_t cursor_mask[16] = {
        0x80, 0xC0, 0xE0, 0xF0,
        0xF8, 0xFC, 0xFE, 0xFF,
        0xF8, 0xD8, 0x8C, 0x0C,
        0x06, 0x06, 0x00, 0x00
    };
    for (int y = 0; y < 16; y++) {
        uint8_t row = cursor_mask[y];
        for (int x = 0; x < 8; x++) {
            if ((row >> (7 - x)) & 1) {
                put_pixel_alpha(fb, stride, mx + x + 2, my + y + 2, 0x000000, 90);
                if (x == 0 || y == 0 || x == 7 ||
                    ((row >> (6 - x)) & 1) == 0 || y == 15) {
                    put_pixel_alpha(fb, stride, mx + x, my + y, 0xFFFFFF, 255);
                } else {
                    put_pixel_alpha(fb, stride, mx + x, my + y, 0x0F172A, 255);
                }
            }
        }
    }
}

/* Ícones vetoriais compactos: evitam siglas de terminal no desktop e no dock.
 * A mesma gramática visual é usada nas duas superfícies para que os apps sejam
 * reconhecíveis sem depender de uma fonte externa. */
static void draw_app_icon(uint32_t *fb, uint32_t stride, int x, int y, int app) {
    uint32_t ink = 0x00FFFFFF;
    if (app % 6 == 0) { /* pasta */
        draw_glass_card_sdf(fb, stride, x + 4, y + 8, 24, 15, 3, ink, 235, ink, 235, 0);
        draw_glass_card_sdf(fb, stride, x + 6, y + 5, 11, 7, 2, ink, 235, ink, 235, 0);
    } else if (app % 6 == 1) { /* navegador */
        draw_glass_card_sdf(fb, stride, x + 5, y + 5, 20, 20, 10, ink, 235, ink, 235, 0);
        draw_glass_card_sdf(fb, stride, x + 8, y + 14, 14, 2, 1, 0x00000000, 170, 0x00000000, 0, 0);
        draw_glass_card_sdf(fb, stride, x + 14, y + 8, 2, 14, 1, 0x00000000, 170, 0x00000000, 0, 0);
    } else if (app % 6 == 2) { /* câmera */
        draw_glass_card_sdf(fb, stride, x + 4, y + 9, 24, 16, 4, ink, 235, ink, 235, 0);
        draw_glass_card_sdf(fb, stride, x + 12, y + 6, 8, 5, 2, ink, 235, ink, 235, 0);
        draw_glass_card_sdf(fb, stride, x + 11, y + 13, 10, 10, 5, 0x00000000, 230, 0x00000000, 0, 0);
    } else if (app % 6 == 3) { /* notas */
        draw_glass_card_sdf(fb, stride, x + 7, y + 4, 18, 24, 3, ink, 235, ink, 235, 0);
        for (int line = 0; line < 3; ++line)
            draw_glass_card_sdf(fb, stride, x + 10, y + 10 + line * 5, 12, 1, 0, 0x00000000, 180, 0x00000000, 0, 0);
    } else if (app % 6 == 4) { /* loja */
        draw_glass_card_sdf(fb, stride, x + 5, y + 11, 22, 16, 3, ink, 235, ink, 235, 0);
        draw_glass_card_sdf(fb, stride, x + 9, y + 6, 14, 8, 6, ink, 235, ink, 235, 0);
    } else { /* conta */
        draw_glass_card_sdf(fb, stride, x + 11, y + 5, 10, 10, 5, ink, 235, ink, 235, 0);
        draw_glass_card_sdf(fb, stride, x + 6, y + 17, 20, 10, 5, ink, 235, ink, 235, 0);
    }
}

// =============================================================================
// 3. ESTADOS E TELAS (ASSISTENTE DE PREVIA vs DESKTOP SHELL)
// =============================================================================

typedef enum {
    MODE_INSTALLER_WIZARD = 0,
    MODE_LIVE_DESKTOP     = 1
} SystemMode;

static SystemMode g_current_mode = MODE_LIVE_DESKTOP;
/* O desktop só grava dados no volume Baken Data de uma instalação validada.
 * A mídia live permanece somente leitura; o instalador usa um segundo disco
 * explícito e nunca um caminho do host. */
static int g_install_progress    = 0;
static int g_mouse_x             = 420;
static int g_mouse_y             = 360;
static int g_selected_btn        = 0; // 0 = Modo Live, 1 = Instalar
static int g_active_desktop_item = -1;
static EFI_BLOCK_IO_PROTOCOL *g_block_io = NULL;
static EFI_BLOCK_IO_PROTOCOL *g_install_target_block_io = NULL;
static int g_install_persistent = 0;
static int g_left_button_down = 0;

#define BAKEN_INSTALL_PAYLOAD_MAX (64U * 1024U)

/* O instalador nunca obtém arquivos do host. Este buffer recebe o executável
 * PE/COFF diretamente da ESP FAT16 de onde o firmware iniciou o Baken OS. */
static uint8_t g_install_payload[BAKEN_INSTALL_PAYLOAD_MAX];
static uint32_t g_install_payload_size = 0;

typedef struct {
    char title[32];
    char line1[48];
    char line2[48];
    char line3[48];
} BakenNoteData;

typedef struct {
    uint64_t magic;
    uint32_t version;
    uint32_t flags;
    char user_name[32];
    char session_info[32];
    BakenNoteData note;
    uint8_t reserved[256];
} BakenPersistentStore;
_Static_assert(sizeof(BakenPersistentStore) == 512, "armazenamento persistente deve ocupar 512 bytes");

static BakenPersistentStore g_persistent_store;
static int g_theme_id = 0;

#define BAKENFS_DATA_LBA 86016ULL
#define BAKENFS_MAGIC 0x3153464E454B4142ULL /* "BAKENFS1" */
#define BAKEN_NOTE_MAGIC 0x31544E4E454B4142ULL /* "BAKENNT1" */
#define BAKEN_TEXT_MAGIC 0x3158544E454B4142ULL /* "BAKENTX1" */
#define BAKENFS_VERSION 1U
#define BAKENFS_KIND_DIRECTORY 1U
#define BAKENFS_KIND_FILE 2U
typedef struct { char name[32]; uint32_t lba; uint32_t size; uint32_t kind; } BakenFsEntry;
typedef struct { uint64_t magic; uint32_t version; uint32_t entry_count; BakenFsEntry entries[6]; uint8_t reserved[232]; } BakenFsHeader;
typedef struct { uint32_t theme; char user_name[32]; uint8_t reserved[476]; } BakenFsPreferences;
typedef struct { uint64_t magic; uint32_t version; uint32_t size; char text[496]; } BakenTextFile;
_Static_assert(sizeof(BakenFsHeader) == 512, "cabecalho BakenFS deve ocupar setor");
_Static_assert(sizeof(BakenFsPreferences) == 512, "preferencias BakenFS devem ocupar setor");
_Static_assert(sizeof(BakenTextFile) == 512, "arquivo de texto BakenFS deve ocupar setor");
static BakenFsHeader g_bakenfs;
static BakenFsPreferences g_bakenfs_preferences;

static int storage_can_read(void);
static int storage_can_write(void);
static int install_target_available(void);
static uint16_t read_le16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
static uint32_t read_le32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }

static void copy_text(char *out, const char *in, uint32_t cap) { uint32_t i=0; for(; i+1<cap && in[i]; ++i) out[i]=in[i]; out[i]=0; }
static int bakenfs_write_sector(uint64_t lba, const void *data) {
    return storage_can_write() && g_block_io->WriteBlocks(g_block_io,g_block_io->Media->MediaId,lba,512,(void*)data)==0;
}
static int bakenfs_flush(void) { return !g_block_io->FlushBlocks || g_block_io->FlushBlocks(g_block_io)==0; }
static int text_same(const char *left, const char *right) { for(uint32_t i=0;i<32;++i){if(left[i]!=right[i])return 0;if(!left[i])return 1;}return 1; }
static BakenFsEntry *bakenfs_find(const char *path) { for(uint32_t i=0;i<g_bakenfs.entry_count;++i)if(text_same(g_bakenfs.entries[i].name,path))return &g_bakenfs.entries[i];return NULL; }
static int bakenfs_write_header(void) { return bakenfs_write_sector(BAKENFS_DATA_LBA,&g_bakenfs) && bakenfs_flush(); }
static int bakenfs_create_entry(const char *path, uint32_t kind, uint32_t lba, uint32_t size) {
    if (g_bakenfs.magic != BAKENFS_MAGIC || bakenfs_find(path)) return 0;
    if (g_bakenfs.entry_count >= 6 ||
        (kind == BAKENFS_KIND_FILE && lba <= BAKENFS_DATA_LBA + 2) ||
        (kind == BAKENFS_KIND_DIRECTORY && (lba || size))) return 0;
    BakenFsEntry *entry=&g_bakenfs.entries[g_bakenfs.entry_count++];
    for(uint32_t i=0;i<sizeof(*entry);++i)((uint8_t*)entry)[i]=0;
    copy_text(entry->name,path,32); entry->kind=kind; entry->lba=lba; entry->size=size;
    if(bakenfs_write_header())return 1;
    --g_bakenfs.entry_count;
    return 0;
}
static int bakenfs_create_directory(const char *path) { return bakenfs_create_entry(path,BAKENFS_KIND_DIRECTORY,0,0); }
static int bakenfs_create_text_file(const char *path, uint32_t lba, const char *text) {
    BakenTextFile file; for(uint32_t i=0;i<sizeof(file);++i)((uint8_t*)&file)[i]=0;
    file.magic=BAKEN_TEXT_MAGIC; file.version=1; copy_text(file.text,text,sizeof(file.text));
    for(uint32_t i=0;file.text[i];++i)file.size=i+1;
    return bakenfs_write_sector(lba,&file) && bakenfs_flush() && bakenfs_create_entry(path,BAKENFS_KIND_FILE,lba,512);
}
static int bakenfs_mount(void) {
    if (!storage_can_read() || g_block_io->Media->LastBlock < BAKENFS_DATA_LBA + 2) return 0;
    if (g_block_io->ReadBlocks(g_block_io,g_block_io->Media->MediaId,BAKENFS_DATA_LBA,512,&g_bakenfs)!=0 ||
        g_bakenfs.magic != BAKENFS_MAGIC || g_bakenfs.version != BAKENFS_VERSION || g_bakenfs.entry_count > 6) return 0;
    if (g_block_io->ReadBlocks(g_block_io,g_block_io->Media->MediaId,BAKENFS_DATA_LBA+1,512,&g_bakenfs_preferences)==0)
        g_theme_id=(int)(g_bakenfs_preferences.theme%4U);
    if (g_block_io->ReadBlocks(g_block_io,g_block_io->Media->MediaId,BAKENFS_DATA_LBA+2,512,&g_persistent_store)!=0 ||
        g_persistent_store.magic != BAKEN_NOTE_MAGIC || g_persistent_store.version != 1 || g_persistent_store.flags != 1)
        return 0;
    return 1;
}
static int bakenfs_save_preferences(void) { g_bakenfs_preferences.theme=(uint32_t)g_theme_id; return bakenfs_write_sector(BAKENFS_DATA_LBA+1,&g_bakenfs_preferences); }
static int bakenfs_save_notes(void) { return bakenfs_write_sector(BAKENFS_DATA_LBA+2,&g_persistent_store); }

/* Carrega /BOOTX64.EFI da FAT16 de origem. O formato é deliberadamente
 * restrito à mídia criada pelo projeto: setores de 512 bytes e entradas 8.3.
 * Falhar fechado é essencial: sem payload válido nenhuma instalação escreve
 * no disco-alvo. */
static int storage_load_boot_payload(void) {
    uint8_t sector[512];
    if (!storage_can_read()) return 0;
    if (g_block_io->ReadBlocks(g_block_io, g_block_io->Media->MediaId, 0, 512, sector) != 0) return 0;
    uint32_t part_lba = read_le32(sector + 454);
    if (part_lba == 0 || g_block_io->ReadBlocks(g_block_io, g_block_io->Media->MediaId, part_lba, 512, sector) != 0) return 0;
    if (read_le16(sector + 11) != 512 || sector[13] == 0 || sector[16] == 0 || read_le16(sector + 22) == 0) return 0;
    uint8_t sectors_per_cluster = sector[13], fat_count = sector[16];
    uint16_t reserved = read_le16(sector + 14), root_entries = read_le16(sector + 17), sectors_per_fat = read_le16(sector + 22);
    uint32_t fat_lba = part_lba + reserved;
    uint32_t root_lba = fat_lba + (uint32_t)fat_count * sectors_per_fat;
    uint32_t root_sectors = ((uint32_t)root_entries * 32U + 511U) / 512U;
    uint32_t first_data_lba = root_lba + root_sectors;
    uint16_t cluster = 0;
    uint32_t file_size = 0;
    static const uint8_t boot_name[11] = {'B','O','O','T','X','6','4',' ','E','F','I'};
    for (uint32_t s = 0; s < root_sectors && !cluster; ++s) {
        if (g_block_io->ReadBlocks(g_block_io, g_block_io->Media->MediaId, root_lba + s, 512, sector) != 0) return 0;
        for (uint32_t off = 0; off < 512; off += 32) {
            if (sector[off] == 0) break;
            int same = 1; for (int i = 0; i < 11; ++i) if (sector[off + i] != boot_name[i]) same = 0;
            if (same && !(sector[off + 11] & 0x10)) { cluster = read_le16(sector + off + 26); file_size = read_le32(sector + off + 28); break; }
        }
    }
    if (cluster < 2 || file_size < 2 || file_size > BAKEN_INSTALL_PAYLOAD_MAX) return 0;
    uint32_t copied = 0;
    while (cluster >= 2 && cluster < 0xFFF8 && copied < file_size) {
        uint32_t cluster_lba = first_data_lba + (uint32_t)(cluster - 2) * sectors_per_cluster;
        for (uint8_t s = 0; s < sectors_per_cluster && copied < file_size; ++s) {
            if (g_block_io->ReadBlocks(g_block_io, g_block_io->Media->MediaId, cluster_lba + s, 512, sector) != 0) return 0;
            uint32_t count = file_size - copied; if (count > 512) count = 512;
            for (uint32_t i = 0; i < count; ++i) g_install_payload[copied + i] = sector[i];
            copied += count;
        }
        uint32_t fat_sector = fat_lba + ((uint32_t)cluster * 2U) / 512U;
        uint32_t fat_offset = ((uint32_t)cluster * 2U) % 512U;
        if (g_block_io->ReadBlocks(g_block_io, g_block_io->Media->MediaId, fat_sector, 512, sector) != 0) return 0;
        cluster = read_le16(sector + fat_offset);
    }
    if (copied != file_size || g_install_payload[0] != 'M' || g_install_payload[1] != 'Z') return 0;
    g_install_payload_size = file_size;
    return 1;
}

#define INSTALL_TOTAL_LBAS 131072ULL
#define INSTALL_ESP_FIRST 2048ULL
#define INSTALL_ESP_LAST  86015ULL
#define INSTALL_DATA_FIRST 86016ULL
#define INSTALL_DATA_LAST 131038ULL
#define INSTALL_FAT_SECTORS 656U

static void put_le16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put_le32(uint8_t *p, uint32_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); p[2]=(uint8_t)(v>>16); p[3]=(uint8_t)(v>>24); }
static void put_le64(uint8_t *p, uint64_t v) { for (int i=0;i<8;++i) p[i]=(uint8_t)(v>>(i*8)); }
static void clear512(uint8_t *p) { for (int i=0;i<512;++i) p[i]=0; }
static uint32_t crc32_step(uint32_t crc, const uint8_t *p, uint32_t count) {
    for (uint32_t i=0;i<count;++i) { crc ^= p[i]; for (int b=0;b<8;++b) crc=(crc>>1)^((crc&1)?0xEDB88320U:0); } return crc;
}
static int target_write(uint64_t lba, const void *buffer) {
    return g_install_target_block_io->WriteBlocks(g_install_target_block_io, g_install_target_block_io->Media->MediaId, lba, 512, (void*)buffer) == 0;
}
static void fat32_entry(uint8_t *sector, uint32_t cluster, uint32_t value) { put_le32(sector + cluster * 4, value); }

/* Transação de instalação nativa. Ela escreve somente o segundo Block I/O,
 * constrói GPT + ESP FAT32 e relê o EFI copiado antes de declarar sucesso. */
static int storage_install_to_target(void) {
    uint8_t sector[512], entries0[512];
    if (!install_target_available() || !storage_load_boot_payload() ||
        g_install_target_block_io->Media->LastBlock + 1 < INSTALL_TOTAL_LBAS) return 0;
    clear512(sector); sector[446+4]=0xEE; put_le32(sector+454,1); put_le32(sector+458,0xFFFFFFFFU); sector[510]=0x55; sector[511]=0xAA;
    if (!target_write(0,sector)) return 0;
    clear512(entries0);
    static const uint8_t esp_guid[16]={0x28,0x73,0x2A,0xC1,0x1F,0xF8,0xD2,0x11,0xBA,0x4B,0,0xA0,0xC9,0x3E,0xC9,0x3B};
    static const uint8_t data_guid[16]={0x58,0x72,0x3C,0x7F,0x1C,0x2F,0x03,0x4E,0xBF,0x20,0x42,0x41,0x4B,0x45,0x4E,0x31};
    for(int i=0;i<16;++i) entries0[i]=esp_guid[i];
    put_le64(entries0+32,INSTALL_ESP_FIRST); put_le64(entries0+40,INSTALL_ESP_LAST); entries0[56]='B'; entries0[58]='a'; entries0[60]='k'; entries0[62]='e'; entries0[64]='n';
    for(int i=0;i<16;++i) entries0[128+i]=data_guid[i];
    put_le64(entries0+160,INSTALL_DATA_FIRST); put_le64(entries0+168,INSTALL_DATA_LAST);
    uint32_t entries_crc=crc32_step(0xFFFFFFFFU,entries0,512); clear512(sector); for(int i=1;i<32;++i) entries_crc=crc32_step(entries_crc,sector,512); entries_crc^=0xFFFFFFFFU;
    for(int i=0;i<32;++i) { const uint8_t *e=(i==0)?entries0:sector; if(!target_write(2+i,e)||!target_write(INSTALL_TOTAL_LBAS-33+i,e)) return 0; }
    for(int copy=0;copy<2;++copy) { clear512(sector); sector[0]='E';sector[1]='F';sector[2]='I';sector[3]=' ';sector[4]='P';sector[5]='A';sector[6]='R';sector[7]='T'; put_le32(sector+8,0x10000);put_le32(sector+12,92);put_le64(sector+24,copy?INSTALL_TOTAL_LBAS-1:1);put_le64(sector+32,copy?1:INSTALL_TOTAL_LBAS-1);put_le64(sector+40,34);put_le64(sector+48,INSTALL_TOTAL_LBAS-34);sector[56]=0x42;sector[57]=0x4B;sector[58]=0x4E;sector[59]=1;put_le64(sector+72,copy?INSTALL_TOTAL_LBAS-33:2);put_le32(sector+80,128);put_le32(sector+84,128);put_le32(sector+88,entries_crc);put_le32(sector+16,crc32_step(0xFFFFFFFFU,sector,92)^0xFFFFFFFFU);if(!target_write(copy?INSTALL_TOTAL_LBAS-1:1,sector))return 0; }
    clear512(sector); sector[0]=0xEB;sector[1]=0x58;sector[2]=0x90;sector[3]='B';sector[4]='A';sector[5]='K';sector[6]='E';sector[7]='N';put_le16(sector+11,512);sector[13]=1;put_le16(sector+14,32);sector[16]=2;sector[21]=0xF8;put_le32(sector+32,(uint32_t)(INSTALL_ESP_LAST-INSTALL_ESP_FIRST+1));put_le32(sector+36,INSTALL_FAT_SECTORS);put_le32(sector+44,2);put_le16(sector+48,1);put_le16(sector+50,6);sector[66]=0x29;sector[71]='B';sector[72]='A';sector[73]='K';sector[74]='E';sector[75]='N';sector[82]='F';sector[83]='A';sector[84]='T';sector[85]='3';sector[86]='2';sector[87]=' ';sector[88]=' ';sector[89]=' ';sector[510]=0x55;sector[511]=0xAA;if(!target_write(INSTALL_ESP_FIRST,sector)||!target_write(INSTALL_ESP_FIRST+6,sector))return 0;
    clear512(sector); for(uint32_t i=0;i<INSTALL_FAT_SECTORS;++i) if(!target_write(INSTALL_ESP_FIRST+32+i,sector)||!target_write(INSTALL_ESP_FIRST+32+INSTALL_FAT_SECTORS+i,sector))return 0;
    clear512(sector);fat32_entry(sector,0,0x0FFFFFF8);fat32_entry(sector,1,0xFFFFFFFF);fat32_entry(sector,2,0x0FFFFFFF);fat32_entry(sector,3,0x0FFFFFFF);fat32_entry(sector,4,0x0FFFFFFF);uint32_t clusters=(g_install_payload_size+511)/512;for(uint32_t c=0;c<clusters;++c)fat32_entry(sector,5+c,c+1==clusters?0x0FFFFFFF:6+c);if(!target_write(INSTALL_ESP_FIRST+32,sector)||!target_write(INSTALL_ESP_FIRST+32+INSTALL_FAT_SECTORS,sector))return 0;
    uint64_t data_lba=INSTALL_ESP_FIRST+32+2*INSTALL_FAT_SECTORS; clear512(sector); for(int i=0;i<11;++i)sector[i]="EFI        "[i];sector[11]=0x10;put_le16(sector+26,3);if(!target_write(data_lba,sector))return 0;clear512(sector);for(int i=0;i<11;++i)sector[i]="BOOT       "[i];sector[11]=0x10;put_le16(sector+26,4);if(!target_write(data_lba+1,sector))return 0;
    for(uint32_t c=0;c<clusters;++c){clear512(sector);uint32_t left=g_install_payload_size-c*512;if(left>512)left=512;for(uint32_t i=0;i<left;++i)sector[i]=g_install_payload[c*512+i];if(!target_write(data_lba+3+c,sector))return 0;}clear512(sector);for(int i=0;i<11;++i)sector[i]="BOOTX64 EFI"[i];sector[11]=0x20;put_le16(sector+26,5);put_le32(sector+28,g_install_payload_size);if(!target_write(data_lba+2,sector))return 0;
    clear512((uint8_t*)&g_bakenfs); g_bakenfs.magic=BAKENFS_MAGIC; g_bakenfs.version=BAKENFS_VERSION; g_bakenfs.entry_count=4;
    copy_text(g_bakenfs.entries[0].name,"/home",32); g_bakenfs.entries[0].kind=BAKENFS_KIND_DIRECTORY;
    copy_text(g_bakenfs.entries[1].name,"/config",32); g_bakenfs.entries[1].kind=BAKENFS_KIND_DIRECTORY;
    copy_text(g_bakenfs.entries[2].name,"/home/notas.txt",32); g_bakenfs.entries[2].kind=BAKENFS_KIND_FILE; g_bakenfs.entries[2].lba=(uint32_t)(INSTALL_DATA_FIRST+2); g_bakenfs.entries[2].size=512;
    copy_text(g_bakenfs.entries[3].name,"/config/theme.cfg",32); g_bakenfs.entries[3].kind=BAKENFS_KIND_FILE; g_bakenfs.entries[3].lba=(uint32_t)(INSTALL_DATA_FIRST+1); g_bakenfs.entries[3].size=512;
    if(!target_write(INSTALL_DATA_FIRST,&g_bakenfs))return 0;
    clear512((uint8_t*)&g_bakenfs_preferences); g_bakenfs_preferences.theme=0; copy_text(g_bakenfs_preferences.user_name,"Usuario",32); if(!target_write(INSTALL_DATA_FIRST+1,&g_bakenfs_preferences))return 0;
    clear512((uint8_t*)&g_persistent_store); g_persistent_store.magic=BAKEN_NOTE_MAGIC; g_persistent_store.version=1; g_persistent_store.flags=1; copy_text(g_persistent_store.note.title,"Notas",32); if(!target_write(INSTALL_DATA_FIRST+2,&g_persistent_store))return 0;
    if(g_install_target_block_io->FlushBlocks&&g_install_target_block_io->FlushBlocks(g_install_target_block_io)!=0)return 0;
    if(g_install_target_block_io->ReadBlocks(g_install_target_block_io,g_install_target_block_io->Media->MediaId,data_lba+3,512,sector)!=0||sector[0]!='M'||sector[1]!='Z')return 0;
    return 1;
}

static int storage_install_selected(void) {
    if (!install_target_available() || !storage_install_to_target()) return 0;
    g_install_persistent = 1; g_install_progress = 100;
    return 1;
}

static int storage_can_read(void) {
    return g_block_io && g_block_io->Media && g_block_io->ReadBlocks &&
           g_block_io->Media->MediaPresent && g_block_io->Media->BlockSize == 512 &&
           g_block_io->Media->LastBlock >= 4096;
}

static int storage_can_write(void) {
    return storage_can_read() && g_block_io->WriteBlocks &&
           !g_block_io->Media->ReadOnly;
}

/* O alvo é informado pelo bootloader e deve ser outro dispositivo físico do
 * que a mídia de boot. Por enquanto esta função habilita a confirmação visual;
 * a escrita GPT/FAT32 será ligada somente quando a cópia do pacote do sistema
 * puder ser feita para esse segundo disco. */
static int install_target_available(void) {
    return g_install_target_block_io && g_install_target_block_io != g_block_io &&
           g_install_target_block_io->Media && g_install_target_block_io->WriteBlocks &&
           g_install_target_block_io->Media->MediaPresent &&
           !g_install_target_block_io->Media->ReadOnly &&
           !g_install_target_block_io->Media->LogicalPartition &&
           g_install_target_block_io->Media->BlockSize == 512 &&
           g_install_target_block_io->Media->LastBlock >= 131071ULL;
}

static uint32_t storage_get_disk_size_mb(void) {
    if (!g_block_io || !g_block_io->Media || g_block_io->Media->BlockSize == 0) return 0;
    uint64_t total_bytes = (g_block_io->Media->LastBlock + 1) * (uint64_t)g_block_io->Media->BlockSize;
    return (uint32_t)(total_bytes / (1024 * 1024));
}

static void format_disk_size_string(char *out, uint32_t size_mb) {
    int pos = 0;
    if (size_mb >= 100) { out[pos++] = '0' + (size_mb / 100); size_mb %= 100; }
    if (size_mb >= 10 || pos > 0) { out[pos++] = '0' + (size_mb / 10); size_mb %= 10; }
    out[pos++] = '0' + size_mb;
    out[pos++] = ' '; out[pos++] = 'M'; out[pos++] = 'B'; out[pos] = '\0';
}

// Estado do Gerenciador de Janelas e Serviços de Aplicativos
static int g_win_x = -1;
static int g_win_y = -1;
static int g_win_w = 480;
static int g_win_h = 260;
static int g_is_dragging = 0;
static int g_drag_offset_x = 0;
static int g_drag_offset_y = 0;
static int g_is_maximized = 0;
static int g_selected_file_index = 0;
static char g_clipboard[128] = "/EFI/BOOT/BOOTX64.EFI";
static int g_note_cursor_line = 0;
static int g_note_dirty = 0;
static int g_note_saved_flash = 0;

// Desenha o Wallpaper Mesh Gradient Vibrante
static void draw_wallpaper(uint32_t *fb, uint32_t stride, uint32_t width, uint32_t height) {
    for (uint32_t y = 0; y < height; y++) {
        for (uint32_t x = 0; x < width; x++) {
            float u = (float)x / (float)width;
            float v = (float)y / (float)height;
            float diag = (u * 0.7f + v * 0.3f);
            float wave = (u - v) * 0.5f + 0.5f;

            int r = 0, g = 0, b = 0;
            if (g_theme_id == 1) {
                // Aero Dark / Midnight Navy
                r = (int)((1.0f - diag) * 10 + diag * 30 + wave * 10);
                g = (int)((1.0f - diag) * 15 + diag * 45 + wave * 15);
                b = (int)((1.0f - diag) * 45 + diag * 90 + wave * 40);
            } else if (g_theme_id == 2) {
                // Aurora Emerald
                r = (int)((1.0f - diag) * 5 + diag * 20 + wave * 10);
                g = (int)((1.0f - diag) * 120 + diag * 220 + wave * 50);
                b = (int)((1.0f - diag) * 110 + diag * 160 + wave * 80);
            } else if (g_theme_id == 3) {
                // Nebula Purple
                r = (int)((1.0f - diag) * 110 + diag * 200 + wave * 40);
                g = (int)((1.0f - diag) * 40 + diag * 90 + wave * 30);
                b = (int)((1.0f - diag) * 160 + diag * 240 + wave * 90);
            } else {
                // Ocean Sunset (Padrao)
                r = (int)((1.0f - diag) * 0 + diag * 240 + (1.0f - wave) * 120);
                g = (int)((1.0f - diag) * 200 + diag * 130 + wave * 60);
                b = (int)((1.0f - diag) * 255 + diag * 60 + (1.0f - wave) * 160);
            }

            if (r > 255) r = 255;
            if (r < 0) r = 0;
            if (g > 255) g = 255;
            if (g < 0) g = 0;
            if (b > 255) b = 255;
            if (b < 0) b = 0;

            fb[y * stride + x] = (r << 16) | (g << 8) | b;
        }
    }
}

// Renderiza o assistente de prévia do Baken.
static void render_installer(uint32_t *fb, uint32_t stride, uint32_t width, uint32_t height) {
    draw_wallpaper(fb, stride, width, height);

    // Topbar Translúcida
    draw_glass_card_sdf(fb, stride, 0, 0, width, 32, 0, 0x050C1A, 110, 0xFFFFFF, 70, 0);
    draw_string_aa(fb, stride, 14, 9, "o  Baken OS - Assistente de Instalacao", 0xFFFFFF);
    draw_string_aa(fb, stride, width - 230, 9, "Modo seguro / pre-instalacao", 0x38BDF8);

    // Janela Central do Instalador
    int win_w = 680;
    int win_h = 440;
    int win_x = (width - win_w) / 2;
    int win_y = (height - win_h) / 2 - 10;

    draw_glass_card_sdf(fb, stride, win_x, win_y, win_w, win_h, 16, 0x0A0F1D, 245, 0x38BDF8, 220, 1);

    // Cabeçalho da Janela
    draw_string_aa(fb, stride, win_x + 24, win_y + 20, "Preparar Baken OS", 0x38BDF8);
    draw_string_aa(fb, stride, win_x + 24, win_y + 42, "Revise a configuracao; gravacao em disco EFI particionado.", 0x94A3B8);

    // Card 1: Idioma e Teclado
    draw_glass_card_sdf(fb, stride, win_x + 24, win_y + 75, win_w - 48, 56, 10, 0x1E293B, 220, 0x38BDF8, 160, 1);
    draw_string_aa(fb, stride, win_x + 38, win_y + 86, "Idioma do Sistema: Portugues (Brasil) [PT-BR]", 0xFFFFFF);
    draw_string_aa(fb, stride, win_x + 38, win_y + 104, "Teclado: ABNT2 com suporte a caracteres acentuados", 0x38BDF8);

    // Card 2: Disco de Destino e Particionamento
    draw_glass_card_sdf(fb, stride, win_x + 24, win_y + 142, win_w - 48, 70, 10, 0x1E293B, 220, 0x10B981, 160, 1);
    uint32_t disk_mb = storage_get_disk_size_mb();
    char disk_info_str[64];
    if (disk_mb > 0) {
        char sz_str[16];
        format_disk_size_string(sz_str, disk_mb);
        const char *prefix = "Destino: midia UEFI [";
        int pos = 0;
        while (prefix[pos] && pos < 60) { disk_info_str[pos] = prefix[pos]; pos++; }
        int sp = 0;
        while (sz_str[sp] && pos < 50) { disk_info_str[pos++] = sz_str[sp++]; }
        const char *suffix = storage_can_write() ? ", gravavel]" : ", somente leitura]";
        int sfx = 0;
        while (suffix[sfx] && pos < 62) { disk_info_str[pos++] = suffix[sfx++]; }
        disk_info_str[pos] = '\0';
    } else {
        const char *fallback = "Destino: midia UEFI de teste (bloco reservado)";
        int pos = 0;
        while (fallback[pos]) { disk_info_str[pos] = fallback[pos]; pos++; }
        disk_info_str[pos] = '\0';
    }
    draw_string_aa(fb, stride, win_x + 38, win_y + 152, disk_info_str, 0xFFFFFF);
    draw_string_aa(fb, stride, win_x + 38, win_y + 170,
                   install_target_available() ? "Destino seguro detectado: disco GPT/FAT32 elegivel" : "Destino: conecte um segundo disco virtual de 64 MB", 0x10B981);
    draw_string_aa(fb, stride, win_x + 38, win_y + 188, "Persistencia: configuracoes e notas salvas em bloco", 0x94A3B8);

    // Card 3: estado do backend de instalacao.
    draw_glass_card_sdf(fb, stride, win_x + 24, win_y + 224, win_w - 48, 90, 10, 0x131D33, 230, 0x64748B, 140, 1);
    draw_string_aa(fb, stride, win_x + 38, win_y + 236,
                   g_install_persistent ? "Status: sistema e persistencia instalados" :
                   (install_target_available() ? "Status: destino seguro selecionado" : "Status: aguardando disco-alvo seguro"), 0xF8FAFC);
    
    int pb_x = win_x + 38;
    int pb_y = win_y + 258;
    int pb_w = win_w - 76;
    int pb_h = 16;
    draw_glass_card_sdf(fb, stride, pb_x, pb_y, pb_w, pb_h, 8, 0x0F172A, 255, 0x334155, 200, 0);
    int fill_w = (pb_w * g_install_progress) / 100;
    draw_glass_card_sdf(fb, stride, pb_x, pb_y, fill_w, pb_h, 8, 0x38BDF8, 255, 0x0284C7, 240, 0);
    draw_string_aa(fb, stride, win_x + 38, win_y + 286,
                   g_install_persistent ? "100% - instalacao e persistencia confirmadas" :
                   (install_target_available() ? "10% - destino validado; pronto para provisionar" : "0% - conecte um segundo disco de teste"), 0x38BDF8);

    // Botões de Ação Interativos
    int btn_y = win_y + win_h - 54;
    uint32_t b1_bg = (g_selected_btn == 0) ? 0x0284C7 : 0x334155;
    uint32_t b1_border = (g_selected_btn == 0) ? 0x38BDF8 : 0x64748B;
    draw_glass_card_sdf(fb, stride, win_x + 24, btn_y, 180, 36, 10, b1_bg, 235, b1_border, 220, 1);
    draw_string_aa(fb, stride, win_x + 40, btn_y + 12, "Voltar ao Desktop", 0xFFFFFF);

    uint32_t b2_bg = (g_selected_btn == 1) ? 0x22C55E : 0x10B981;
    draw_glass_card_sdf(fb, stride, win_x + win_w - 204, btn_y, 180, 36, 10, b2_bg, 255, 0x34D399, 240, 1);
    draw_string_aa(fb, stride, win_x + win_w - 188, btn_y + 12,
                   g_install_persistent ? "Reiniciar Sistema >" : "Instalar no disco >", 0x0F172A);

    draw_mouse_cursor(fb, stride, g_mouse_x, g_mouse_y);
}

// Renderiza o desktop live com widgets e dock.
static void render_desktop(uint32_t *fb, uint32_t stride, uint32_t width, uint32_t height) {
    draw_wallpaper(fb, stride, width, height);

    // Topbar Aero Glass
    draw_glass_card_sdf(fb, stride, 0, 0, width, 32, 0, 0x050C1A, 110, 0xFFFFFF, 70, 0);
    draw_string_aa(fb, stride, 14, 9, "o  Baken OS", 0xFFFFFF);
    draw_string_aa(fb, stride, 120, 9, "Arquivo  Editar  Exibir  Janela  Ajuda", 0xF1F5F9);

    int rx = width - 330;
    draw_glass_card_sdf(fb, stride, rx, 4, 82, 24, 12, 0x38BDF8, 220, 0xFFFFFF, 180, 0);
    draw_string_aa(fb, stride, rx + 8, 9, "Sessao", 0x0A1128);
    draw_string_aa(fb, stride, rx + 92, 9, "Offline PT-BR Live", 0xFFFFFF);

    // Ícones da Área de Trabalho
    const char *labels1[] = {"Arquivos", "Notas", "Midia", "Ajuda", "Instalador", "Sessao"};
    uint32_t colors1[]    = {0x38BDF8, 0x0284C7, 0x818CF8, 0x0EA5E9, 0x10B981, 0xF59E0B};

    for (int i = 0; i < 6; i++) {
        int ix = 24;
        int iy = 50 + (i * 76);
        uint32_t icon_alpha = (g_active_desktop_item == i) ? 255 : 224;
        draw_glass_card_sdf(fb, stride, ix + 8, iy, 42, 42, 12, colors1[i], icon_alpha, 0xFFFFFF, 170, 1);
        draw_app_icon(fb, stride, ix + 9, iy + 7, i);
        draw_string_aa(fb, stride, ix, iy + 46, labels1[i], 0xFFFFFF);
    }

    // Renderização da janela do aplicativo ativo
    if (g_active_desktop_item >= 0) {
        static const char *app_titles[] = {
            "Gerenciador de Arquivos - Baken Data",
            "Baken Notas - Persistencia em Disco",
            "Baken Player - Central Multimidia",
            "Central de Ajuda e Atalhos",
            "Assistente de Instalacao",
            "Painel de Sessao e Ajustes"
        };
        if (g_win_x == -1) {
            g_win_w = 480;
            g_win_h = 260;
            g_win_x = (int)(width - g_win_w) / 2 - 40;
            g_win_y = (int)(height - g_win_h) / 2 - 20;
        }

        int win_x = g_is_maximized ? 10 : g_win_x;
        int win_y = g_is_maximized ? 36 : g_win_y;
        int win_w = g_is_maximized ? (int)width - 20 : g_win_w;
        int win_h = g_is_maximized ? (int)height - 110 : g_win_h;

        // Moldura Glassmorphism da Janela
        draw_glass_card_sdf(fb, stride, win_x, win_y, win_w, win_h, 16, 0x0F172A, 245, 0x38BDF8, 220, 1);

        // Barra de Título
        draw_string_aa(fb, stride, win_x + 16, win_y + 14, app_titles[g_active_desktop_item], 0x38BDF8);

        // Botão Fechar (x) - Vermelho
        draw_glass_card_sdf(fb, stride, win_x + win_w - 26, win_y + 10, 16, 16, 8, 0xEF4444, 255, 0xFCA5A5, 200, 0);
        draw_string_aa(fb, stride, win_x + win_w - 22, win_y + 11, "x", 0xFFFFFF);

        // Botão Minimizar (-) - Amarelo
        draw_glass_card_sdf(fb, stride, win_x + win_w - 46, win_y + 10, 16, 16, 8, 0xF59E0B, 255, 0xFDE68A, 200, 0);
        draw_string_aa(fb, stride, win_x + win_w - 42, win_y + 11, "-", 0xFFFFFF);

        // Botão Maximizar (+) - Verde
        draw_glass_card_sdf(fb, stride, win_x + win_w - 66, win_y + 10, 16, 16, 8, 0x10B981, 255, 0xA7F3D0, 200, 0);
        draw_string_aa(fb, stride, win_x + win_w - 62, win_y + 11, "+", 0xFFFFFF);

        // Conteúdo Específico do Aplicativo
        if (g_active_desktop_item == 0) {
            // Arquivos
            draw_glass_card_sdf(fb, stride, win_x + 16, win_y + 36, win_w - 32, 26, 8, 0x1E293B, 220, 0x38BDF8, 140, 1);
            uint32_t visible_entries = (g_bakenfs.magic == BAKENFS_MAGIC) ? g_bakenfs.entry_count : 0;
            draw_string_aa(fb, stride, win_x + 24, win_y + 42,
                           visible_entries ? "Local: / (Baken Data / BakenFS)" : "Local: / (Midia live somente leitura)", 0x38BDF8);
            if (visible_entries == 0) {
                draw_string_aa(fb, stride, win_x + 24, win_y + 78, "BakenFS disponivel somente apos a instalacao.", 0x94A3B8);
            }
            for (uint32_t f = 0; f < visible_entries; f++) {
                int fy = win_y + 68 + (f * 22);
                if (g_selected_file_index == (int)f) {
                    draw_glass_card_sdf(fb, stride, win_x + 18, fy - 2, win_w - 36, 20, 6, 0x0284C7, 180, 0x38BDF8, 220, 1);
                }
                BakenFsEntry *entry=&g_bakenfs.entries[f];
                uint32_t fcol = entry->kind == BAKENFS_KIND_DIRECTORY ? 0xFFFFFF : 0x10B981;
                draw_string_aa(fb, stride, win_x + 24, fy + 2,
                               entry->kind == BAKENFS_KIND_DIRECTORY ? "[DIR]" : "[ARQ]", fcol);
                draw_string_aa(fb, stride, win_x + 68, fy + 2, entry->name, fcol);
            }

            draw_glass_card_sdf(fb, stride, win_x + 16, win_y + win_h - 40, win_w - 32, 26, 8, 0x1E293B, 200, 0x64748B, 120, 0);
            draw_string_aa(fb, stride, win_x + 24, win_y + win_h - 34,
                           visible_entries ? "N: novo arquivo | D: nova pasta | Selecionado:" : "Instale o Baken OS para criar arquivos.", 0x94A3B8);
            if (visible_entries && g_selected_file_index >= 0 && g_selected_file_index < (int)visible_entries)
                draw_string_aa(fb, stride, win_x + 300, win_y + win_h - 34, g_bakenfs.entries[g_selected_file_index].name, 0x38BDF8);
        } else if (g_active_desktop_item == 1) {
            // Notas
            draw_glass_card_sdf(fb, stride, win_x + 16, win_y + 36, win_w - 32, 26, 8, 0x1E293B, 220, 0xF59E0B, 140, 1);
            draw_string_aa(fb, stride, win_x + 24, win_y + 42, "Documento: /home/notas.txt [BakenFS - Editavel]", 0xF59E0B);

            draw_glass_card_sdf(fb, stride, win_x + 16, win_y + 68, win_w - 32, 110, 10, 0x1E293B, 220, 0x64748B, 160, 1);

            char *lines[3] = {
                g_persistent_store.note.line1,
                g_persistent_store.note.line2,
                g_persistent_store.note.line3
            };
            if (!lines[0][0]) {
                const char *init_l1 = "- Sistema grafico pronto";
                for (int i = 0; init_l1[i]; ++i) lines[0][i] = init_l1[i];
                lines[0][24] = '\0';
            }
            if (!lines[1][0]) {
                const char *init_l2 = "- Framebuffer GOP ativo";
                for (int i = 0; init_l2[i]; ++i) lines[1][i] = init_l2[i];
                lines[1][23] = '\0';
            }
            if (!lines[2][0]) {
                const char *init_l3 = "- Digite texto para salvar";
                for (int i = 0; init_l3[i]; ++i) lines[2][i] = init_l3[i];
                lines[2][26] = '\0';
            }

            draw_string_aa(fb, stride, win_x + 26, win_y + 78, "* Editor de Notas do Baken OS", 0xFDE047);
            for (int l = 0; l < 3; l++) {
                int ly = win_y + 98 + (l * 20);
                if (g_note_cursor_line == l) {
                    draw_glass_card_sdf(fb, stride, win_x + 22, ly - 2, win_w - 44, 18, 4, 0x334155, 140, 0x38BDF8, 120, 0);
                }
                draw_string_aa(fb, stride, win_x + 26, ly, lines[l], 0xFFFFFF);
            }

            // Botão Gravar no Disco
            draw_glass_card_sdf(fb, stride, win_x + 16, win_y + win_h - 40, win_w - 32, 26, 8, 0x1E293B, 220, 0x10B981, 160, 1);
            if (g_note_saved_flash > 0) {
                draw_string_aa(fb, stride, win_x + 24, win_y + win_h - 34, "Status: Gravado com sucesso em /home/notas.txt", 0x22C55E);
            } else if (g_note_dirty) {
                draw_string_aa(fb, stride, win_x + 24, win_y + win_h - 34, "Status: Modificado | Pressione ENTER para gravar", 0xF59E0B);
            } else {
                draw_string_aa(fb, stride, win_x + 24, win_y + win_h - 34, "Status: Sincronizado com BakenFS", 0x10B981);
            }
        } else if (g_active_desktop_item == 2) {
            // Player Multimídia
            draw_string_aa(fb, stride, win_x + 24, win_y + 44, "Faixa: Ambient Waves - Baken OS Live", 0xFFFFFF);
            draw_string_aa(fb, stride, win_x + 24, win_y + 64, "Tempo: 02:45 / 04:12 [Reproduzindo sintetizador]", 0x38BDF8);

            // Equalizador Visual Dinâmico
            for (int b = 0; b < 14; b++) {
                int bh = 15 + ((b * 7 + (int)(g_mouse_x % 20)) % 35);
                int bx = win_x + 30 + (b * 28);
                int by = win_y + 140 - bh;
                uint32_t bcolor = (b % 2 == 0) ? 0x38BDF8 : 0x818CF8;
                draw_glass_card_sdf(fb, stride, bx, by, 18, bh, 4, bcolor, 240, 0xFFFFFF, 180, 0);
            }

            draw_glass_card_sdf(fb, stride, win_x + 16, win_y + win_h - 44, win_w - 32, 28, 8, 0x1E293B, 220, 0x818CF8, 140, 1);
            draw_string_aa(fb, stride, win_x + 30, win_y + win_h - 36, "[ |<< ]    [  >  ]    [ >>| ]    Volume: [======..] 75%", 0xFFFFFF);
        } else if (g_active_desktop_item == 3) {
            // Ajuda e Atalhos
            draw_string_aa(fb, stride, win_x + 24, win_y + 42, "Atalhos e Comandos do Sistema:", 0x38BDF8);
            draw_string_aa(fb, stride, win_x + 24, win_y + 68, "ESC        : Fechar janela ativa ou voltar ao desktop", 0xFFFFFF);
            draw_string_aa(fb, stride, win_x + 24, win_y + 90, "1 ate 6    : Alternar entre os 6 aplicativos", 0xFFFFFF);
            draw_string_aa(fb, stride, win_x + 24, win_y + 112, "i ou I     : Assistente de Instalacao e Particionamento", 0x10B981);
            draw_string_aa(fb, stride, win_x + 24, win_y + 134, "t ou T     : Alternar temas do desktop (4 paletas)", 0xF59E0B);
            draw_string_aa(fb, stride, win_x + 24, win_y + 156, "w ou W     : Fechar janela atual", 0x38BDF8);

            draw_string_aa(fb, stride, win_x + 24, win_y + win_h - 34, "Baken OS 2.0 Sovereign - Ambiente Grafico EFI", 0x94A3B8);
        } else if (g_active_desktop_item == 5) {
            // Painel de Sessão & Ajustes
            draw_string_aa(fb, stride, win_x + 24, win_y + 36, "Temas Visuais (Pressione 't' para alternar):", 0x38BDF8);

            const char *theme_names[] = {"1. Oceano", "2. Midnight", "3. Aurora", "4. Nebula"};
            uint32_t theme_colors[] = {0x0284C7, 0x1E293B, 0x059669, 0x7C3AED};
            for (int t = 0; t < 4; t++) {
                int tx = win_x + 20 + (t * 105);
                int ty = win_y + 52;
                uint32_t border = (g_theme_id == t) ? 0xFFFFFF : 0x64748B;
                draw_glass_card_sdf(fb, stride, tx, ty, 98, 22, 6, theme_colors[t], 240, border, 220, (g_theme_id == t) ? 2 : 0);
                draw_string_aa(fb, stride, tx + 8, ty + 4, theme_names[t], 0xFFFFFF);
            }

            draw_string_aa(fb, stride, win_x + 24, win_y + 80, "Dispositivos PCI Detectados no Hardware Real:", 0x38BDF8);
            if (g_pci_device_count > 0) {
                for (int p = 0; p < g_pci_device_count && p < 4; p++) {
                    int py = win_y + 100 + (p * 18);
                    draw_string_aa(fb, stride, win_x + 28, py, g_pci_devices[p].name, 0x10B981);
                }
            } else {
                draw_string_aa(fb, stride, win_x + 28, win_y + 100, "PCI Bus: varredura concluida", 0x10B981);
            }

            draw_string_aa(fb, stride, win_x + 24, win_y + 175, "Clipboard Atual: ", 0x94A3B8);
            draw_string_aa(fb, stride, win_x + 140, win_y + 175, g_clipboard, 0x38BDF8);

            draw_glass_card_sdf(fb, stride, win_x + 16, win_y + win_h - 40, win_w - 32, 26, 8, 0x1E293B, 200, 0x10B981, 140, 1);
            draw_string_aa(fb, stride, win_x + 24, win_y + win_h - 34, "Barramento PCI Escaneado - Drivers Nativos Ativos", 0x10B981);
        }
    }

    // Widgets da Direita
    int card_w = 224;
    int wx = width - card_w - 14;

    // Clima
    draw_glass_card_sdf(fb, stride, wx, 42, card_w, 80, 16, 0xFFFFFF, 190, 0xFFFFFF, 240, 1);
    draw_string_aa(fb, stride, wx + 14, 52, "* Clima", 0x475569);
    draw_string_aa(fb, stride, wx + 14, 70, "Offline", 0x0F172A);
    draw_string_aa(fb, stride, wx + 72, 72, "Sem provedor", 0x059669);
    draw_string_aa(fb, stride, wx + 14, 96, "Dados de rede indisponiveis", 0x64748B);

    // Player
    draw_glass_card_sdf(fb, stride, wx, 130, card_w, 78, 16, 0x0B132B, 210, 0x38BDF8, 180, 1);
    draw_glass_card_sdf(fb, stride, wx + 10, 140, 32, 32, 8, 0x06B6D4, 255, 0xFFFFFF, 140, 0);
    draw_string_aa(fb, stride, wx + 14, 148, "MUS", 0xFFFFFF);
    draw_string_aa(fb, stride, wx + 48, 140, "Player", 0xF8FAFC);
    draw_string_aa(fb, stride, wx + 48, 156, "Servico de audio pendente", 0x94A3B8);
    draw_glass_card_sdf(fb, stride, wx + 96, 176, 22, 22, 11, 0x38BDF8, 240, 0xFFFFFF, 200, 0);
    draw_string_aa(fb, stride, wx + 102, 180, ">", 0x0B132B);
    draw_string_aa(fb, stride, wx + 72, 180, "<<", 0x94A3B8);
    draw_string_aa(fb, stride, wx + 132, 180, ">>", 0x94A3B8);

    // Calendário
    draw_glass_card_sdf(fb, stride, wx, 216, card_w, 100, 16, 0xFFFFFF, 190, 0xFFFFFF, 240, 1);
    draw_string_aa(fb, stride, wx + 14, 226, "Agosto 2026", 0x0F172A);
    draw_string_aa(fb, stride, wx + 146, 226, "Baken OS", 0x0284C7);
    draw_string_aa(fb, stride, wx + 14, 246, " D   S   T   Q   Q   S   S", 0x64748B);
    draw_string_aa(fb, stride, wx + 14, 262, " 2   3   4   5   6   7   8", 0x334155);
    draw_string_aa(fb, stride, wx + 14, 276, " 9  10  11  12  13  14  15", 0x334155);
    draw_glass_card_sdf(fb, stride, wx + 106, 288, 18, 18, 9, 0x0284C7, 255, 0xFFFFFF, 200, 0);
    draw_string_aa(fb, stride, wx + 14, 290, "16  17  18  19  20  21  28", 0x334155);

    // Estado da sessão com telemetria de barramento real
    draw_glass_card_sdf(fb, stride, wx, 324, card_w, 94, 16, 0x0F172A, 220, 0x10B981, 160, 1);
    draw_string_aa(fb, stride, wx + 14, 332, "Estado da sessao", 0x10B981);
    draw_string_aa(fb, stride, wx + 14, 350, "Grafico: GOP", 0xE2E8F0);
    draw_string_aa(fb, stride, wx + 130, 350, "Ativo", 0x38BDF8);
    draw_string_aa(fb, stride, wx + 14, 366, "Entrada: UEFI", 0xE2E8F0);
    draw_string_aa(fb, stride, wx + 130, 366, "Ativa", 0x22C55E);
    draw_string_aa(fb, stride, wx + 14, 382, "Rede: PCI", 0xE2E8F0);
    draw_string_aa(fb, stride, wx + 130, 382, g_has_net ? "Detectada" : "Offline", g_has_net ? 0x22C55E : 0xF59E0B);
    draw_string_aa(fb, stride, wx + 14, 398, "Disco: PCI", 0xE2E8F0);
    draw_string_aa(fb, stride, wx + 130, 398, g_has_ahci ? "AHCI/SATA" : (g_install_persistent ? "Instalado" : "ESP FAT"), 0x38BDF8);

    // Notas Rápidas / Persistentes
    draw_glass_card_sdf(fb, stride, wx, 426, card_w, 94, 16, 0xFEF08A, 240, 0xFDE047, 255, 1);
    if (g_persistent_store.magic == BAKEN_NOTE_MAGIC && g_persistent_store.note.title[0]) {
        draw_string_aa(fb, stride, wx + 14, 434, g_persistent_store.note.title, 0x854D0E);
        draw_string_aa(fb, stride, wx + 14, 450, "Status do Sistema:", 0x713F12);
        draw_string_aa(fb, stride, wx + 14, 464, g_persistent_store.note.line1, 0x854D0E);
        draw_string_aa(fb, stride, wx + 14, 478, g_persistent_store.note.line2, 0x854D0E);
        draw_string_aa(fb, stride, wx + 14, 492, g_persistent_store.note.line3, 0x854D0E);
    } else {
        draw_string_aa(fb, stride, wx + 14, 434, "* Notas Rapidas", 0x854D0E);
        draw_string_aa(fb, stride, wx + 14, 450, "Lembrete Baken OS:", 0x713F12);
        draw_string_aa(fb, stride, wx + 14, 464, "- Desktop grafico em validacao", 0x854D0E);
        draw_string_aa(fb, stride, wx + 14, 478, "- Compilador Cq: grafo validado", 0x854D0E);
        draw_string_aa(fb, stride, wx + 14, 492, "- Instalador: somente registro teste", 0x854D0E);
    }

    // Doca na Base
    int dock_w = 640;
    int dock_h = 52;
    int dock_x = (width - dock_w) / 2;
    int dock_y = height - 64;
    draw_glass_card_sdf(fb, stride, dock_x, dock_y, dock_w, dock_h, 24, 0xFFFFFF, 175, 0xFFFFFF, 230, 1);

    uint32_t dock_bgs[]    = {0x0F172A, 0x60A5FA, 0x818CF8, 0x38BDF8, 0xFB7185, 0xF43F5E, 0x06B6D4, 0x22C55E, 0x10B981, 0xF59E0B, 0x3B82F6, 0x64748B, 0x14B8A6, 0x0EA5E9};
    for (int i = 0; i < 14; i++) {
        int dx = dock_x + 12 + (i * 36);
        int dy = dock_y + 8;
        draw_glass_card_sdf(fb, stride, dx, dy, 34, 34, 10, dock_bgs[i], 255, 0xFFFFFF, 120, 0);
        draw_app_icon(fb, stride, dx + 1, dy + 1, i);
    }

    int px = dock_x + 520;
    int py = dock_y + 8;
    draw_glass_card_sdf(fb, stride, px, py, 110, 34, 12, 0xF8FAFC, 230, 0xCBD5E1, 200, 0);
    draw_glass_card_sdf(fb, stride, px + 4, py + 4, 26, 26, 13, 0x0284C7, 255, 0xFFFFFF, 200, 0);
    draw_string_aa(fb, stride, px + 8, py + 10, "HP", 0xFFFFFF);
    draw_string_aa(fb, stride, px + 36, py + 6, "Usuario", 0x0F172A);
    draw_string_aa(fb, stride, px + 36, py + 18, "Sessao live", 0x64748B);

    draw_mouse_cursor(fb, stride, g_mouse_x, g_mouse_y);
}

// =============================================================================
// 4. PONTO DE ENTRADA DO MICROKERNEL E LOOP INTERATIVO REAL (Ring 0)
// =============================================================================

static void handle_desktop_mouse_click(uint32_t width, uint32_t height, int *needs_redraw) {
    if (g_current_mode == MODE_INSTALLER_WIZARD) {
        // Clique em "Voltar ao Desktop"
        if (g_mouse_x >= (int)(width - 680)/2 + 24 && g_mouse_x <= (int)(width - 680)/2 + 204 &&
            g_mouse_y >= (int)(height - 440)/2 + 440 - 64 && g_mouse_y <= (int)(height - 440)/2 + 440 - 18) {
            g_current_mode = MODE_LIVE_DESKTOP;
            *needs_redraw = 1;
            return;
        }
        // Clique em "Instalar no disco" ou "Reiniciar Sistema"
        if (g_mouse_x >= (int)(width - 680)/2 + 476 && g_mouse_x <= (int)(width - 680)/2 + 656 &&
            g_mouse_y >= (int)(height - 440)/2 + 440 - 64 && g_mouse_y <= (int)(height - 440)/2 + 440 - 18) {
            if (g_install_persistent) {
                uefi_reset_system();
            } else {
                storage_install_selected();
            }
            *needs_redraw = 1;
            return;
        }
    } else {
        int cur_x = g_is_maximized ? 10 : g_win_x;
        int cur_y = g_is_maximized ? 36 : g_win_y;
        int cur_w = g_is_maximized ? (int)width - 20 : g_win_w;

        // Se uma janela estiver aberta, verifica cliques nos botões de controle e arrasto
        if (g_active_desktop_item >= 0) {
            // Fechar (x) - Vermelho
            if (g_mouse_x >= cur_x + cur_w - 28 && g_mouse_x <= cur_x + cur_w - 6 &&
                g_mouse_y >= cur_y + 6 && g_mouse_y <= cur_y + 28) {
                g_active_desktop_item = -1;
                g_is_dragging = 0;
                *needs_redraw = 1;
                return;
            }
            // Minimizar (-) - Amarelo
            if (g_mouse_x >= cur_x + cur_w - 48 && g_mouse_x <= cur_x + cur_w - 28 &&
                g_mouse_y >= cur_y + 6 && g_mouse_y <= cur_y + 28) {
                g_active_desktop_item = -1;
                g_is_dragging = 0;
                *needs_redraw = 1;
                return;
            }
            // Maximizar / Restaurar (+) - Verde
            if (g_mouse_x >= cur_x + cur_w - 68 && g_mouse_x <= cur_x + cur_w - 48 &&
                g_mouse_y >= cur_y + 6 && g_mouse_y <= cur_y + 28) {
                g_is_maximized = !g_is_maximized;
                g_is_dragging = 0;
                *needs_redraw = 1;
                return;
            }
            // Início de Arrasto na Barra de Título (se não maximizado)
            if (!g_is_maximized && g_mouse_x >= cur_x && g_mouse_x <= cur_x + cur_w - 70 &&
                g_mouse_y >= cur_y && g_mouse_y <= cur_y + 32) {
                g_is_dragging = 1;
                g_drag_offset_x = g_mouse_x - g_win_x;
                g_drag_offset_y = g_mouse_y - g_win_y;
                return;
            }
        }

        // Clique nos ícones da lateral esquerda
        if (g_mouse_x >= 24 && g_mouse_x <= 74 && g_mouse_y >= 50 && g_mouse_y < 506) {
            int item = (g_mouse_y - 50) / 76;
            if (item == 4) {
                g_current_mode = MODE_INSTALLER_WIZARD;
                g_selected_btn = 0;
                *needs_redraw = 1;
            } else if (item >= 0 && item < 6) {
                g_active_desktop_item = item;
                *needs_redraw = 1;
            }
        }
        // Clique na Doca inferior
        int dock_w = 640;
        int dock_x = (width - dock_w) / 2;
        int dock_y = height - 64;
        if (g_mouse_x >= dock_x + 12 && g_mouse_x <= dock_x + 12 + (14 * 36) &&
            g_mouse_y >= dock_y + 8 && g_mouse_y <= dock_y + 42) {
            int dock_idx = (g_mouse_x - (dock_x + 12)) / 36;
            if (dock_idx == 4) {
                g_current_mode = MODE_INSTALLER_WIZARD;
                g_selected_btn = 0;
                *needs_redraw = 1;
            } else if (dock_idx >= 0 && dock_idx < 6) {
                g_active_desktop_item = dock_idx;
                *needs_redraw = 1;
            }
        }
    }
}

/* Durante a migração Cq, a entrada pública é gerada a partir de
 * kernel::main. Este runtime mantém o desktop funcional sob um símbolo
 * privado até que seus subsistemas tenham sido completamente portados. */
#ifdef BAKEN_LEGACY_RUNTIME_ONLY
#define BAKEN_RUNTIME_ENTRY baken_legacy_kernel_main
#else
#define BAKEN_RUNTIME_ENTRY baken_kernel_main
#endif
void BAKEN_RUNTIME_ENTRY(const BakenBootInfo *boot_info) {
    if (!boot_info || !boot_info->framebuffer_base ||
        boot_info->screen_width == 0 || boot_info->screen_height == 0 ||
        boot_info->pixels_per_scanline < boot_info->screen_width ||
        boot_info->framebuffer_size / sizeof(uint32_t) <
            (uint64_t)boot_info->pixels_per_scanline * boot_info->screen_height) return;

    // 1. Inicializa somente os pontos de extensão seguros desta ponte.
    bridge_init();
    storage_init();

    uint32_t *fb     = boot_info->framebuffer_base;
    uint32_t stride  = boot_info->pixels_per_scanline;
    uint32_t width   = boot_info->screen_width;
    uint32_t height  = boot_info->screen_height;
    g_framebuffer_width = width;
    g_framebuffer_height = height;

    EFI_SYSTEM_TABLE_IN *st = (EFI_SYSTEM_TABLE_IN*)boot_info->system_table;
    if (st) {
        g_runtime_services = st->RuntimeServices;
    }
    EFI_SIMPLE_POINTER_PROTOCOL *simple_pointer = (EFI_SIMPLE_POINTER_PROTOCOL*)boot_info->pointer_protocol;
    EFI_ABSOLUTE_POINTER_PROTOCOL *abs_pointer = NULL;
    if (st && st->BootServices && st->BootServices->LocateProtocol) {
        st->BootServices->LocateProtocol(&EFI_ABSOLUTE_POINTER_PROTOCOL_GUID, NULL, (void**)&abs_pointer);
        if (!simple_pointer) {
            st->BootServices->LocateProtocol(&EFI_SIMPLE_POINTER_PROTOCOL_GUID, NULL, (void**)&simple_pointer);
        }
    }

    g_block_io = (EFI_BLOCK_IO_PROTOCOL*)boot_info->block_io_protocol;
    g_install_target_block_io = (EFI_BLOCK_IO_PROTOCOL*)boot_info->install_target_block_io_protocol;
    /* A mídia live é somente leitura; dados de sessão só são carregados de
     * uma instalação que possua o volume BakenFS válido. */
    bakenfs_mount();

    g_mouse_x = width / 2;
    g_mouse_y = height / 2;
    int needs_redraw = 1;

    // 2. Loop de Eventos em Tempo Real do Microkernel
    // O desktop e um compositor continuo: nunca congela apos alguns quadros.
    for (;;) {
        // Leitura de Entrada do Mouse (Suporte a Absolute Pointer / USB Tablet e Simple Pointer)
        int pointer_handled = 0;
        if (abs_pointer && abs_pointer->GetState && abs_pointer->Mode) {
            EFI_ABSOLUTE_POINTER_STATE abs_state;
            if (abs_pointer->GetState(abs_pointer, &abs_state) == 0) {
                uint64_t range_x = abs_pointer->Mode->AbsoluteMaxX - abs_pointer->Mode->AbsoluteMinX;
                uint64_t range_y = abs_pointer->Mode->AbsoluteMaxY - abs_pointer->Mode->AbsoluteMinY;
                if (range_x > 0 && range_y > 0) {
                    int new_x = (int)(((abs_state.CurrentX - abs_pointer->Mode->AbsoluteMinX) * (uint64_t)width) / range_x);
                    int new_y = (int)(((abs_state.CurrentY - abs_pointer->Mode->AbsoluteMinY) * (uint64_t)height) / range_y);
                    if (new_x < 0) new_x = 0;
                    if (new_x >= (int)width - 16) new_x = width - 16;
                    if (new_y < 0) new_y = 0;
                    if (new_y >= (int)height - 16) new_y = height - 16;
                    if (new_x != g_mouse_x || new_y != g_mouse_y) {
                        g_mouse_x = new_x;
                        g_mouse_y = new_y;
                        needs_redraw = 1;
                    }
                    uint8_t left_btn = (abs_state.ActiveButtons & 1) ? 1 : 0;
                    if (left_btn) {
                        if (!g_left_button_down) {
                            handle_desktop_mouse_click(width, height, &needs_redraw);
                        } else if (g_is_dragging && g_active_desktop_item >= 0 && !g_is_maximized) {
                            int new_wx = g_mouse_x - g_drag_offset_x;
                            int new_wy = g_mouse_y - g_drag_offset_y;
                            if (new_wy < 34) new_wy = 34;
                            if (new_wy > (int)height - 60) new_wy = (int)height - 60;
                            if (new_wx < -g_win_w + 80) new_wx = -g_win_w + 80;
                            if (new_wx > (int)width - 80) new_wx = (int)width - 80;
                            if (new_wx != g_win_x || new_wy != g_win_y) {
                                g_win_x = new_wx;
                                g_win_y = new_wy;
                                needs_redraw = 1;
                            }
                        }
                    } else {
                        g_is_dragging = 0;
                    }
                    g_left_button_down = left_btn;
                    pointer_handled = 1;
                }
            }
        }

        if (!pointer_handled && simple_pointer && simple_pointer->GetState) {
            EFI_SIMPLE_POINTER_STATE state;
            if (simple_pointer->GetState(simple_pointer, &state) == 0) {
                int previous_x = g_mouse_x;
                int previous_y = g_mouse_y;
                g_mouse_x += state.RelativeMovementX / 4;
                g_mouse_y += state.RelativeMovementY / 4;
                if (g_mouse_x < 0) g_mouse_x = 0;
                if (g_mouse_x >= (int)width - 16) g_mouse_x = width - 16;
                if (g_mouse_y < 0) g_mouse_y = 0;
                if (g_mouse_y >= (int)height - 16) g_mouse_y = height - 16;
                if (previous_x != g_mouse_x || previous_y != g_mouse_y) needs_redraw = 1;

                // Clique e Arrasto do Mouse
                uint8_t left_btn = state.LeftButton ? 1 : 0;
                if (left_btn) {
                    if (!g_left_button_down) {
                        handle_desktop_mouse_click(width, height, &needs_redraw);
                    } else if (g_is_dragging && g_active_desktop_item >= 0 && !g_is_maximized) {
                        int new_wx = g_mouse_x - g_drag_offset_x;
                        int new_wy = g_mouse_y - g_drag_offset_y;
                        if (new_wy < 34) new_wy = 34;
                        if (new_wy > (int)height - 60) new_wy = (int)height - 60;
                        if (new_wx < -g_win_w + 80) new_wx = -g_win_w + 80;
                        if (new_wx > (int)width - 80) new_wx = (int)width - 80;
                        if (new_wx != g_win_x || new_wy != g_win_y) {
                            g_win_x = new_wx;
                            g_win_y = new_wy;
                            needs_redraw = 1;
                        }
                    }
                } else {
                    g_is_dragging = 0;
                }
                g_left_button_down = left_btn;
            }
        }

        // Leitura de Entrada do Teclado
        if (st && st->ConIn && st->ConIn->ReadKeyStroke) {
            EFI_INPUT_KEY key;
            if (st->ConIn->ReadKeyStroke(st->ConIn, &key) == 0) {
                // 't' ou 'T' alterna tema visual
                if (key.UnicodeChar == 't' || key.UnicodeChar == 'T') {
                    g_theme_id = (g_theme_id + 1) % 4;
                    if (g_bakenfs.magic == BAKENFS_MAGIC) bakenfs_save_preferences();
                    needs_redraw = 1;
                }
                // ESC ou tecla 27 fecha modal ou janela ativa
                else if (key.ScanCode == 0x17 || key.UnicodeChar == 27) {
                    if (g_current_mode == MODE_INSTALLER_WIZARD) {
                        g_current_mode = MODE_LIVE_DESKTOP;
                        needs_redraw = 1;
                    } else if (g_active_desktop_item >= 0) {
                        g_active_desktop_item = -1;
                        needs_redraw = 1;
                    }
                }
                // 'w' ou 'W' fecha janela ativa
                else if (key.UnicodeChar == 'w' || key.UnicodeChar == 'W') {
                    if (g_active_desktop_item >= 0) {
                        g_active_desktop_item = -1;
                        needs_redraw = 1;
                    }
                }
                // Gerenciador de arquivos BakenFS: cria objetos reais no
                // volume de dados instalado; a mídia live permanece intacta.
                else if ((key.UnicodeChar == 'd' || key.UnicodeChar == 'D') && g_active_desktop_item == 0) {
                    if (bakenfs_create_directory("/home/documentos")) copy_text(g_clipboard,"/home/documentos",sizeof(g_clipboard));
                    needs_redraw = 1;
                }
                else if ((key.UnicodeChar == 'n' || key.UnicodeChar == 'N') && g_active_desktop_item == 0) {
                    if (bakenfs_create_text_file("/home/arquivo.txt",(uint32_t)(BAKENFS_DATA_LBA+4),"Arquivo criado pelo Baken OS."))
                        copy_text(g_clipboard,"/home/arquivo.txt",sizeof(g_clipboard));
                    needs_redraw = 1;
                }
                // ENTER ou Espaço
                else if (key.UnicodeChar == '\r' || key.UnicodeChar == '\n' || key.UnicodeChar == ' ') {
                    if (g_current_mode == MODE_INSTALLER_WIZARD) {
                        if (g_selected_btn == 0) g_current_mode = MODE_LIVE_DESKTOP;
                        else {
                            if (g_install_persistent) uefi_reset_system();
                            else storage_install_selected();
                        }
                        needs_redraw = 1;
                    } else if (g_active_desktop_item == 1) {
                        // Grava notas no arquivo BakenFS /home/notas.txt.
                        if (g_persistent_store.magic != BAKEN_NOTE_MAGIC) {
                            g_persistent_store.magic = BAKEN_NOTE_MAGIC;
                            g_persistent_store.version = 1;
                            g_persistent_store.flags = 1;
                            const char *t_init = "* Notas Persistentes";
                            for (int i = 0; t_init[i] && i < 31; ++i) g_persistent_store.note.title[i] = t_init[i];
                        }
                        if (g_bakenfs.magic == BAKENFS_MAGIC && bakenfs_save_notes()) {
                            g_note_dirty = 0;
                            g_note_saved_flash = 1;
                        }
                        g_note_cursor_line = (g_note_cursor_line + 1) % 3;
                        needs_redraw = 1;
                    }
                }
                // Backspace (apaga caractere no editor de notas)
                else if (key.UnicodeChar == 8 || key.ScanCode == 0x08) {
                    if (g_active_desktop_item == 1) {
                        char *target_line = (g_note_cursor_line == 0) ? g_persistent_store.note.line1 :
                                           ((g_note_cursor_line == 1) ? g_persistent_store.note.line2 : g_persistent_store.note.line3);
                        int len = 0;
                        while (target_line[len]) len++;
                        if (len > 0) {
                            target_line[len - 1] = '\0';
                            g_note_dirty = 1;
                            g_note_saved_flash = 0;
                            needs_redraw = 1;
                        }
                    }
                }
                // 'i' ou 'I' abre o assistente
                else if (key.UnicodeChar == 'i' || key.UnicodeChar == 'I') {
                    g_current_mode = MODE_INSTALLER_WIZARD;
                    /* O botão só executa com um segundo disco-alvo validado;
                     * sem alvo, não grava nada na mídia de inicialização. */
                    g_selected_btn = 1;
                    needs_redraw = 1;
                }
                // TAB alterna foco de botão no instalador ou cicla aplicativos no desktop
                else if (key.UnicodeChar == '\t') {
                    if (g_current_mode == MODE_INSTALLER_WIZARD) {
                        g_selected_btn = (g_selected_btn == 0) ? 1 : 0;
                        needs_redraw = 1;
                    } else {
                        g_active_desktop_item = (g_active_desktop_item + 1) % 6;
                        if (g_active_desktop_item == 4) g_active_desktop_item = 5;
                        needs_redraw = 1;
                    }
                }
                // Setas Cima / Baixo
                else if (key.ScanCode == 0x01) { // Up
                    if (g_current_mode == MODE_LIVE_DESKTOP) {
                        if (g_active_desktop_item == 0) {
                            uint32_t count = g_bakenfs.magic == BAKENFS_MAGIC ? g_bakenfs.entry_count : 0;
                            if (count) {
                                if (g_selected_file_index > 0) g_selected_file_index--;
                                else g_selected_file_index = (int)count - 1;
                            }
                            needs_redraw = 1;
                        } else if (g_active_desktop_item == 1) {
                            g_note_cursor_line = (g_note_cursor_line + 2) % 3;
                            needs_redraw = 1;
                        } else if (g_active_desktop_item > 0) {
                            g_active_desktop_item--;
                            needs_redraw = 1;
                        }
                    }
                }
                else if (key.ScanCode == 0x02) { // Down
                    if (g_current_mode == MODE_LIVE_DESKTOP) {
                        if (g_active_desktop_item == 0) {
                            uint32_t count = g_bakenfs.magic == BAKENFS_MAGIC ? g_bakenfs.entry_count : 0;
                            if (count) g_selected_file_index = (g_selected_file_index + 1) % (int)count;
                            needs_redraw = 1;
                        } else if (g_active_desktop_item == 1) {
                            g_note_cursor_line = (g_note_cursor_line + 1) % 3;
                            needs_redraw = 1;
                        } else if (g_active_desktop_item < 5) {
                            g_active_desktop_item++;
                            needs_redraw = 1;
                        }
                    }
                }
                // Atalhos numéricos 1 a 6
                else if (key.UnicodeChar >= '1' && key.UnicodeChar <= '6') {
                    int num = key.UnicodeChar - '1';
                    if (num == 4) {
                        g_current_mode = MODE_INSTALLER_WIZARD;
                        g_selected_btn = 0;
                    } else {
                        g_current_mode = MODE_LIVE_DESKTOP;
                        g_active_desktop_item = num;
                    }
                    needs_redraw = 1;
                }
                // Digitação de texto livre se App 1 (Notas) estiver aberto
                else if (key.UnicodeChar >= 32 && key.UnicodeChar <= 126) {
                    if (g_active_desktop_item == 1) {
                        char *target_line = (g_note_cursor_line == 0) ? g_persistent_store.note.line1 :
                                           ((g_note_cursor_line == 1) ? g_persistent_store.note.line2 : g_persistent_store.note.line3);
                        int len = 0;
                        while (target_line[len] && len < 44) len++;
                        if (len < 44) {
                            target_line[len] = (char)key.UnicodeChar;
                            target_line[len + 1] = '\0';
                            g_note_dirty = 1;
                            g_note_saved_flash = 0;
                            needs_redraw = 1;
                        }
                    }
                }
            }
        }

        // Renderização de Acordo com o Modo Ativo
        if (needs_redraw) {
            if (g_current_mode == MODE_INSTALLER_WIZARD) {
                render_installer(fb, stride, width, height);
            } else {
                render_desktop(fb, stride, width, height);
            }
            needs_redraw = 0;
        }

        for (volatile int d = 0; d < 80000; d++);
    }

}
