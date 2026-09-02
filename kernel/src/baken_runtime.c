/* Adaptador UEFI de entrada, tempo e assets.
 *
 * Este arquivo não desenha interface. Ele traduz eventos do firmware para as
 * APIs públicas do shell Sotlas e mantém o relógio de quadros próximo de 60 Hz.
 */
#include <stdint.h>
#include <stddef.h>
#include "../include/baken_boot_info.h"
#include "../include/font_google_sans_flex_atlas.h"
#include "../include/baken_logo_atlas.h"

typedef struct {
    int32_t RelativeMovementX, RelativeMovementY, RelativeMovementZ;
    uint8_t LeftButton, RightButton;
} EfiSimplePointerState;

typedef struct EfiSimplePointer {
    uint64_t (*Reset)(struct EfiSimplePointer *, uint8_t);
    uint64_t (*GetState)(struct EfiSimplePointer *, EfiSimplePointerState *);
    void *WaitForInput;
    void *Mode;
} EfiSimplePointer;

typedef struct {
    uint64_t CurrentX, CurrentY, CurrentZ;
    uint32_t ActiveButtons;
} EfiAbsolutePointerState;

typedef struct {
    uint64_t AbsoluteMinX, AbsoluteMinY, AbsoluteMinZ;
    uint64_t AbsoluteMaxX, AbsoluteMaxY, AbsoluteMaxZ;
    uint32_t Attributes;
} EfiAbsolutePointerMode;

typedef struct EfiAbsolutePointer {
    uint64_t (*Reset)(struct EfiAbsolutePointer *, uint8_t);
    uint64_t (*GetState)(struct EfiAbsolutePointer *, EfiAbsolutePointerState *);
    void *WaitForInput;
    EfiAbsolutePointerMode *Mode;
} EfiAbsolutePointer;

typedef struct {
    uint32_t Data1;
    uint16_t Data2, Data3;
    uint8_t Data4[8];
} EfiGuid;

static const EfiGuid EFI_SIMPLE_POINTER_PROTOCOL_GUID = {
    0x31878c87, 0x0b75, 0x11d5, {0x9a, 0x4f, 0x00, 0x90, 0x27, 0x3f, 0xc1, 0x4d}
};
static const EfiGuid EFI_ABSOLUTE_POINTER_PROTOCOL_GUID = {
    0x8d59d32b, 0xc655, 0x4ae9, {0x9b, 0x15, 0xf2, 0x59, 0x04, 0x99, 0x2a, 0x43}
};

typedef struct { uint16_t ScanCode, UnicodeChar; } EfiInputKey;
typedef struct EfiTextInput {
    uint64_t (*Reset)(struct EfiTextInput *, uint8_t);
    uint64_t (*ReadKeyStroke)(struct EfiTextInput *, EfiInputKey *);
    void *WaitForKey;
} EfiTextInput;

typedef struct {
    uint8_t Hdr[24];
    void *RaiseTPL, *RestoreTPL, *AllocatePages, *FreePages, *GetMemoryMap;
    void *AllocatePool, *FreePool, *CreateEvent, *SetTimer, *WaitForEvent;
    void *SignalEvent, *CloseEvent, *CheckEvent, *InstallProtocolInterface;
    void *ReinstallProtocolInterface, *UninstallProtocolInterface, *HandleProtocol;
    void *Reserved, *RegisterProtocolNotify, *LocateHandle, *LocateDevicePath;
    void *InstallConfigurationTable, *LoadImage, *StartImage, *Exit, *UnloadImage;
    void *ExitBootServices, *GetNextMonotonicCount;
    uint64_t (*Stall)(uint64_t);
    void *SetWatchdogTimer, *ConnectController, *DisconnectController;
    void *OpenProtocol, *CloseProtocol, *OpenProtocolInformation;
    void *ProtocolsPerHandle, *LocateHandleBuffer;
    uint64_t (*LocateProtocol)(const EfiGuid *, void *, void **);
} EfiBootServicesPrefix;

typedef struct {
    uint8_t Hdr[24];
    void *FirmwareVendor;
    uint32_t FirmwareRevision;
    void *ConsoleInHandle;
    EfiTextInput *ConIn;
    void *ConsoleOutHandle, *ConOut, *StandardErrorHandle, *StdErr;
    void *RuntimeServices;
    EfiBootServicesPrefix *BootServices;
} EfiSystemTablePrefix;

extern uint8_t gfx_bind_font_atlas(const uint8_t *, const uint8_t *, uint32_t, uint32_t, uint32_t);
extern uint8_t gfx_bind_logo_atlas(const uint32_t *, uint32_t);
extern void desktop_shell_set_frame_delta(float);
extern void desktop_shell_set_cursor(int32_t, int32_t);
extern void desktop_shell_handle_click(int32_t, int32_t);
extern void desktop_compositor_render_frame(void);
extern uint8_t wm_handle_mouse_down(int32_t, int32_t);
extern void wm_handle_mouse_move(int32_t, int32_t);
extern void wm_handle_mouse_up(void);
extern void baken_installer_handle_key(uint32_t);

static uint64_t read_tsc(void) {
#if defined(__x86_64__) || defined(__i386__)
    uint32_t low, high;
    __asm__ volatile ("rdtsc" : "=a"(low), "=d"(high));
    return ((uint64_t)high << 32) | low;
#else
    return 0;
#endif
}

void baken_runtime_init_assets(void) {
    const SotlasFontAtlas *font = &sotlas_font_atlases[0];
    gfx_bind_font_atlas(font->advances, font->alpha, font->width, font->height, font->px);
    gfx_bind_logo_atlas(g_baken_logo_atlases[0].pixels, g_baken_logo_atlases[0].size);
}

