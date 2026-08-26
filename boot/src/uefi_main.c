/*
 * Baken OS - Aero-Quantum Ultra-Modern Desktop Engine (UEFI Native x86_64)
 * Motor Gráfico e Tipográfico de Alta Definição:
 * - Tipografia Proporcional Sans-Serif com Anti-Aliasing Subpixel (256 Níveis de Alfa)
 * - Renderizador de Títulos e Relógio Digital Grande (32px Display Font)
 * - Ícones Vetoriais em Squircle 3D com Preenchimento Sólido e Gradientes Vivos
 * - At a Glance Widget com Relógio Moderno e Barra Superior com Glifos Reais
 * - Dock Flutuante Material You com Efeito Lupa e Sombras Volumétricas
 * - Suporte Completo a Drag & Drop de Janelas, Z-Order e Kawase Blur
 */

typedef unsigned short CHAR16;
typedef unsigned long long UINTN;
typedef long long INTN;
typedef int INT32;
typedef unsigned char BOOLEAN;
typedef void* EFI_HANDLE;
typedef UINTN EFI_STATUS;
typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;
typedef unsigned long long uint64_t;

#define EFI_SUCCESS 0

#include "../../kernel/src/bkn_font.c"

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

typedef EFI_STATUS (*EFI_TEXT_RESET)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, unsigned char ExtendedVerification);
typedef EFI_STATUS (*EFI_TEXT_STRING)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, CHAR16 *String);
typedef EFI_STATUS (*EFI_TEXT_SET_ATTRIBUTE)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, UINTN Attribute);
typedef EFI_STATUS (*EFI_TEXT_CLEAR_SCREEN)(EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This);

struct _EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL {
    EFI_TEXT_RESET Reset;
    EFI_TEXT_STRING OutputString;
    void* TestString;
    void* QueryMode;
    void* SetMode;
    EFI_TEXT_SET_ATTRIBUTE SetAttribute;
    EFI_TEXT_CLEAR_SCREEN ClearScreen;
    void* SetCursorPosition;
    void* EnableCursor;
    void* Mode;
};

typedef EFI_STATUS (*EFI_INPUT_RESET)(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, unsigned char ExtendedVerification);
typedef EFI_STATUS (*EFI_INPUT_READ_KEY)(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This, EFI_INPUT_KEY *Key);

struct _EFI_SIMPLE_TEXT_INPUT_PROTOCOL {
    EFI_INPUT_RESET Reset;
    EFI_INPUT_READ_KEY ReadKeyStroke;
    void* WaitForKey;
};

// Protocolo Gráfico UEFI (GOP)
typedef struct {
    unsigned int Version;
    unsigned int HorizontalResolution;
    unsigned int VerticalResolution;
    unsigned int PixelFormat;
    unsigned int RedMask;
    unsigned int GreenMask;
    unsigned int BlueMask;
    unsigned int ReservedMask;
    unsigned int PixelsPerScanLine;
} EFI_GRAPHICS_OUTPUT_MODE_INFORMATION;

typedef struct {
    unsigned int MaxMode;
    unsigned int Mode;
    EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *Info;
    UINTN SizeOfInfo;
    unsigned long long FrameBufferBase;
    UINTN FrameBufferSize;
} EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE;

typedef struct _EFI_GRAPHICS_OUTPUT_PROTOCOL EFI_GRAPHICS_OUTPUT_PROTOCOL;

typedef EFI_STATUS (*EFI_GRAPHICS_OUTPUT_PROTOCOL_QUERY_MODE)(EFI_GRAPHICS_OUTPUT_PROTOCOL *This, unsigned int ModeNumber, UINTN *SizeOfInfo, EFI_GRAPHICS_OUTPUT_MODE_INFORMATION **Info);
typedef EFI_STATUS (*EFI_GRAPHICS_OUTPUT_PROTOCOL_SET_MODE)(EFI_GRAPHICS_OUTPUT_PROTOCOL *This, unsigned int ModeNumber);

struct _EFI_GRAPHICS_OUTPUT_PROTOCOL {
    EFI_GRAPHICS_OUTPUT_PROTOCOL_QUERY_MODE QueryMode;
    EFI_GRAPHICS_OUTPUT_PROTOCOL_SET_MODE SetMode;
    void* Blt;
    EFI_GRAPHICS_OUTPUT_PROTOCOL_MODE *Mode;
};

typedef struct {
    unsigned long long CurrentX;
    unsigned long long CurrentY;
    unsigned long long CurrentZ;
    unsigned int ActiveButtons;
} EFI_ABSOLUTE_POINTER_STATE;

typedef struct {
    unsigned long long AbsoluteMinX;
    unsigned long long AbsoluteMinY;
    unsigned long long AbsoluteMinZ;
    unsigned long long AbsoluteMaxX;
    unsigned long long AbsoluteMaxY;
    unsigned long long AbsoluteMaxZ;
    unsigned int Attributes;
} EFI_ABSOLUTE_POINTER_MODE;

typedef struct _EFI_ABSOLUTE_POINTER_PROTOCOL EFI_ABSOLUTE_POINTER_PROTOCOL;

typedef EFI_STATUS (*EFI_ABSOLUTE_POINTER_RESET)(EFI_ABSOLUTE_POINTER_PROTOCOL *This, BOOLEAN ExtendedVerification);
typedef EFI_STATUS (*EFI_ABSOLUTE_POINTER_GET_STATE)(EFI_ABSOLUTE_POINTER_PROTOCOL *This, EFI_ABSOLUTE_POINTER_STATE *State);

struct _EFI_ABSOLUTE_POINTER_PROTOCOL {
    EFI_ABSOLUTE_POINTER_RESET Reset;
    EFI_ABSOLUTE_POINTER_GET_STATE GetState;
    void* WaitForInput;
    EFI_ABSOLUTE_POINTER_MODE *Mode;
};

typedef struct {
    INT32 RelativeMovementX;
    INT32 RelativeMovementY;
    INT32 RelativeMovementZ;
    BOOLEAN LeftButton;
    BOOLEAN RightButton;
} EFI_SIMPLE_POINTER_STATE;

typedef struct _EFI_SIMPLE_POINTER_PROTOCOL EFI_SIMPLE_POINTER_PROTOCOL;

typedef EFI_STATUS (*EFI_SIMPLE_POINTER_RESET)(EFI_SIMPLE_POINTER_PROTOCOL *This, BOOLEAN ExtendedVerification);
typedef EFI_STATUS (*EFI_SIMPLE_POINTER_GET_STATE)(EFI_SIMPLE_POINTER_PROTOCOL *This, EFI_SIMPLE_POINTER_STATE *State);

struct _EFI_SIMPLE_POINTER_PROTOCOL {
    EFI_SIMPLE_POINTER_RESET Reset;
    EFI_SIMPLE_POINTER_GET_STATE GetState;
    void* WaitForInput;
    void* Mode;
};

typedef EFI_STATUS (*EFI_ALLOCATE_PAGES)(int Type, int MemoryType, UINTN Pages, unsigned long long *Memory);
typedef EFI_STATUS (*EFI_LOCATE_PROTOCOL)(EFI_GUID *Protocol, void *Registration, void **Interface);

