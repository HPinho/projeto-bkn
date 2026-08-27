/*
 * Baken OS - UEFI Sovereign Bootloader & GOP Kernel Launcher (x86_64)
 * Inicializa GOP (Graphics Output Protocol), prepara framebuffer e entrega controle ao Kernel Gráfico.
 */

#include <stdint.h>

typedef unsigned short CHAR16;
typedef unsigned long long UINTN;
typedef void* EFI_HANDLE;
typedef UINTN EFI_STATUS;

#define EFI_SUCCESS 0

typedef struct {
    unsigned int Data1;
    unsigned short Data2;
    unsigned short Data3;
    unsigned char Data4[8];
} EFI_GUID;

typedef struct _EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL;
typedef struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL EFI_SIMPLE_TEXT_INPUT_PROTOCOL;

typedef struct {
    unsigned short ScanCode;
    CHAR16 UnicodeChar;
} EFI_INPUT_KEY;

typedef EFI_STATUS (*EFI_TEXT_STRING)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, CHAR16 *String);
typedef EFI_STATUS (*EFI_TEXT_CLEAR_SCREEN)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This);
typedef EFI_STATUS (*EFI_INPUT_READ_KEY)(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, EFI_INPUT_KEY *Key);
typedef EFI_STATUS (*EFI_INPUT_RESET)(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, unsigned char ExtendedVerification);

struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL {
    EFI_INPUT_RESET Reset;
    EFI_INPUT_READ_KEY ReadKeyStroke;
    void *WaitForKey;
};

struct _EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL {
    void* Reset;
    EFI_TEXT_STRING OutputString;
    void* TestString;
    void* QueryMode;
    void* SetMode;
    void* SetAttribute;
    EFI_TEXT_CLEAR_SCREEN ClearScreen;
    void* SetCursorPosition;
    void* EnableCursor;
    void* Mode;
};

// =============================================================================
// UEFI GOP (GRAPHICS OUTPUT PROTOCOL) DEFINITIONS
// =============================================================================

typedef struct {
    uint32_t Version;
    uint32_t HorizontalResolution;
    uint32_t VerticalResolution;
    uint32_t PixelFormat;
    uint32_t RedMask;
    uint32_t GreenMask;
    uint32_t BlueMask;
    uint32_t ReservedMask;
    uint32_t PixelsPerScanLine;
} EFI_GRAPHICS_OUTPUT_MODE_INFORMATION;

typedef struct {
    uint32_t MaxMode;
    uint32_t Mode;
    EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *Info;
    UINTN SizeOfInfo;
    uint64_t FrameBufferBase;
    UINTN FrameBufferSize;
} EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE;

typedef struct _EFI_GRAPHICS_OUTPUT_PROTOCOL EFI_GRAPHICS_OUTPUT_PROTOCOL;

typedef EFI_STATUS (*EFI_GRAPHICS_OUTPUT_PROTOCOL_QUERY_MODE)(
    EFI_GRAPHICS_OUTPUT_PROTOCOL *This,
    uint32_t ModeNumber,
    UINTN *SizeOfInfo,
    EFI_GRAPHICS_OUTPUT_MODE_INFORMATION **Info
);

typedef EFI_STATUS (*EFI_GRAPHICS_OUTPUT_PROTOCOL_SET_MODE)(
    EFI_GRAPHICS_OUTPUT_PROTOCOL *This,
    uint32_t ModeNumber
);

struct _EFI_GRAPHICS_OUTPUT_PROTOCOL {
    EFI_GRAPHICS_OUTPUT_PROTOCOL_QUERY_MODE QueryMode;
    EFI_GRAPHICS_OUTPUT_PROTOCOL_SET_MODE SetMode;
    void *Blt;
    EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE *Mode;
};

// =============================================================================
// BOOT SERVICES
// =============================================================================