void baken_runtime_run(const void *opaque_boot_info, uint32_t width, uint32_t height) {
    const BakenBootInfo *boot_info = (const BakenBootInfo *)opaque_boot_info;
    EfiSystemTablePrefix *system_table = boot_info ? (EfiSystemTablePrefix *)boot_info->system_table : NULL;
    EfiTextInput *keyboard = system_table ? system_table->ConIn : NULL;
    EfiSimplePointer *pointer = boot_info ? (EfiSimplePointer *)boot_info->pointer_protocol : NULL;
    EfiAbsolutePointer *absolute_pointer = NULL;
    EfiBootServicesPrefix *boot_services = system_table ? system_table->BootServices : NULL;
    uint64_t (*stall)(uint64_t) = system_table && system_table->BootServices
        ? system_table->BootServices->Stall : NULL;
    int32_t mouse_x = (int32_t)(width / 2), mouse_y = (int32_t)(height / 2);
    uint8_t left_down = 0;
    uint64_t cycles_per_us = 0;

    /* O handoff prefere Simple Pointer para permitir um fallback tipado. Quando
     * LocateProtocol esta disponivel, descobrimos ambos sem tentar adivinhar o
     * tipo pela disposicao interna dos protocolos UEFI. */
    if (boot_services && boot_services->LocateProtocol) {
        void *located = NULL;
        if (boot_services->LocateProtocol(&EFI_SIMPLE_POINTER_PROTOCOL_GUID, NULL, &located) == 0 && located)
            pointer = (EfiSimplePointer *)located;
        located = NULL;
        if (boot_services->LocateProtocol(&EFI_ABSOLUTE_POINTER_PROTOCOL_GUID, NULL, &located) == 0 && located)
            absolute_pointer = (EfiAbsolutePointer *)located;
    }

    if (stall) {
        uint64_t start = read_tsc();
        stall(10000);
        uint64_t end = read_tsc();
        if (end > start) cycles_per_us = (end - start) / 10000;
    }

    for (;;) {
        uint64_t frame_start = read_tsc();
        if (keyboard && keyboard->ReadKeyStroke) {
            EfiInputKey key;
            while (keyboard->ReadKeyStroke(keyboard, &key) == 0) {
                baken_installer_handle_key(key.UnicodeChar ? key.UnicodeChar : key.ScanCode);
            }
        }
        if (absolute_pointer && absolute_pointer->GetState && absolute_pointer->Mode) {
            EfiAbsolutePointerState state;
            EfiAbsolutePointerMode *mode = absolute_pointer->Mode;
            if (absolute_pointer->GetState(absolute_pointer, &state) == 0) {
                uint64_t range_x = mode->AbsoluteMaxX - mode->AbsoluteMinX;
                uint64_t range_y = mode->AbsoluteMaxY - mode->AbsoluteMinY;
                if (range_x && range_y) {
                    uint64_t raw_x = state.CurrentX > mode->AbsoluteMinX ? state.CurrentX - mode->AbsoluteMinX : 0;
                    uint64_t raw_y = state.CurrentY > mode->AbsoluteMinY ? state.CurrentY - mode->AbsoluteMinY : 0;
                    if (raw_x > range_x) raw_x = range_x;
                    if (raw_y > range_y) raw_y = range_y;
                    mouse_x = (int32_t)((raw_x * (width - 1)) / range_x);
                    mouse_y = (int32_t)((raw_y * (height - 1)) / range_y);
                }
                desktop_shell_set_cursor(mouse_x, mouse_y);
                uint8_t pressed = (state.ActiveButtons & 1U) ? 1 : 0;
                if (pressed && !left_down) {
                    if (!wm_handle_mouse_down(mouse_x, mouse_y)) desktop_shell_handle_click(mouse_x, mouse_y);
                } else if (pressed) {
                    wm_handle_mouse_move(mouse_x, mouse_y);
                } else if (left_down) {
                    wm_handle_mouse_up();
                }
                left_down = pressed;
            }
        } else if (pointer && pointer->GetState) {
            EfiSimplePointerState state;
            if (pointer->GetState(pointer, &state) == 0) {
                int32_t dx = state.RelativeMovementX / 16;
                int32_t dy = state.RelativeMovementY / 16;
                if (!dx && state.RelativeMovementX) dx = state.RelativeMovementX > 0 ? 1 : -1;
                if (!dy && state.RelativeMovementY) dy = state.RelativeMovementY > 0 ? 1 : -1;
                mouse_x += dx; mouse_y += dy;
                if (mouse_x < 0) mouse_x = 0;
                if (mouse_y < 0) mouse_y = 0;
                if (mouse_x >= (int32_t)width) mouse_x = (int32_t)width - 1;
                if (mouse_y >= (int32_t)height) mouse_y = (int32_t)height - 1;
                desktop_shell_set_cursor(mouse_x, mouse_y);
                if (state.LeftButton && !left_down) {
                    if (!wm_handle_mouse_down(mouse_x, mouse_y)) desktop_shell_handle_click(mouse_x, mouse_y);
                } else if (state.LeftButton) {
                    wm_handle_mouse_move(mouse_x, mouse_y);
                } else if (left_down) {
                    wm_handle_mouse_up();
                }
                left_down = state.LeftButton ? 1 : 0;
            }
        }

        desktop_compositor_render_frame();
        uint64_t frame_end = read_tsc();
        float dt = 1.0f / 60.0f;
        if (stall && cycles_per_us && frame_end > frame_start) {
            uint64_t work_us = (frame_end - frame_start) / cycles_per_us;
            if (work_us < 16667) stall(16667 - work_us);
            frame_end = read_tsc();
            dt = (float)((frame_end - frame_start) / cycles_per_us) / 1000000.0f;
        }
        desktop_shell_set_frame_delta(dt);
    }
}