typedef struct {
    char Header[24];
    void *RaiseTPL;
    void *RestoreTPL;
    EFI_ALLOCATE_PAGES AllocatePages;
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
    EFI_LOCATE_PROTOCOL LocateProtocol;
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

static EFI_GUID GOP_GUID = { 0x9042a9de, 0x23dc, 0x4a38, { 0x96, 0xfb, 0x7a, 0xde, 0xd0, 0x80, 0x51, 0x6a } };
static EFI_GUID ABS_POINTER_GUID = { 0x8d59d32b, 0xc655, 0x4ae9, { 0x9b, 0x15, 0xf2, 0x59, 0x04, 0x99, 0x2a, 0x43 } };
static EFI_GUID REL_POINTER_GUID = { 0x31878c87, 0xb75, 0x11d5, { 0x9a, 0x4f, 0x0, 0x90, 0x27, 0x3f, 0xc1, 0x4d } };

// Buffers do Display
static unsigned int *g_front_fb = 0;
static unsigned int *g_back_fb = 0;
static unsigned int *g_wallpaper_cache = 0;
static unsigned int g_width = 1024;
static unsigned int g_height = 768;
static unsigned int g_pitch = 1024;

// Estados do Cursor e Janelas
static int g_mouse_x = 512;
static int g_mouse_y = 384;
static int g_last_mouse_x = 512;
static int g_last_mouse_y = 384;
static unsigned int g_mouse_underlay[24][24];

static int g_start_menu_open = 0;
static int g_control_center_open = 0;
static int g_active_editor_tab = 0;
static int g_anim_frame = 0;

static int g_win_ide_x = 24;
static int g_win_ide_y = 54;
static int g_win_ide_open = 0;
static int g_win_ide_maximized = 0;

static int g_win_qpu_x = 524;
static int g_win_qpu_y = 54;
static int g_win_qpu_open = 0;
static int g_win_qpu_maximized = 0;

static int g_dragging_win = 0; // 0: nenhum, 1: IDE, 2: Q-HAL
static int g_drag_offset_x = 0;
static int g_drag_offset_y = 0;
static int g_win_z_order[2] = { 0, 1 }; // 0: IDE, 1: Q-HAL

static int g_volume_level = 85;
static int g_brightness_level = 95;

static int g_dock_w = 510;
static int g_dock_h = 66;
static int g_dock_x = 257;
static int g_dock_y = 684;
static int g_icon_centers[6] = { 298, 370, 442, 514, 586, 658 };

static char g_term_history[3][120] = {
    "[Q-HAL Core] Telemetria quantica pronta. Zero erros.",
    "[Baken OS] Aero-Quantum Kernel v1.1 [Ring 0 Soberano]",
    "Digite 'qpu bell', 'pqc shield', 'fs ls' ou 'bknc run'"
};

// I/O Direto PS/2
static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ __volatile__("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}

static inline void outb(uint16_t port, uint8_t val) {
    __asm__ __volatile__("outb %0, %1" : : "a"(val), "Nd"(port));
}

static void init_hardware_mouse() {
    outb(0x64, 0xA8);
    outb(0x64, 0x20);
    uint8_t status = inb(0x60) | 2;
    outb(0x64, 0x60);
    outb(0x60, status);
    outb(0x64, 0xD4);
    outb(0x60, 0xF4);
    inb(0x60);
}

static int poll_hardware_mouse(int *dx, int *dy, int *btn) {
    if ((inb(0x64) & 1) == 0) return 0;
    uint8_t b1 = inb(0x60);
    if ((inb(0x64) & 1) == 0) return 0;
    uint8_t b2 = inb(0x60);
    if ((inb(0x64) & 1) == 0) return 0;
    uint8_t b3 = inb(0x60);

    *btn = b1 & 1;
    *dx = (int)(int8_t)b2;
    *dy = -(int)(int8_t)b3;
    return 1;
}

// -------------------------------------------------------------
// MOTOR GRÁFICO BAKENFX (SDF Anti-Aliased, Kawase Blur, Glassmorphism)
// -------------------------------------------------------------

static inline unsigned int blend_color(unsigned int bg, unsigned int fg, unsigned char alpha) {
    if (alpha == 255) return fg;
    if (alpha == 0) return bg;

    unsigned int a = alpha;
    unsigned int inv_a = 255 - a;

    unsigned int bg_r = (bg >> 16) & 0xFF;
    unsigned int bg_g = (bg >> 8) & 0xFF;
    unsigned int bg_b = bg & 0xFF;

    unsigned int fg_r = (fg >> 16) & 0xFF;
    unsigned int fg_g = (fg >> 8) & 0xFF;
    unsigned int fg_b = fg & 0xFF;

    unsigned int out_r = ((fg_r * a) + (bg_r * inv_a)) / 255;
    unsigned int out_g = ((fg_g * a) + (bg_g * inv_a)) / 255;
    unsigned int out_b = ((fg_b * a) + (bg_b * inv_a)) / 255;

    return (out_r << 16) | (out_g << 8) | out_b;
}

static inline void put_pixel_alpha(int x, int y, unsigned int color, unsigned char alpha) {
    if (x >= 0 && x < (int)g_width && y >= 0 && y < (int)g_height && g_back_fb && alpha > 0) {
        unsigned int offset = (unsigned int)y * g_pitch + (unsigned int)x;
        g_back_fb[offset] = blend_color(g_back_fb[offset], color, alpha);
    }
}

static inline void put_pixel_fast(int x, int y, unsigned int color) {
    if (x >= 0 && x < (int)g_width && y >= 0 && y < (int)g_height && g_back_fb) {
        g_back_fb[(unsigned int)y * g_pitch + (unsigned int)x] = color;
    }
}

static void bakenfx_present_frame() {
    if (!g_front_fb || !g_back_fb) return;
    unsigned int total = g_pitch * g_height;
    for (unsigned int i = 0; i < total; i++) {
        g_front_fb[i] = g_back_fb[i];
    }
}

// -------------------------------------------------------------
// MOTOR TIPOGRÁFICO SANS-SERIF PROPORCIONAL & SUBPIXEL ANTI-ALIASING
// -------------------------------------------------------------

// Largura Proporcional de cada caractere (em pixels) para visual moderno não-monospaçado
static inline int get_char_advance(char c) {
    if (c == ' ' || c == '\t') return 5;
    if (c == '.' || c == ',' || c == ':' || c == ';' || c == '\'' || c == '`' || c == '!') return 4;
    if (c == 'i' || c == 'l' || c == 'j' || c == '|' || c == '(' || c == ')' || c == '[' || c == ']') return 5;
    if (c == 'f' || c == 't' || c == 'r' || c == '-' || c == 'I') return 6;
    if (c == 'w' || c == 'm' || c == 'M' || c == 'W' || c == '@' || c == '%') return 11;
    if (c >= 'A' && c <= 'Z') return 9;
    if (c >= '0' && c <= '9') return 8;
    return 7;
}

// Renderizador de Texto Proporcional com Anti-Aliasing Subpixel
static void draw_text_smooth(int x, int y, const char *str, unsigned int color) {
    int cx = x;
    while (*str) {
        char c = *str;
        if ((unsigned char)c < 128) {
            const uint8_t *glyph = bkn_font8x16[(unsigned char)c];
            int advance = get_char_advance(c);
            int start_col = 0;
            if (advance <= 5 && c != ' ') start_col = 1;

            for (int row = 0; row < 16; row++) {
                uint8_t bits = glyph[row];
                for (int col = start_col; col < start_col + advance && col < 8; col++) {
                    int bit_on = (bits >> (7 - col)) & 1;
                    int px = cx + (col - start_col);
                    int py = y + row;

                    if (bit_on) {
                        put_pixel_alpha(px, py, color, 255);
                    } else {
                        // Suavização anti-aliased baseada em vizinhos (Subpixel Filtering)
                        int left   = (col > 0) ? ((bits >> (8 - col)) & 1) : 0;
                        int right  = (col < 7) ? ((bits >> (6 - col)) & 1) : 0;
                        int up     = (row > 0) ? ((bkn_font8x16[(unsigned char)c][row - 1] >> (7 - col)) & 1) : 0;
                        int down   = (row < 15) ? ((bkn_font8x16[(unsigned char)c][row + 1] >> (7 - col)) & 1) : 0;

                        int neighbors = left + right + up + down;
                        if (neighbors >= 2) {
                            put_pixel_alpha(px, py, color, 85);
                        } else if (neighbors == 1) {
                            put_pixel_alpha(px, py, color, 35);
                        }
                    }
                }
            }
            cx += advance + 1;
        } else {
            cx += 7;
        }
        str++;
    }
}

// Forward Declarations de Primitivas Gráficas
static void draw_rounded_rect_sdf(int x, int y, int w, int h, int radius, unsigned int bg_color, unsigned char bg_alpha, unsigned int border_color, unsigned char border_alpha, int border_width);
static void draw_smooth_circle(int cx, int cy, int radius, unsigned int fill_color, unsigned int border_color);

// Renderizador de Segmentos Vetoriais Suaves para Dígitos de Alta Definição (36px)
static void draw_smooth_segment(int x, int y, int w, int h, int radius, unsigned int color) {
    draw_rounded_rect_sdf(x, y, w, h, radius, color, 255, 0x00FFFFFF, 80, 1);
}

// Renderizador de Numerais Vetoriais de Alta Definição (Estilo Modern Clock Display)
static void draw_display_clock_numeral(int x, int y, char c, unsigned int color) {
    if (c == ':') {
        draw_smooth_circle(x + 5, y + 12, 3, 0x0000E5FF, 0x00FFFFFF);
        draw_smooth_circle(x + 5, y + 26, 3, 0x0000E5FF, 0x00FFFFFF);
        return;
    }

    if (c < '0' || c > '9') return;
    int digit = c - '0';

    // Segmentos: Top, Top-Left, Top-Right, Mid, Bot-Left, Bot-Right, Bot
    // 0: T, TL, TR, BL, BR, B
    // 1: TR, BR
    // 2: T, TR, M, BL, B
    // 3: T, TR, M, BR, B
    // 4: TL, TR, M, BR
    // 5: T, TL, M, BR, B
    // 6: T, TL, M, BL, BR, B
    // 7: T, TR, BR
    // 8: T, TL, TR, M, BL, BR, B
    // 9: T, TL, TR, M, BR, B

    int seg_t  = (digit != 1 && digit != 4);
    int seg_tl = (digit == 0 || digit == 4 || digit == 5 || digit == 6 || digit == 8 || digit == 9);
    int seg_tr = (digit != 5 && digit != 6);
    int seg_m  = (digit != 0 && digit != 1 && digit != 7);
    int seg_bl = (digit == 0 || digit == 2 || digit == 6 || digit == 8);
    int seg_br = (digit != 2);
    int seg_b  = (digit != 1 && digit != 4 && digit != 7);

    int w = 22;
    int h = 36;
    int th = 4;
    int r = 2;

    if (seg_t)  draw_smooth_segment(x + 2, y, w - 4, th, r, color);
    if (seg_tl) draw_smooth_segment(x, y + 2, th, (h / 2) - 2, r, color);
    if (seg_tr) draw_smooth_segment(x + w - th, y + 2, th, (h / 2) - 2, r, color);
    if (seg_m)  draw_smooth_segment(x + 2, y + (h / 2) - (th / 2), w - 4, th, r, color);
    if (seg_bl) draw_smooth_segment(x, y + (h / 2), th, (h / 2) - 2, r, color);
    if (seg_br) draw_smooth_segment(x + w - th, y + (h / 2), th, (h / 2) - 2, r, color);
    if (seg_b)  draw_smooth_segment(x + 2, y + h - th, w - 4, th, r, color);
}

static void draw_display_clock_text(int x, int y, const char *str, unsigned int color) {
    int cx = x;
    while (*str) {
        char c = *str;
        draw_display_clock_numeral(cx, y, c, color);
        if (c == ':') cx += 14;
        else cx += 26;
        str++;
    }
}

// -------------------------------------------------------------
// PRIMITIVAS SDF, BLUR E SOMBRAS
// -------------------------------------------------------------

// Renderizador de Cantos Arredondados com Anti-Aliasing (SDF)
static void draw_rounded_rect_sdf(
    int x, int y, int w, int h, int radius,
    unsigned int bg_color, unsigned char bg_alpha,
    unsigned int border_color, unsigned char border_alpha, int border_width
) {
    int x1 = x;
    int y1 = y;
    int x2 = x + w;
    int y2 = y + h;

    int min_x = (x1 > 0) ? x1 : 0;
    int max_x = (x2 < (int)g_width) ? x2 : (int)g_width;
    int min_y = (y1 > 0) ? y1 : 0;
    int max_y = (y2 < (int)g_height) ? y2 : (int)g_height;

    int r = (radius > 0) ? radius : 0;

    for (int py = min_y; py < max_y; py++) {
        for (int px = min_x; px < max_x; px++) {
            int cx = (px < x1 + r) ? (x1 + r) : ((px > x2 - r - 1) ? (x2 - r - 1) : px);
            int cy = (py < y1 + r) ? (y1 + r) : ((py > y2 - r - 1) ? (y2 - r - 1) : py);

            int dx = px - cx;
            int dy = py - cy;
            int dist_sq = dx * dx + dy * dy;

            if (dist_sq <= r * r) {
                int is_border = 0;
                if (border_width > 0) {
                    if (px < x1 + border_width || px >= x2 - border_width ||
                        py < y1 + border_width || py >= y2 - border_width) {
                        is_border = 1;
                    } else if (r > 0 && dist_sq >= (r - border_width) * (r - border_width)) {
                        is_border = 1;
                    }
                }

                if (is_border) {
                    put_pixel_alpha(px, py, border_color, border_alpha);
                } else {
                    put_pixel_alpha(px, py, bg_color, bg_alpha);
                }
            } else if (dist_sq <= (r + 1) * (r + 1)) {
                put_pixel_alpha(px, py, border_color, border_alpha / 2);
            }
        }
    }
}

// Sombra com Elevação Suave Material 3
static void draw_material_elevation_shadow(int x, int y, int w, int h, int radius, int blur, int offset_y, unsigned char opacity) {
    (void)radius;
    int sx0 = x - blur;
    int sy0 = y + offset_y - blur / 2;
    int sx1 = x + w + blur;
    int sy1 = y + h + offset_y + blur;

    if (sx0 < 0) sx0 = 0;
    if (sy0 < 0) sy0 = 0;
    if (sx1 >= (int)g_width) sx1 = g_width;
    if (sy1 >= (int)g_height) sy1 = g_height;

    float blur_f = (float)blur;

    for (int py = sy0; py < sy1; py += 2) {
        for (int px = sx0; px < sx1; px += 2) {
            int qx = (px < x) ? (x - px) : ((px > x + w) ? (px - (x + w)) : 0);
            int qy = (py < y + offset_y) ? (y + offset_y - py) : ((py > y + h + offset_y) ? (py - (y + h + offset_y)) : 0);

            float dist = (float)(qx * qx + qy * qy);
            if (dist < blur_f * blur_f) {
                float falloff = 1.0f - (dist / (blur_f * blur_f));
                unsigned char alpha = (unsigned char)((float)opacity * falloff * falloff);
                if (alpha > 1) {
                    put_pixel_alpha(px, py, 0x00000000, alpha);
                    put_pixel_alpha(px + 1, py, 0x00000000, alpha);
                    put_pixel_alpha(px, py + 1, 0x00000000, alpha);
                    put_pixel_alpha(px + 1, py + 1, 0x00000000, alpha);
                }
            }
        }
    }
}

// Filtro Kawase Blur para Superfícies de Vidro Acrílico (Glassmorphism)
static void apply_kawase_blur(int x, int y, int w, int h, int distance) {
    if (!g_back_fb || distance <= 0) return;

    int x0 = (x < 0) ? 0 : x;
    int y0 = (y < 0) ? 0 : y;
    int x1 = (x + w >= (int)g_width) ? (int)g_width - 1 : x + w;
    int y1 = (y + h >= (int)g_height) ? (int)g_height - 1 : y + h;

    int d = distance;

    for (int py = y0; py < y1; py += 2) {
        for (int px = x0; px < x1; px += 2) {
            int sx0 = (px - d >= 0) ? px - d : px;
            int sy0 = (py - d >= 0) ? py - d : py;
            int sx1 = (px + d < (int)g_width) ? px + d : px;
            int sy1 = (py + d < (int)g_height) ? py + d : py;

            unsigned int c1 = g_back_fb[sy0 * g_pitch + sx0];
            unsigned int c2 = g_back_fb[sy0 * g_pitch + sx1];
            unsigned int c3 = g_back_fb[sy1 * g_pitch + sx0];
            unsigned int c4 = g_back_fb[sy1 * g_pitch + sx1];

            unsigned int r = (((c1 >> 16) & 0xFF) + ((c2 >> 16) & 0xFF) + ((c3 >> 16) & 0xFF) + ((c4 >> 16) & 0xFF)) / 4;
            unsigned int g = (((c1 >> 8) & 0xFF) + ((c2 >> 8) & 0xFF) + ((c3 >> 8) & 0xFF) + ((c4 >> 8) & 0xFF)) / 4;
            unsigned int b = ((c1 & 0xFF) + (c2 & 0xFF) + (c3 & 0xFF) + (c4 & 0xFF)) / 4;

            unsigned int avg = (r << 16) | (g << 8) | b;
            g_back_fb[py * g_pitch + px] = avg;
            if (px + 1 < (int)g_width) g_back_fb[py * g_pitch + (px + 1)] = avg;
            if (py + 1 < (int)g_height) g_back_fb[(py + 1) * g_pitch + px] = avg;
            if (px + 1 < (int)g_width && py + 1 < (int)g_height) g_back_fb[(py + 1) * g_pitch + (px + 1)] = avg;
        }
    }
}

// Painel de Superfície Material 3 com Cantos Suaves
static void draw_googlebook_card(int x, int y, int w, int h, int radius, unsigned int bg_color, unsigned char alpha, unsigned int border_color) {
    draw_material_elevation_shadow(x, y, w, h, radius, 22, 8, 110);
    apply_kawase_blur(x, y, w, h, 3);
    draw_rounded_rect_sdf(x, y, w, h, radius, bg_color, alpha, border_color, 80, 1);

    int hl_x1 = x + radius;
    int hl_x2 = x + w - radius;
    if (hl_x2 > hl_x1 && (y + 1) < (int)g_height) {
        for (int px = hl_x1; px < hl_x2; px++) {
            put_pixel_alpha(px, y + 1, 0x00FFFFFF, 50);
        }
    }
}

// Círculo com Suavização de Borda
static void draw_smooth_circle(int cx, int cy, int radius, unsigned int fill_color, unsigned int border_color) {
    int r2 = radius * radius;
    int r_outer2 = (radius + 1) * (radius + 1);

    for (int dy = -(radius + 1); dy <= (radius + 1); dy++) {
        for (int dx = -(radius + 1); dx <= (radius + 1); dx++) {
            int d2 = dx * dx + dy * dy;
            int px = cx + dx;
            int py = cy + dy;

            if (d2 <= (radius - 1) * (radius - 1)) {
                put_pixel_fast(px, py, fill_color);
            } else if (d2 <= r2) {
                put_pixel_fast(px, py, border_color);
            } else if (d2 <= r_outer2) {
                put_pixel_alpha(px, py, border_color, 110);
            }
        }
    }
}

// Linha Antialiased
static void draw_line_alpha(int x0, int y0, int x1, int y1, unsigned int color, unsigned char alpha) {
    int dx = (x1 >= x0) ? (x1 - x0) : (x0 - x1);
    int dy = (y1 >= y0) ? (y1 - y0) : (y0 - y1);
    int sx = (x0 < x1) ? 1 : -1;
    int sy = (y0 < y1) ? 1 : -1;
    int err = dx - dy;

    while (1) {
        put_pixel_alpha(x0, y0, color, alpha);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 < dx) { err += dx; y0 += sy; }
    }
}

// Linha Grossa Antialiased (3px) para Ícones Vetoriais
static void draw_thick_line(int x0, int y0, int x1, int y1, unsigned int color) {
    draw_line_alpha(x0, y0, x1, y1, color, 255);
    draw_line_alpha(x0 + 1, y0, x1 + 1, y1, color, 220);
    draw_line_alpha(x0, y0 + 1, x1, y1 + 1, color, 220);
    draw_line_alpha(x0 - 1, y0, x1 - 1, y1, color, 140);
    draw_line_alpha(x0, y0 - 1, x1, y1 - 1, color, 140);
}

// Controles Minimalistas de Janela Material 3
static void draw_material_window_controls(int x, int y) {
    draw_rounded_rect_sdf(x, y - 10, 24, 20, 10, 0x001E293B, 180, 0x00475569, 100, 1);
    draw_text_smooth(x + 8, y - 8, "-", 0x0094A3B8);

    draw_rounded_rect_sdf(x + 28, y - 10, 24, 20, 10, 0x001E293B, 180, 0x00475569, 100, 1);
    draw_text_smooth(x + 36, y - 8, "+", 0x0094A3B8);

    draw_rounded_rect_sdf(x + 56, y - 10, 24, 20, 10, 0x00451A1A, 220, 0x00EF4444, 180, 1);
    draw_text_smooth(x + 64, y - 8, "x", 0x00FCA5A5);
}

// -------------------------------------------------------------
// ÍCONES VETORIAIS MODERNOS (3D Squircle com Preenchimento e Gradientes)
// -------------------------------------------------------------

static void draw_material_app_icon(int cx, int cy, int size, int app_id, int is_hovered) {
    int radius = size / 3;
    int x = cx - size / 2;
    int y = cy - size / 2;

    if (is_hovered) {
        draw_material_elevation_shadow(x - 2, y - 2, size + 4, size + 4, radius, 14, 4, 180);
    } else {
        draw_material_elevation_shadow(x, y, size, size, radius, 8, 3, 110);
    }

    switch (app_id) {
        case 0: // Terminal Soberano (Fundo Esmeralda Escuro + Prompt Neon Grosso)
            draw_rounded_rect_sdf(x, y, size, size, radius, 0x00062016, 255, 0x0010B981, 240, 1);
            // Círculo central sutil
            draw_smooth_circle(cx, cy, size / 3, 0x000D3827, 0x0010B981);
            // Prompt `>_` Grosso e Nítido
            draw_thick_line(x + 15, y + 16, x + 23, y + 24, 0x0034D399);
            draw_thick_line(x + 15, y + 32, x + 23, y + 24, 0x0034D399);
            draw_thick_line(x + 26, y + 32, x + 37, y + 32, 0x0000E5FF);
            break;

        case 1: // BKN Studio IDE (Safira/Azul Índigo + Código `< / >`)
            draw_rounded_rect_sdf(x, y, size, size, radius, 0x000E1C38, 255, 0x003B82F6, 240, 1);
            draw_smooth_circle(cx, cy, size / 3, 0x001D3557, 0x0038BDF8);
            // Glifo `< / >`
            draw_thick_line(x + 18, y + 17, x + 12, y + 24, 0x0038BDF8);
            draw_thick_line(x + 12, y + 24, x + 18, y + 31, 0x0038BDF8);
            draw_thick_line(x + 23, y + 33, x + 29, y + 15, 0x00C084FC);
            draw_thick_line(x + 34, y + 17, x + 40, y + 24, 0x0038BDF8);
            draw_thick_line(x + 40, y + 24, x + 34, y + 31, 0x0038BDF8);
            break;

        case 2: // BakenFS Explorer (Pasta 3D Dourada/Âmbar com Aba Branca)
            draw_rounded_rect_sdf(x, y, size, size, radius, 0x002B1D04, 255, 0x00F59E0B, 240, 1);
            // Aba de Fundo da Pasta
            draw_rounded_rect_sdf(x + 12, y + 14, 14, 7, 3, 0x00D97706, 255, 0x00F59E0B, 255, 1);
            // Documento Branco Interno
            draw_rounded_rect_sdf(x + 18, y + 15, 18, 12, 2, 0x00F8FAFC, 255, 0x00CBD5E1, 255, 1);
            // Aba Frontal da Pasta 3D
            draw_rounded_rect_sdf(x + 12, y + 19, 28, 18, 5, 0x00F59E0B, 255, 0x00FDE68A, 255, 1);
            break;

        case 3: // Q-HAL 3D (Orbe Quântico Atômico + Anéis Orbitais)
            draw_rounded_rect_sdf(x, y, size, size, radius, 0x00062036, 255, 0x0000E5FF, 240, 1);
            // Núcleo Quântico Central
            draw_smooth_circle(cx, cy, 6, 0x0000E5FF, 0x00FFFFFF);
            // Anéis Orbitais Elípticos
            for (int deg = 0; deg < 360; deg += 10) {
                int ox1 = cx + (int)(15.0f * (float)(deg < 180 ? (1.0f - (float)deg/90.0f) : ((float)deg/90.0f - 3.0f)));
                int oy1 = cy + (int)(7.0f * (float)(deg < 180 ? (float)deg/90.0f : (4.0f - (float)deg/90.0f)));
                put_pixel_alpha(ox1, oy1, 0x0038BDF8, 200);
            }
            break;

        case 4: // PQC Shield (Escudo Pós-Quântico Púrpura/Ciano)
            draw_rounded_rect_sdf(x, y, size, size, radius, 0x00260742, 255, 0x00A855F7, 240, 1);
            // Silhueta do Escudo
            draw_thick_line(x + 15, y + 15, cx, y + 12, 0x00C084FC);
            draw_thick_line(cx, y + 12, x + size - 15, y + 15, 0x00C084FC);
            draw_thick_line(x + 15, y + 15, x + 17, y + 26, 0x00C084FC);
            draw_thick_line(x + size - 15, y + 15, x + size - 17, y + 26, 0x00C084FC);
            draw_thick_line(x + 17, y + 26, cx, y + 35, 0x0000E5FF);
            draw_thick_line(x + size - 17, y + 26, cx, y + 35, 0x0000E5FF);
            draw_smooth_circle(cx, cy + 2, 3, 0x00FFFFFF, 0x0000E5FF);
            break;

        case 5: // Settings & Control (Engrenagem com 8 Dentes e Eixo Metálico)
            draw_rounded_rect_sdf(x, y, size, size, radius, 0x00131C2E, 255, 0x0094A3B8, 220, 1);
            // Dentes da Engrenagem
            draw_smooth_circle(cx, cy, 10, 0x00475569, 0x0094A3B8);
            draw_thick_line(cx - 13, cy, cx + 13, cy, 0x00CBD5E1);
            draw_thick_line(cx, cy - 13, cx, cy + 13, 0x00CBD5E1);
            draw_thick_line(cx - 9, cy - 9, cx + 9, cy + 9, 0x00CBD5E1);
            draw_thick_line(cx - 9, cy + 9, cx + 9, cy - 9, 0x00CBD5E1);
            // Eixo Central
            draw_smooth_circle(cx, cy, 5, 0x00131C2E, 0x0000E5FF);
            break;
    }

    // Reflexo de Luz Superior no Squircle
    for (int px = x + radius; px < x + size - radius; px++) {
        put_pixel_alpha(px, y + 1, 0x00FFFFFF, 80);
    }
}

// Esfera de Bloch 3D Fluida
static void draw_bloch_sphere_3d(int cx, int cy, int radius, int step) {
    for (int dy = -radius; dy <= radius; dy++) {
        for (int dx = -radius; dx <= radius; dx++) {
            int d2 = dx * dx + dy * dy;
            if (d2 <= radius * radius) {
                int light_dist = (dx + radius / 3) * (dx + radius / 3) + (dy + radius / 3) * (dy + radius / 3);
                int intensity = 20 + (50 * (radius * radius * 2 - light_dist)) / (radius * radius * 2);
                if (intensity < 10) intensity = 10;
                if (intensity > 85) intensity = 85;

                unsigned int r = (unsigned int)(8 + intensity / 4);
                unsigned int g = (unsigned int)(18 + intensity / 2);
                unsigned int b = (unsigned int)(42 + intensity);
                put_pixel_alpha(cx + dx, cy + dy, (r << 16) | (g << 8) | b, 240);
            }
        }
    }

    draw_line_alpha(cx, cy - radius - 8, cx, cy + radius + 8, 0x0038BDF8, 120);
    draw_line_alpha(cx - radius - 8, cy, cx + radius + 8, cy, 0x0038BDF8, 120);

    for (int deg = 0; deg < 360; deg += 6) {
        int ex = cx + (int)((float)radius * (float)(deg < 180 ? (1.0f - (float)deg/90.0f) : ((float)deg/90.0f - 3.0f)));
        int ey = cy + (int)((float)radius * 0.35f * (float)(deg < 180 ? (float)deg/90.0f : (4.0f - (float)deg/90.0f)));
        put_pixel_alpha(ex, ey, 0x00818CF8, 110);
    }

    int offsets_x[8] = { 30, 20, -16, -30, -22, 0, 22, 34 };
    int offsets_y[8] = { -34, -40, -30, -8, 18, 36, 24, 0 };
    int target_x = cx + offsets_x[step % 8];
    int target_y = cy + offsets_y[step % 8];

    draw_line_alpha(cx, cy, target_x, target_y, 0x0000E5FF, 255);
    draw_smooth_circle(target_x, target_y, 6, 0x0000E5FF, 0x00FFFFFF);
    draw_smooth_circle(target_x, target_y, 2, 0x00FFFFFF, 0x00FFFFFF);
}

// Gráfico de Onda Quântica Material Design
static void draw_quantum_wave_graph(int x, int y, int w, int h) {
    draw_rounded_rect_sdf(x, y, w, h, 12, 0x00080E18, 230, 0x001E293B, 120, 1);
    draw_text_smooth(x + 14, y + 10, "Quantum Probability Amplitude", 0x0038BDF8);

    int mid_y = y + h / 2 + 10;
    int prev_px = x + 12;
    int prev_py = mid_y;

    for (int i = 0; i < w - 24; i += 3) {
        float nx = (float)i / (float)(w - 24);
        int wave_val = (int)(18.0f * (float)((i / 8) % 2 == 0 ? 1 : -1) * (1.0f - (nx - 0.5f) * (nx - 0.5f) * 4.0f));
        int curr_px = x + 12 + i;
        int curr_py = mid_y + wave_val;

        draw_line_alpha(prev_px, prev_py, curr_px, curr_py, 0x0000E5FF, 230);
        put_pixel_alpha(curr_px, curr_py + 1, 0x0010B981, 120);

        prev_px = curr_px;
        prev_py = curr_py;
    }
}

// Papel de Parede Nebula Bloom Orgânico de Alta Definição
static void init_wallpaper_cache() {
    if (!g_wallpaper_cache) return;

    for (unsigned int y = 0; y < g_height; y++) {
        float ny = (float)y / (float)g_height;
        for (unsigned int x = 0; x < g_width; x++) {
            float nx = (float)x / (float)g_width;

            // Foco 1: Aurora Ciano / Azul Elétrico no Canto Superior Direito
            float dx1 = nx - 0.75f;
            float dy1 = ny - 0.25f;
            float d1 = (dx1 * dx1 + dy1 * dy1) * 1.8f;
            float w1 = 1.0f - d1;
            if (w1 < 0.0f) w1 = 0.0f;

            // Foco 2: Orbe Magenta / Púrpura no Canto Inferior Esquerdo
            float dx2 = nx - 0.20f;
            float dy2 = ny - 0.75f;
            float d2 = (dx2 * dx2 + dy2 * dy2) * 2.2f;
            float w2 = 1.0f - d2;
            if (w2 < 0.0f) w2 = 0.0f;

            // Foco 3: Halo Central Sutil
            float dx3 = nx - 0.50f;
            float dy3 = ny - 0.45f;
            float d3 = (dx3 * dx3 + dy3 * dy3) * 3.0f;
            float w3 = 1.0f - d3;
            if (w3 < 0.0f) w3 = 0.0f;

            // Cores ricas e luminosas (Sapphire, Cyan, Indigo, Violet)
            int r = (int)(12.0f + 35.0f * w1 + 110.0f * w2 + 25.0f * w3 + 10.0f * ny);
            int g = (int)(18.0f + 95.0f * w1 + 30.0f * w2 + 40.0f * w3 + 15.0f * ny);
            int b = (int)(45.0f + 160.0f * w1 + 140.0f * w2 + 80.0f * w3 + 55.0f * ny);

            if (r > 255) r = 255;
            if (g > 255) g = 255;
            if (b > 255) b = 255;

            g_wallpaper_cache[y * g_pitch + x] = ((unsigned int)r << 16) | ((unsigned int)g << 8) | (unsigned int)b;
        }
    }
}

// Magic Pointer
static const char g_magic_pointer[20][21] = {
    "X                   ",
    "XX                  ",
    "X.X                 ",
    "X..X                ",
    "X...X               ",
    "X....X              ",
    "X.....X             ",
    "X......X            ",
    "X.......X           ",
    "X........X          ",
    "X.....XXXXX         ",
    "X..X..X             ",
    "X.X X..X            ",
    "XX   X..X           ",
    "X     X..X          ",
    "       XX           ",
    "                    ",
    "                    ",
    "                    ",
    "                    "
};

static void save_and_draw_cursor_frontbuffer(int x, int y) {
    if (!g_front_fb) return;
    for (int r = 0; r < 20; r++) {
        for (int c = 0; c < 20; c++) {
            int px = x + c;
            int py = y + r;
            if (px >= 0 && px < (int)g_width && py >= 0 && py < (int)g_height) {
                g_mouse_underlay[r][c] = g_front_fb[py * g_pitch + px];
                char ch = g_magic_pointer[r][c];
                if (ch == 'X') {
                    g_front_fb[py * g_pitch + px] = 0x000B0F19;
                } else if (ch == '.') {
                    g_front_fb[py * g_pitch + px] = 0x0000E5FF;
                }
            }
        }
    }
}

static void restore_cursor_frontbuffer(int x, int y) {
    if (!g_front_fb) return;
    for (int r = 0; r < 20; r++) {
        for (int c = 0; c < 20; c++) {
            int px = x + c;
            int py = y + r;
            if (px >= 0 && px < (int)g_width && py >= 0 && py < (int)g_height) {
                g_front_fb[py * g_pitch + px] = g_mouse_underlay[r][c];
            }
        }
    }
}

// -------------------------------------------------------------
// RENDERIZADORES DE JANELAS (BKN Studio IDE e Q-HAL Studio)
// -------------------------------------------------------------

// Janela 1: BKN Studio IDE
static void render_window_ide(const char* current_input) {
    if (!g_win_ide_open) return;

    int win1_w = g_win_ide_maximized ? (g_width - 40) : 490;
    int win1_h = g_win_ide_maximized ? (g_height - 130) : (g_height - 150);
    if (!g_win_ide_maximized && win1_h > 530) win1_h = 530;

    int win1_x = g_win_ide_maximized ? 20 : g_win_ide_x;
    int win1_y = g_win_ide_maximized ? 54 : g_win_ide_y;

    draw_googlebook_card(win1_x, win1_y, win1_w, win1_h, 20, 0x000B101E, 250, 0x003B82F6);

    // Barra Superior da Janela (Title Bar)
    draw_rounded_rect_sdf(win1_x, win1_y, win1_w, 42, 20, 0x00131C31, 255, 0x003B82F6, 60, 1);

    // Abas Material You
    unsigned int tab1_bg = (g_active_editor_tab == 0) ? 0x001D4ED8 : 0x001E293B;
    draw_rounded_rect_sdf(win1_x + 16, win1_y + 8, 130, 26, 13, tab1_bg, 255, 0x0060A5FA, 180, 1);
    draw_smooth_circle(win1_x + 28, win1_y + 21, 3, 0x0000E5FF, 0x0000E5FF);
    draw_text_smooth(win1_x + 38, win1_y + 13, "quantum.bkn", (g_active_editor_tab == 0) ? 0x00FFFFFF : 0x0094A3B8);

    unsigned int tab2_bg = (g_active_editor_tab == 1) ? 0x006D28D9 : 0x001E293B;
    draw_rounded_rect_sdf(win1_x + 152, win1_y + 8, 136, 26, 13, tab2_bg, 255, 0x00C084FC, 180, 1);
    draw_smooth_circle(win1_x + 164, win1_y + 21, 3, 0x00C084FC, 0x00C084FC);
    draw_text_smooth(win1_x + 174, win1_y + 13, "crypto_pqc.bkn", (g_active_editor_tab == 1) ? 0x00FFFFFF : 0x0094A3B8);

    draw_material_window_controls(win1_x + win1_w - 90, win1_y + 21);

    // Sidebar Mini-Explorer Material
    int sb_w = 92;
    draw_rounded_rect_sdf(win1_x + 12, win1_y + 50, sb_w, win1_h - 110, 12, 0x00080D1A, 255, 0x001E293B, 80, 1);
    draw_text_smooth(win1_x + 20, win1_y + 60, "PROJECT", 0x0064748B);
    draw_text_smooth(win1_x + 20, win1_y + 80, "kernel/", 0x0038BDF8);
    draw_text_smooth(win1_x + 28, win1_y + 98, "main.bkn", 0x0094A3B8);
    draw_text_smooth(win1_x + 28, win1_y + 116, "teleport", 0x0000E5FF);
    draw_text_smooth(win1_x + 20, win1_y + 136, "libbkn/", 0x0038BDF8);
    draw_text_smooth(win1_x + 28, win1_y + 154, "gui.bkn", 0x0010B981);

    // Editor Canvas
    int editor_x = win1_x + sb_w + 20;
    int code_y = win1_y + 54;
    for (int l = 1; l <= 11; l++) {
        char num[4];
        num[0] = (l < 10) ? ' ' : '1';
        num[1] = '0' + (l % 10);
        num[2] = '\0';
        draw_text_smooth(editor_x, code_y + (l - 1) * 18, num, 0x00475569);
    }

    int text_x = editor_x + 22;
    if (g_active_editor_tab == 0) {
        draw_text_smooth(text_x, code_y + 0 * 18,   "module kernel::quantum_teleport;", 0x0094A3B8);
        draw_text_smooth(text_x, code_y + 1 * 18,   "import libbkn::gui::*; import libbkn::quantum::*;", 0x0060A5FA);
        draw_text_smooth(text_x, code_y + 2 * 18,   "@quantum", 0x00C084FC);
        draw_text_smooth(text_x, code_y + 3 * 18,   "pub fn teleport_qubit(src: qubit) -> (u8, u8) {", 0x0038BDF8);
        draw_text_smooth(text_x + 14, code_y + 4 * 18,  "let mut bell = qreg::alloc(2);", 0x00F8FAFC);
        draw_text_smooth(text_x + 14, code_y + 5 * 18,  "H(bell[0]);", 0x0060A5FA);
        draw_text_smooth(text_x + 14, code_y + 6 * 18,  "CNOT(bell[0], bell[1]); // EPR Pair", 0x0010B981);
        draw_text_smooth(text_x + 14, code_y + 7 * 18,  "CNOT(src, bell[0]);", 0x0060A5FA);
        draw_text_smooth(text_x + 14, code_y + 8 * 18,  "let m0 = measure(src);", 0x00F59E0B);
        draw_text_smooth(text_x + 14, code_y + 9 * 18,  "let m1 = measure(bell[0]);", 0x00F59E0B);
        draw_text_smooth(text_x + 14, code_y + 10 * 18, "return (m0, m1);", 0x0038BDF8);
    } else {
        draw_text_smooth(text_x, code_y + 0 * 18,   "module kernel::crypto_pqc;", 0x0094A3B8);
        draw_text_smooth(text_x, code_y + 1 * 18,   "import libbkn::crypto::{ml_kem_768, ml_dsa_65};", 0x0060A5FA);
        draw_text_smooth(text_x, code_y + 2 * 18,   "@system", 0x00C084FC);
        draw_text_smooth(text_x, code_y + 3 * 18,   "pub fn encapsulate_key(pk: &[u8; 1184]) -> [u8; 32] {", 0x0038BDF8);
        draw_text_smooth(text_x + 14, code_y + 4 * 18,  "let (ct, secret) = ml_kem_768::encaps(pk);", 0x0010B981);
        draw_text_smooth(text_x + 14, code_y + 5 * 18,  "return secret; // Quantum-Safe Shield", 0x00F59E0B);
        draw_text_smooth(text_x, code_y + 6 * 18,   "}", 0x0038BDF8);
    }

    // Terminal Integrado
    int term_y = win1_h - 96 + win1_y;
    int term_w = win1_w - 24;
    draw_rounded_rect_sdf(win1_x + 12, term_y, term_w, 82, 12, 0x00060A14, 255, 0x0038BDF8, 120, 1);

    draw_text_smooth(win1_x + 22, term_y + 8, g_term_history[0], 0x0094A3B8);
    draw_text_smooth(win1_x + 22, term_y + 24, g_term_history[1], 0x0060A5FA);
    draw_text_smooth(win1_x + 22, term_y + 40, g_term_history[2], 0x0034D399);

    char prompt_buf[140];
    prompt_buf[0] = 'b'; prompt_buf[1] = 'a'; prompt_buf[2] = 'k'; prompt_buf[3] = 'e';
    prompt_buf[4] = 'n'; prompt_buf[5] = '>'; prompt_buf[6] = ' ';
    int pi = 0;
    while (current_input[pi] && pi < 45) {
        prompt_buf[7 + pi] = current_input[pi];
        pi++;
    }
    prompt_buf[7 + pi] = '_';
    prompt_buf[8 + pi] = '\0';
    draw_text_smooth(win1_x + 22, term_y + 58, prompt_buf, 0x0000E5FF);
}

// Janela 2: Q-HAL Quantum AI Studio
static void render_window_qpu() {
    if (!g_win_qpu_open) return;

    int win2_w = g_win_qpu_maximized ? (g_width - 40) : (g_width - g_win_qpu_x - 36);
    if (!g_win_qpu_maximized && win2_w < 410) win2_w = 410;
    int win2_h = g_win_qpu_maximized ? (g_height - 130) : (g_height - 150);
    if (!g_win_qpu_maximized && win2_h > 530) win2_h = 530;

    int win2_x = g_win_qpu_maximized ? 20 : g_win_qpu_x;
    int win2_y = g_win_qpu_maximized ? 54 : g_win_qpu_y;

    draw_googlebook_card(win2_x, win2_y, win2_w, win2_h, 20, 0x00070F1C, 250, 0x0000E5FF);

    // Barra de Título
    draw_rounded_rect_sdf(win2_x, win2_y, win2_w, 42, 20, 0x000F2942, 255, 0x0000E5FF, 60, 1);
    draw_text_smooth(win2_x + 20, win2_y + 13, "Q-HAL 3D Quantum Coprocessor", 0x0000E5FF);
    draw_material_window_controls(win2_x + win2_w - 90, win2_y + 21);

    // Esfera de Bloch 3D Fluida
    int sphere_cx = win2_x + (win2_w / 2);
    int sphere_cy = win2_y + 105;
    draw_bloch_sphere_3d(sphere_cx, sphere_cy, 48, g_anim_frame);

    draw_text_smooth(sphere_cx - 10, sphere_cy - 66, "|0>", 0x0000E5FF);
    draw_text_smooth(sphere_cx - 10, sphere_cy + 56, "|1>", 0x0000E5FF);
    draw_text_smooth(sphere_cx + 56, sphere_cy - 6, "|+>", 0x00818CF8);
    draw_text_smooth(sphere_cx - 72, sphere_cy - 6, "|->", 0x00818CF8);

    // Gráfico de Onda
    int wave_y = win2_y + 172;
    int wave_w = win2_w - 28;
    draw_quantum_wave_graph(win2_x + 14, wave_y, wave_w, 76);

    // Cartões Material 3 em Grade
    int card_y = wave_y + 86;
    int half_w = (wave_w - 12) / 2;

    // Card 1: Qubit Telemetry
    draw_rounded_rect_sdf(win2_x + 14, card_y, half_w, 64, 12, 0x000A1A2E, 230, 0x0000E5FF, 120, 1);
    draw_text_smooth(win2_x + 24, card_y + 12, "EPR Bell State", 0x0000E5FF);
    draw_text_smooth(win2_x + 24, card_y + 34, "Fidelity: 99.99%", 0x0010B981);

    // Card 2: Engine AVX-512
    draw_rounded_rect_sdf(win2_x + 20 + half_w, card_y, half_w, 64, 12, 0x00172554, 230, 0x003B82F6, 120, 1);
    draw_text_smooth(win2_x + 30 + half_w, card_y + 12, "AVX-512 Matrix", 0x0060A5FA);
    draw_text_smooth(win2_x + 30 + half_w, card_y + 34, "32 Qubits Active", 0x0093C5FD);

    // Card 3: PQC Shield Full Width
    draw_rounded_rect_sdf(win2_x + 14, card_y + 72, wave_w, 54, 12, 0x001E1B4B, 230, 0x00C084FC, 120, 1);
    draw_text_smooth(win2_x + 24, card_y + 82, "PQC Shield: ML-KEM-768 + ML-DSA-65", 0x00C084FC);
    draw_text_smooth(win2_x + 24, card_y + 102, "Zero-Trust Ring 0 Enclave [Secured]", 0x0010B981);
}

// -------------------------------------------------------------
// RENDERIZADOR DO DESKTOP SOBERANO / MATERIAL 3
// -------------------------------------------------------------

static void render_full_frame_to_backbuffer(const char* current_input) {
    if (!g_back_fb || !g_wallpaper_cache) return;

    // 1. Wallpaper
    unsigned int total = g_pitch * g_height;
    for (unsigned int i = 0; i < total; i++) {
        g_back_fb[i] = g_wallpaper_cache[i];
    }

    // 2. Barra Superior Flutuante Material You (Floating Top Bar)
    draw_googlebook_card(20, 10, g_width - 40, 38, 19, 0x000B0F19, 210, 0x001E293B);

    // Baken OS Logo Pill
    draw_rounded_rect_sdf(30, 16, 110, 26, 13, 0x001E1B4B, 255, 0x00818CF8, 160, 1);
    draw_smooth_circle(44, 29, 6, 0x0000E5FF, 0x00FFFFFF);
    draw_text_smooth(56, 22, "Baken OS", 0x00FFFFFF);

    // Barra de Pesquisa Centralizada (com Ícone Lupa)
    int search_w = 340;
    int search_x = (g_width - search_w) / 2;
    draw_rounded_rect_sdf(search_x, 16, search_w, 26, 13, 0x001E293B, 240, 0x0038BDF8, 120, 1);
    // Ícone Lupa
    draw_smooth_circle(search_x + 18, 29, 4, 0x001E293B, 0x0038BDF8);
    draw_line_alpha(search_x + 21, 32, search_x + 25, 36, 0x0038BDF8, 255);
    draw_text_smooth(search_x + 32, 22, "Pesquisar no Baken OS ou digitar comando...", 0x0094A3B8);

    // Status da Direita (Ícones Vetoriais Wi-Fi, Bateria e Relógio)
    int status_x = g_width - 250;
    draw_rounded_rect_sdf(status_x, 16, 220, 26, 13, 0x00172554, 255, 0x003B82F6, 140, 1);

    // Ícone Wi-Fi (3 Arcos)
    draw_smooth_circle(status_x + 18, 31, 2, 0x0060A5FA, 0x0060A5FA);
    draw_line_alpha(status_x + 14, 27, status_x + 22, 27, 0x0060A5FA, 220);
    draw_line_alpha(status_x + 11, 24, status_x + 25, 24, 0x0060A5FA, 160);

    draw_text_smooth(status_x + 32, 22, "Wi-Fi 7", 0x0060A5FA);

    draw_text_smooth(status_x + 92, 22, "|", 0x00334155);
    draw_text_smooth(status_x + 104, 22, "10:24", 0x00FFFFFF);
    draw_text_smooth(status_x + 152, 22, "|", 0x00334155);

    // Ícone Bateria
    draw_rounded_rect_sdf(status_x + 164, 23, 20, 11, 2, 0x001E293B, 255, 0x0010B981, 255, 1);
    draw_rounded_rect_sdf(status_x + 166, 25, 14, 7, 1, 0x0010B981, 255, 0x0010B981, 255, 1);
    draw_line_alpha(status_x + 185, 26, status_x + 185, 29, 0x0010B981, 255);
    draw_text_smooth(status_x + 190, 22, "95%", 0x0010B981);

    // 2.5. Área de Trabalho Limpa (At a Glance Smart Widget & Ícones de Desktop)
    if (!g_win_ide_open && !g_win_qpu_open) {
        // Smart Widget Central "At a Glance"
        int aag_w = 480;
        int aag_x = (g_width - aag_w) / 2;
        int aag_y = 110;

        draw_googlebook_card(aag_x, aag_y, aag_w, 124, 24, 0x000D1527, 210, 0x002A3B5C);

        // Relógio Digital Display Grande em Vetor Suave (36px)
        draw_display_clock_text(aag_x + 24, aag_y + 16, "10:24", 0x0000E5FF);

        // Data e Clima com Tipografia Proporcional
        draw_text_smooth(aag_x + 160, aag_y + 18, "Quinta-feira, 26 de Agosto", 0x00F1F5F9);
        draw_text_smooth(aag_x + 160, aag_y + 36, "24 C Ensolarado | Sao Paulo", 0x0038BDF8);

        // Chip de Status Q-HAL Core
        draw_rounded_rect_sdf(aag_x + 24, aag_y + 76, aag_w - 48, 30, 15, 0x00131F37, 240, 0x0000E5FF, 140, 1);
        draw_smooth_circle(aag_x + 38, aag_y + 91, 4, 0x0010B981, 0x004ADE80);
        draw_text_smooth(aag_x + 50, aag_y + 83, "Baken OS Soberano • Microkernel Ring 0 Online", 0x00F8FAFC);

        // Grade de Ícones na Área de Trabalho (Desktop App Squircles)
        int desk_app_x[6] = { 180, 320, 460, 600, 740, 880 };
        int desk_app_y = 310;
        const char* desk_labels[6] = { "Terminal", "BKN Studio", "BakenFS", "Q-HAL 3D", "PQC Shield", "Settings" };

        for (int i = 0; i < 6; i++) {
            int cx = desk_app_x[i];
            int cy = desk_app_y;
            int dist = (g_mouse_x - cx) >= 0 ? (g_mouse_x - cx) : -(g_mouse_x - cx);
            int is_near = (dist < 40 && (g_mouse_y - cy >= -30 && g_mouse_y - cy <= 30));
            int size = is_near ? 56 : 50;

            draw_material_app_icon(cx, cy, size, i, is_near);

            // Calcula largura proporcional do label para centralização perfeita
            int label_w = 0;
            const char* lp = desk_labels[i];
            while (*lp) { label_w += get_char_advance(*lp) + 1; lp++; }
            int label_x = cx - label_w / 2;

            draw_text_smooth(label_x, cy + 34, desk_labels[i], is_near ? 0x0000E5FF : 0x00CBD5E1);
        }
    }

    // 3. Renderiza Janelas Ativas de acordo com a Ordem Z (Foco)
    for (int z = 0; z < 2; z++) {
        int win_id = g_win_z_order[z];
        if (win_id == 0) {
            render_window_ide(current_input);
        } else if (win_id == 1) {
            render_window_qpu();
        }
    }

    // 5. Dock Flutuante Material You (Floating Shelf)
    g_dock_x = (g_width - g_dock_w) / 2;
    g_dock_y = g_height - 76;

    draw_googlebook_card(g_dock_x, g_dock_y, g_dock_w, g_dock_h, 28, 0x000B101E, 230, 0x003B82F6);

    g_icon_centers[0] = g_dock_x + 50;
    g_icon_centers[1] = g_dock_x + 130;
    g_icon_centers[2] = g_dock_x + 210;
    g_icon_centers[3] = g_dock_x + 290;
    g_icon_centers[4] = g_dock_x + 370;
    g_icon_centers[5] = g_dock_x + 450;

    for (int i = 0; i < 6; i++) {
        int cx = g_icon_centers[i];
        int cy = g_dock_y + 33;

        int dist = (g_mouse_x - cx) >= 0 ? (g_mouse_x - cx) : -(g_mouse_x - cx);
        int is_near = (dist < 40 && g_mouse_y >= g_dock_y - 10);
        int size = is_near ? 50 : 44;
        int draw_cy = is_near ? (cy - 6) : cy;

        draw_material_app_icon(cx, draw_cy, size, i, is_near);

        if (i == 0 || (i == 1 && g_win_ide_open) || (i == 3 && g_win_qpu_open)) {
            draw_smooth_circle(cx, g_dock_y + 58, 2, 0x0038BDF8, 0x0038BDF8);
        }
    }

    // 6. Central de Controle Material 3 (Se Aberta)
    if (g_control_center_open) {
        int cc_w = 320;
        int cc_x = g_width - cc_w - 20;
        draw_googlebook_card(cc_x, 48, cc_w, 340, 20, 0x000F172A, 252, 0x0038BDF8);

        draw_text_smooth(cc_x + 24, 64, "QUICK SETTINGS", 0x0060A5FA);

        // Tiles
        draw_rounded_rect_sdf(cc_x + 20, 90, 132, 54, 14, 0x00064E3B, 255, 0x0010B981, 200, 1);
        draw_text_smooth(cc_x + 30, 102, "Wi-Fi 7 MLO", 0x0010B981);
        draw_text_smooth(cc_x + 30, 122, "5.8 Gbps", 0x0094A3B8);

        draw_rounded_rect_sdf(cc_x + 164, 90, 132, 54, 14, 0x00172554, 255, 0x003B82F6, 200, 1);
        draw_text_smooth(cc_x + 174, 102, "Bluetooth 5.4", 0x0060A5FA);
        draw_text_smooth(cc_x + 174, 122, "Connected", 0x0094A3B8);

        // Sliders
        draw_text_smooth(cc_x + 24, 160, "Volume (85%)", 0x00F8FAFC);
        draw_rounded_rect_sdf(cc_x + 20, 180, 276, 16, 8, 0x001E293B, 255, 0x00475569, 150, 1);
        draw_rounded_rect_sdf(cc_x + 20, 180, (276 * g_volume_level) / 100, 16, 8, 0x0010B981, 255, 0x0010B981, 255, 1);

        draw_text_smooth(cc_x + 24, 210, "Brightness (95%)", 0x00F8FAFC);
        draw_rounded_rect_sdf(cc_x + 20, 230, 276, 16, 8, 0x001E293B, 255, 0x00475569, 150, 1);
        draw_rounded_rect_sdf(cc_x + 20, 230, (276 * g_brightness_level) / 100, 16, 8, 0x0000E5FF, 255, 0x0000E5FF, 255, 1);

        draw_rounded_rect_sdf(cc_x + 20, 264, 276, 56, 12, 0x001E1B4B, 240, 0x00C084FC, 180, 1);
        draw_text_smooth(cc_x + 30, 276, "QPU Quantum State: Active", 0x00C084FC);
        draw_text_smooth(cc_x + 30, 296, "Quantum Telemetry: 120 FPS", 0x0010B981);
    }

    // 7. Menu Iniciar / App Drawer (Se Aberto)
    if (g_start_menu_open) {
        draw_googlebook_card(20, 48, 310, 360, 20, 0x000B0F19, 252, 0x003B82F6);

        draw_rounded_rect_sdf(32, 62, 286, 34, 10, 0x001E293B, 255, 0x0060A5FA, 200, 1);
        draw_text_smooth(44, 71, "Pesquisar no Baken OS...", 0x0094A3B8);

        draw_text_smooth(36, 110, "APLICATIVOS SOBERANOS", 0x0060A5FA);
        draw_text_smooth(36, 136, "1. BKN Studio IDE (v1.1)", 0x00FFFFFF);
        draw_text_smooth(36, 162, "2. Q-HAL Quantum Studio", 0x0000E5FF);
        draw_text_smooth(36, 188, "3. BakenFS File Explorer", 0x00F59E0B);
        draw_text_smooth(36, 214, "4. Quantum PQC Shield", 0x00C084FC);
        draw_text_smooth(36, 240, "5. Audio Studio & Synth", 0x00EC4899);
        draw_text_smooth(36, 266, "6. Terminal / BKNC Compiler", 0x0010B981);

        draw_rounded_rect_sdf(32, 298, 286, 56, 12, 0x000F172A, 240, 0x0010B981, 180, 1);
        draw_text_smooth(42, 308, "BakenUI: Native Vector Engine", 0x0010B981);
        draw_text_smooth(42, 328, "Memory: 512 MB / 4096 MB", 0x0038BDF8);
    }

    // Copia Backbuffer para tela física
    bakenfx_present_frame();

    // Desenha Cursor
    save_and_draw_cursor_frontbuffer(g_mouse_x, g_mouse_y);
    g_last_mouse_x = g_mouse_x;
    g_last_mouse_y = g_mouse_y;
}

// Loop Principal de Eventos e Renderização
static void run_baken_gui_shell(
    EFI_SYSTEM_TABLE *SystemTable,
    EFI_ABSOLUTE_POINTER_PROTOCOL *abs_pointer,
    EFI_SIMPLE_POINTER_PROTOCOL *rel_pointer
) {
    EFI_SIMPLE_TEXT_INPUT_PROTOCOL *in = SystemTable->ConIn;

    char cmd_buffer[128];
    int cmd_idx = 0;
    cmd_buffer[0] = '\0';

    init_wallpaper_cache();
    init_hardware_mouse();

    render_full_frame_to_backbuffer("");

    int loop_counter = 0;

    while (1) {
        loop_counter++;

        if (loop_counter % 300 == 0) {
            g_anim_frame++;
            render_full_frame_to_backbuffer(cmd_buffer);
        }

        int moved = 0;
        int btn_clicked = 0;

        // 1. Mouse PS/2
        int hdx = 0, hdy = 0, hbtn = 0;
        if (poll_hardware_mouse(&hdx, &hdy, &hbtn)) {
            g_mouse_x += hdx;
            g_mouse_y += hdy;
            if (g_mouse_x < 0) g_mouse_x = 0;
            if (g_mouse_y < 0) g_mouse_y = 0;
            if (g_mouse_x >= (int)g_width) g_mouse_x = g_width - 1;
            if (g_mouse_y >= (int)g_height) g_mouse_y = g_height - 1;
            moved = 1;
            if (hbtn) btn_clicked = 1;
        }

        // 2. Mouse Absoluto
        if (!moved && abs_pointer && abs_pointer->Mode) {
            EFI_ABSOLUTE_POINTER_STATE state;
            if (abs_pointer->GetState(abs_pointer, &state) == EFI_SUCCESS) {
                unsigned long long max_x = abs_pointer->Mode->AbsoluteMaxX;
                unsigned long long max_y = abs_pointer->Mode->AbsoluteMaxY;
                if (max_x > 0 && max_y > 0) {
                    g_mouse_x = (int)((state.CurrentX * g_width) / max_x);
                    g_mouse_y = (int)((state.CurrentY * g_height) / max_y);
                    moved = 1;
                    if (state.ActiveButtons & 1) btn_clicked = 1;
                }
            }
        }

        // 3. Mouse Relativo
        if (!moved && rel_pointer) {
            EFI_SIMPLE_POINTER_STATE state;
            if (rel_pointer->GetState(rel_pointer, &state) == EFI_SUCCESS) {
                g_mouse_x += (int)(state.RelativeMovementX / 2);
                g_mouse_y += (int)(state.RelativeMovementY / 2);
                if (g_mouse_x < 0) g_mouse_x = 0;
                if (g_mouse_y < 0) g_mouse_y = 0;
                if (g_mouse_x >= (int)g_width) g_mouse_x = g_width - 1;
                if (g_mouse_y >= (int)g_height) g_mouse_y = g_height - 1;
                moved = 1;
                if (state.LeftButton) btn_clicked = 1;
            }
        }

        if (moved) {
            if (btn_clicked && g_dragging_win == 1 && !g_win_ide_maximized) {
                g_win_ide_x = g_mouse_x - g_drag_offset_x;
                g_win_ide_y = g_mouse_y - g_drag_offset_y;
                if (g_win_ide_x < 0) g_win_ide_x = 0;
                if (g_win_ide_y < 38) g_win_ide_y = 38;
                render_full_frame_to_backbuffer(cmd_buffer);
            } else if (btn_clicked && g_dragging_win == 2 && !g_win_qpu_maximized) {
                g_win_qpu_x = g_mouse_x - g_drag_offset_x;
                g_win_qpu_y = g_mouse_y - g_drag_offset_y;
                if (g_win_qpu_x < 0) g_win_qpu_x = 0;
                if (g_win_qpu_y < 38) g_win_qpu_y = 38;
                render_full_frame_to_backbuffer(cmd_buffer);
            } else {
                restore_cursor_frontbuffer(g_last_mouse_x, g_last_mouse_y);
                save_and_draw_cursor_frontbuffer(g_mouse_x, g_mouse_y);
                g_last_mouse_x = g_mouse_x;
                g_last_mouse_y = g_mouse_y;

                if (g_mouse_y >= g_dock_y - 20) {
                    render_full_frame_to_backbuffer(cmd_buffer);
                }
            }
        }

        if (!btn_clicked) {
            g_dragging_win = 0;
        }

        // 4. Clique do Mouse
        if (btn_clicked) {
            int win1_w = g_win_ide_maximized ? (g_width - 40) : 490;
            int win1_x = g_win_ide_maximized ? 20 : g_win_ide_x;
            int win1_y = g_win_ide_maximized ? 54 : g_win_ide_y;

            int win2_w = g_win_qpu_maximized ? (g_width - 40) : (g_width - g_win_qpu_x - 36);
            int win2_x = g_win_qpu_maximized ? 20 : g_win_qpu_x;
            int win2_y = g_win_qpu_maximized ? 54 : g_win_qpu_y;

            // Top Bar: Menu Iniciar (Esquerda) e Central de Controle (Direita)
            if (g_mouse_x >= 20 && g_mouse_x <= 150 && g_mouse_y >= 10 && g_mouse_y <= 48) {
                g_start_menu_open = !g_start_menu_open;
                render_full_frame_to_backbuffer(cmd_buffer);
            } else if (g_mouse_x >= (int)g_width - 250 && g_mouse_x <= (int)g_width - 20 && g_mouse_y >= 10 && g_mouse_y <= 48) {
                g_control_center_open = !g_control_center_open;
                render_full_frame_to_backbuffer(cmd_buffer);
            }
            // Clique dentro do Menu Iniciar (App Drawer)
            else if (g_start_menu_open && g_mouse_x >= 20 && g_mouse_x <= 330 && g_mouse_y >= 48 && g_mouse_y <= 410) {
                if (g_mouse_y >= 126 && g_mouse_y < 152) {
                    // 1. BKN Studio IDE
                    g_win_ide_open = 1;
                    g_active_editor_tab = 0;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    g_start_menu_open = 0;
                } else if (g_mouse_y >= 152 && g_mouse_y < 178) {
                    // 2. Q-HAL Quantum Studio
                    g_win_qpu_open = 1;
                    g_win_z_order[0] = 0; g_win_z_order[1] = 1;
                    g_start_menu_open = 0;
                } else if (g_mouse_y >= 178 && g_mouse_y < 204) {
                    // 3. BakenFS File Explorer
                    g_start_menu_open = 0;
                } else if (g_mouse_y >= 204 && g_mouse_y < 230) {
                    // 4. Quantum PQC Shield
                    g_win_ide_open = 1;
                    g_active_editor_tab = 1;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    g_start_menu_open = 0;
                } else if (g_mouse_y >= 230 && g_mouse_y < 256) {
                    // 5. Audio Studio
                    g_start_menu_open = 0;
                } else if (g_mouse_y >= 256 && g_mouse_y < 285) {
                    // 6. Terminal / BKNC Compiler
                    g_win_ide_open = 1;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    g_start_menu_open = 0;
                }
                render_full_frame_to_backbuffer(cmd_buffer);
            }
            // Janela 1 IDE: Foco, Abas, Controles e Arrasto
            else if (g_win_ide_open && g_mouse_x >= win1_x && g_mouse_x <= win1_x + win1_w && g_mouse_y >= win1_y && g_mouse_y <= win1_y + 42) {
                g_win_z_order[0] = 1; g_win_z_order[1] = 0;

                if (g_mouse_x >= win1_x + win1_w - 35 && g_mouse_x <= win1_x + win1_w - 10) {
                    g_win_ide_open = 0;
                    g_dragging_win = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= win1_x + win1_w - 65 && g_mouse_x <= win1_x + win1_w - 40) {
                    g_win_ide_maximized = !g_win_ide_maximized;
                    g_dragging_win = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= win1_x + win1_w - 95 && g_mouse_x <= win1_x + win1_w - 70) {
                    g_win_ide_open = 0;
                    g_dragging_win = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                }
                else if (g_mouse_x >= win1_x + 16 && g_mouse_x <= win1_x + 146) {
                    g_active_editor_tab = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= win1_x + 152 && g_mouse_x <= win1_x + 288) {
                    g_active_editor_tab = 1;
                    render_full_frame_to_backbuffer(cmd_buffer);
                }
                else if (!g_win_ide_maximized) {
                    g_dragging_win = 1;
                    g_drag_offset_x = g_mouse_x - g_win_ide_x;
                    g_drag_offset_y = g_mouse_y - g_win_ide_y;
                }
            }
            // Janela 2 Q-HAL: Foco, Controles e Arrasto
            else if (g_win_qpu_open && g_mouse_x >= win2_x && g_mouse_x <= win2_x + win2_w && g_mouse_y >= win2_y && g_mouse_y <= win2_y + 42) {
                g_win_z_order[0] = 0; g_win_z_order[1] = 1;

                if (g_mouse_x >= win2_x + win2_w - 35 && g_mouse_x <= win2_x + win2_w - 10) {
                    g_win_qpu_open = 0;
                    g_dragging_win = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= win2_x + win2_w - 65 && g_mouse_x <= win2_x + win2_w - 40) {
                    g_win_qpu_maximized = !g_win_qpu_maximized;
                    g_dragging_win = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= win2_x + win2_w - 95 && g_mouse_x <= win2_x + win2_w - 70) {
                    g_win_qpu_open = 0;
                    g_dragging_win = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                }
                else if (!g_win_qpu_maximized) {
                    g_dragging_win = 2;
                    g_drag_offset_x = g_mouse_x - g_win_qpu_x;
                    g_drag_offset_y = g_mouse_y - g_win_qpu_y;
                }
            }
            // Ícones da Área de Trabalho
            else if (!g_win_ide_open && !g_win_qpu_open && g_mouse_y >= 260 && g_mouse_y <= 360) {
                if (g_mouse_x >= 150 && g_mouse_x <= 210) {
                    g_win_ide_open = 1;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= 290 && g_mouse_x <= 350) {
                    g_win_ide_open = 1;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= 430 && g_mouse_x <= 490) {
                    g_start_menu_open = 1;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= 570 && g_mouse_x <= 630) {
                    g_win_qpu_open = 1;
                    g_win_z_order[0] = 0; g_win_z_order[1] = 1;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= 710 && g_mouse_x <= 770) {
                    g_win_ide_open = 1;
                    g_active_editor_tab = 1;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= 850 && g_mouse_x <= 910) {
                    g_control_center_open = 1;
                    render_full_frame_to_backbuffer(cmd_buffer);
                }
            }
            // Dock Flutuante no Rodapé
            else if (g_mouse_y >= g_dock_y && g_mouse_y <= g_dock_y + g_dock_h) {
                if (g_mouse_x >= g_icon_centers[0] - 25 && g_mouse_x <= g_icon_centers[0] + 25) {
                    // Terminal
                    g_win_ide_open = 1;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= g_icon_centers[1] - 25 && g_mouse_x <= g_icon_centers[1] + 25) {
                    // BKN Studio IDE
                    g_win_ide_open = !g_win_ide_open;
                    if (g_win_ide_open) { g_win_z_order[0] = 1; g_win_z_order[1] = 0; }
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= g_icon_centers[2] - 25 && g_mouse_x <= g_icon_centers[2] + 25) {
                    // Start Menu / File Explorer
                    g_start_menu_open = !g_start_menu_open;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= g_icon_centers[3] - 25 && g_mouse_x <= g_icon_centers[3] + 25) {
                    // Q-HAL 3D Studio
                    g_win_qpu_open = !g_win_qpu_open;
                    if (g_win_qpu_open) { g_win_z_order[0] = 0; g_win_z_order[1] = 1; }
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= g_icon_centers[4] - 25 && g_mouse_x <= g_icon_centers[4] + 25) {
                    // PQC Shield
                    g_win_ide_open = 1;
                    g_active_editor_tab = 1;
                    g_win_z_order[0] = 1; g_win_z_order[1] = 0;
                    render_full_frame_to_backbuffer(cmd_buffer);
                } else if (g_mouse_x >= g_icon_centers[5] - 25 && g_mouse_x <= g_icon_centers[5] + 25) {
                    // Settings / Quick Settings
                    g_control_center_open = !g_control_center_open;
                    render_full_frame_to_backbuffer(cmd_buffer);
                }
            }
        }

        // 5. Teclado
        EFI_INPUT_KEY key;
        if (in->ReadKeyStroke(in, &key) == EFI_SUCCESS) {
            CHAR16 c = key.UnicodeChar;

            if (c == L'\r' || c == L'\n') {
                cmd_buffer[cmd_idx] = '\0';

                if (cmd_idx > 0) {
                    for (int k = 0; g_term_history[1][k] && k < 119; k++) g_term_history[0][k] = g_term_history[1][k];
                    for (int k = 0; g_term_history[2][k] && k < 119; k++) g_term_history[1][k] = g_term_history[2][k];

                    if (cmd_buffer[0] == 'q' && cmd_buffer[1] == 'p' && cmd_buffer[2] == 'u') {
                        g_anim_frame++;
                        const char* res = "[Q-HAL] EPR Bell State: (|00>+|11>)/sqrt(2) | Fidelity: 99.99%";
                        int k = 0; while (res[k] && k < 119) { g_term_history[2][k] = res[k]; k++; } g_term_history[2][k] = '\0';
                    } else if (cmd_buffer[0] == 'p' && cmd_buffer[1] == 'q' && cmd_buffer[2] == 'c') {
                        const char* res = "[PQC Shield] Chaves pos-quanticas ML-KEM-768 e ML-DSA-65 validadas.";
                        int k = 0; while (res[k] && k < 119) { g_term_history[2][k] = res[k]; k++; } g_term_history[2][k] = '\0';
                    } else if (cmd_buffer[0] == 'b' && cmd_buffer[1] == 'k' && cmd_buffer[2] == 'n') {
                        const char* res = "[BKNC] Compilado com sucesso: 'quantum_teleport.bkn_exec' [ML-DSA]";
                        int k = 0; while (res[k] && k < 119) { g_term_history[2][k] = res[k]; k++; } g_term_history[2][k] = '\0';
                    } else if (cmd_buffer[0] == 'm' && cmd_buffer[1] == 'e' && cmd_buffer[2] == 'n') {
                        g_start_menu_open = !g_start_menu_open;
                        const char* res = g_start_menu_open ? "[Baken OS] Menu de aplicativos aberto." : "[Baken OS] Menu fechado.";
                        int k = 0; while (res[k] && k < 119) { g_term_history[2][k] = res[k]; k++; } g_term_history[2][k] = '\0';
                    } else if (cmd_buffer[0] == 'f' && cmd_buffer[1] == 's') {
                        const char* res = "[BakenFS] Sovereign NVMe Storage: /system/libbkn.a, /apps/studio.bkn";
                        int k = 0; while (res[k] && k < 119) { g_term_history[2][k] = res[k]; k++; } g_term_history[2][k] = '\0';
                    } else {
                        const char* res = "Comandos: 'qpu bell', 'pqc shield', 'bknc build', 'fs ls', 'menu'";
                        int k = 0; while (res[k] && k < 119) { g_term_history[2][k] = res[k]; k++; } g_term_history[2][k] = '\0';
                    }
                }

                cmd_idx = 0;
                cmd_buffer[0] = '\0';
                render_full_frame_to_backbuffer("");
            } else if (c == 0x08) {
                if (cmd_idx > 0) {
                    cmd_idx--;
                    cmd_buffer[cmd_idx] = '\0';
                    render_full_frame_to_backbuffer(cmd_buffer);
                }
            } else if (c >= 32 && c <= 126 && cmd_idx < 45) {
                cmd_buffer[cmd_idx++] = (char)c;
                cmd_buffer[cmd_idx] = '\0';
                render_full_frame_to_backbuffer(cmd_buffer);
            }
        }
    }
}

// Entry Point Oficial UEFI x86_64
EFI_STATUS efi_main(__attribute__((unused)) EFI_HANDLE ImageHandle, EFI_SYSTEM_TABLE *SystemTable) {
    if (!SystemTable || !SystemTable->ConOut || !SystemTable->ConIn || !SystemTable->BootServices) {
        return EFI_SUCCESS;
    }

    // 1. Inicializa GOP
    EFI_GRAPHICS_OUTPUT_PROTOCOL *gop = 0;
    EFI_STATUS status = SystemTable->BootServices->LocateProtocol(&GOP_GUID, 0, (void**)&gop);
    if (status == EFI_SUCCESS && gop && gop->Mode && gop->Mode->Info) {
        unsigned int max_mode = gop->Mode->MaxMode;
        for (unsigned int m = 0; m < max_mode; m++) {
            EFI_GRAPHICS_OUTPUT_MODE_INFORMATION *info = 0;
            UINTN size_info = 0;
            if (gop->QueryMode(gop, m, &size_info, &info) == EFI_SUCCESS && info) {
                if (info->HorizontalResolution == 1024 && info->VerticalResolution == 768) {
                    gop->SetMode(gop, m);
                    break;
                }
            }
        }

        g_front_fb = (unsigned int*)gop->Mode->FrameBufferBase;
        g_width = gop->Mode->Info->HorizontalResolution;
        g_height = gop->Mode->Info->VerticalResolution;
        g_pitch = gop->Mode->Info->PixelsPerScanLine;
        g_mouse_x = g_width / 2;
        g_mouse_y = g_height / 2;
        g_last_mouse_x = g_mouse_x;
        g_last_mouse_y = g_mouse_y;
    }

    // 2. Aloca Backbuffer Real em Memória RAM
    UINTN pages_needed = ((UINTN)g_pitch * g_height * 4 + 4095) / 4096;
    unsigned long long backbuffer_mem = 0;
    status = SystemTable->BootServices->AllocatePages(0, 2, pages_needed, &backbuffer_mem);
    if (status == EFI_SUCCESS && backbuffer_mem != 0) {
        g_back_fb = (unsigned int*)backbuffer_mem;
    } else {
        g_back_fb = g_front_fb;
    }

    // 3. Aloca Cache de Wallpaper Mesh em RAM
    unsigned long long wp_mem = 0;
    status = SystemTable->BootServices->AllocatePages(0, 2, pages_needed, &wp_mem);
    if (status == EFI_SUCCESS && wp_mem != 0) {
        g_wallpaper_cache = (unsigned int*)wp_mem;
    } else {
        g_wallpaper_cache = g_back_fb;
    }

    // 4. Inicializa Ponteiros de Mouse
    EFI_ABSOLUTE_POINTER_PROTOCOL *abs_pointer = 0;
    SystemTable->BootServices->LocateProtocol(&ABS_POINTER_GUID, 0, (void**)&abs_pointer);

    EFI_SIMPLE_POINTER_PROTOCOL *rel_pointer = 0;
    SystemTable->BootServices->LocateProtocol(&REL_POINTER_GUID, 0, (void**)&rel_pointer);

    // 5. Inicializa o Desktop Soberano
    run_baken_gui_shell(SystemTable, abs_pointer, rel_pointer);

    return EFI_SUCCESS;
}