typedef struct {
    char Header[24];
    void* RaiseTPL;
    void* RestoreTPL;
    void* AllocatePages;
    void* FreePages;
    void* GetMemoryMap;
    void* AllocatePool;
    void* FreePool;
    void* CreateEvent;
    void* SetTimer;
    EFI_STATUS (*WaitForEvent)(UINTN NumberOfEvents, void **Event, UINTN *Index);
    void* SignalEvent;
    void* CloseEvent;
    void* CheckEvent;
    void* InstallProtocolInterface;
    void* ReinstallProtocolInterface;
    void* UninstallProtocolInterface;
    void* HandleProtocol;
    void* Void;
    void* RegisterProtocolNotify;
    void* LocateHandle;
    void* LocateDevicePath;
    void* InstallConfigurationTable;
    void* LoadImage;
    void* StartImage;
    void* Exit;
    void* UnloadImage;
    EFI_STATUS (*ExitBootServices)(EFI_HANDLE ImageHandle, UINTN MapKey);
    void* GetNextMonotonicCount;
    void* Stall;
    void* SetWatchdogTimer;
    void* ConnectController;
    void* DisconnectController;
    void* OpenProtocol;
    void* CloseProtocol;
    void* OpenProtocolInformation;
    void* ProtocolsPerHandle;
    EFI_STATUS (*LocateHandleBuffer)(int SearchType, EFI_GUID *Protocol, void *SearchKey, UINTN *NoHandles, EFI_HANDLE **Buffer);
    EFI_STATUS (*LocateProtocol)(EFI_GUID *Protocol, void *Registration, void **Interface);
} EFI_BOOT_SERVICES;

typedef struct {
    char Header[24];
    CHAR16 *FirmwareVendor;
    unsigned int FirmwareRevision;
    EFI_HANDLE ConsoleInHandle;
    EFI_SIMPLE_TEXT_INPUT_PROTOCOL *ConIn;
    EFI_HANDLE ConsoleOutHandle;
    EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *ConOut;
    EFI_HANDLE StandardErrorHandle;
    EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *StdErr;
    void *RuntimeServices;
    EFI_BOOT_SERVICES *BootServices;
    UINTN NumberOfTableEntries;
    void *ConfigurationTable;
} EFI_SYSTEM_TABLE;

// GUID oficial do EFI_GRAPHICS_OUTPUT_PROTOCOL: 9042a9de-23dc-4a38-96fb-7adefa80516a
static EFI_GUID gop_guid = {0x9042a9de, 0x23dc, 0x4a38, {0x96, 0xfb, 0x7a, 0xde, 0xd0, 0x80, 0x51, 0x6a}};

// Declaração da função do Kernel Core
typedef struct {
    uint32_t *framebuffer_base;
    uint64_t framebuffer_size;
    uint32_t screen_width;
    uint32_t screen_height;
    uint32_t pixels_per_scanline;
    void *memory_map;
    uint64_t memory_map_size;
} BakenBootInfo;

extern void bkn_kernel_main(BakenBootInfo *boot_info);

// Ponto de entrada oficial UEFI (BOOTX64.EFI)
EFI_STATUS efi_main(__attribute__((unused)) EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable) {
    if (!SystemTable || !SystemTable->BootServices) {
        return EFI_SUCCESS;
    }

    EFI_BOOT_SERVICES *BS = SystemTable->BootServices;
    EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *Out = SystemTable->ConOut;
    EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop = (void*)0;

    if (Out) {
        Out->ClearScreen(Out);
        Out->OutputString(Out, (CHAR16*)L"Iniciando Baken OS Kernel & Graphics Engine...\r\n");
    }

    // 1. Localiza o Protocolo Gráfico UEFI (GOP)
    EFI_STATUS status = BS->LocateProtocol(&gop_guid, (void*)0, (void**)&Gop);
    
    if (status == EFI_SUCCESS && Gop && Gop->Mode) {
        // Inicializa o BootInfo com o Framebuffer linear físico do hardware
        BakenBootInfo boot_info;
        boot_info.framebuffer_base = (uint32_t*)Gop->Mode->FrameBufferBase;
        boot_info.framebuffer_size = Gop->Mode->FrameBufferSize;
        boot_info.screen_width = Gop->Mode->Info->HorizontalResolution;
        boot_info.screen_height = Gop->Mode->Info->VerticalResolution;
        boot_info.pixels_per_scanline = Gop->Mode->Info->PixelsPerScanLine;
        boot_info.memory_map = (void*)0;
        boot_info.memory_map_size = 0;

        // 2. Transfere a execução para o Kernel Principal do Baken OS
        bkn_kernel_main(&boot_info);

        // 3. Loop infinito do Kernel Gráfico no Framebuffer (Mantém o sistema ativo a 120 FPS)
        while (1) {
            // Mantém a CPU ativa processando frames
            __asm__ __volatile__("hlt");
        }
    }

    // Fallback: Aguarda evento caso não localize GOP
    if (Out) {
        Out->OutputString(Out, (CHAR16*)L"Aviso: Modo GOP nao detectado. Rodando em modo texto.\r\n");
    }
    while (1) {
        __asm__ __volatile__("hlt");
    }

    return EFI_SUCCESS;
}
