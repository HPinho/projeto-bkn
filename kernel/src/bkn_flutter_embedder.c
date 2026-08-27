/*
 * Baken OS - Flutter Custom Embedder Implementation (x86_64)
 * Conecta o Motor C++ do Flutter (Dart VM + Skia/Impeller) ao Framebuffer do Kernel BKN.
 */

#include "../include/flutter_embedder.h"
#include <stdint.h>
#include <string.h>

// Ponteiros globais do Framebuffer fornecidos pelo Kernel BKN
extern uint32_t *g_fb_base;
extern uint32_t g_fb_width;
extern uint32_t g_fb_height;
extern uint32_t g_fb_pitch;

static FlutterEngine g_flutter_engine = NULL;

// Ponteiros dinâmicos para a biblioteca do Flutter Engine
typedef FlutterResult (*FlutterEngineRun_t)(size_t, const FlutterRendererConfig*, const FlutterProjectArgs*, void*, FlutterEngine*);
typedef FlutterResult (*FlutterEngineSendWindowMetricsEvent_t)(FlutterEngine, const FlutterWindowMetricsEvent*);
typedef FlutterResult (*FlutterEngineSendPointerEvent_t)(FlutterEngine, const FlutterPointerEvent*, size_t);

static FlutterEngineRun_t p_FlutterEngineRun = NULL;
static FlutterEngineSendWindowMetricsEvent_t p_FlutterEngineSendWindowMetricsEvent = NULL;
static FlutterEngineSendPointerEvent_t p_FlutterEngineSendPointerEvent = NULL;

// Callback de apresentação de frames: O Skia/Flutter rasteriza e chama esta função
static bool bkn_flutter_software_present(
    __attribute__((unused)) void* user_data,
    const void* allocation,
    size_t row_bytes,
    size_t height
) {
    if (!g_fb_base || !allocation) return false;

    const uint32_t *src = (const uint32_t*)allocation;
    uint32_t copy_width = (row_bytes / 4 < g_fb_width) ? (uint32_t)(row_bytes / 4) : g_fb_width;
    uint32_t copy_height = ((uint32_t)height < g_fb_height) ? (uint32_t)height : g_fb_height;

    // Copia os pixels rasterizados pelo Skia diretamente para o Framebuffer físico
    for (uint32_t y = 0; y < copy_height; y++) {
        uint32_t dst_offset = y * g_fb_pitch;
        uint32_t src_offset = y * (uint32_t)(row_bytes / 4);
        for (uint32_t x = 0; x < copy_width; x++) {
            g_fb_base[dst_offset + x] = src[src_offset + x];
        }
    }

    return true;
}

// Inicialização do Motor do Flutter no Baken OS
int bkn_flutter_embedder_init(const char *assets_path, const char *icu_data_path) {
    FlutterRendererConfig config;
    memset(&config, 0, sizeof(config));
    config.type = kSoftware;
    config.software.struct_size = sizeof(FlutterSoftwareRendererConfig);
    config.software.present_view_callback = bkn_flutter_software_present;

    FlutterProjectArgs args;
    memset(&args, 0, sizeof(args));
    args.struct_size = sizeof(FlutterProjectArgs);
    args.assets_path = assets_path ? assets_path : "data/flutter_assets";
    args.icu_data_path = icu_data_path ? icu_data_path : "data/icudtl.dat";
    args.isolate_snapshot_data = NULL;
    args.vm_snapshot_data = NULL;

    FlutterWindowMetricsEvent window_metrics;
    memset(&window_metrics, 0, sizeof(window_metrics));
    window_metrics.struct_size = sizeof(FlutterWindowMetricsEvent);
    window_metrics.width = g_fb_width;
    window_metrics.height = g_fb_height;
    window_metrics.pixel_ratio = 1.0;

    if (p_FlutterEngineRun) {
        FlutterResult res = p_FlutterEngineRun(1, &config, &args, NULL, &g_flutter_engine);
        if (res == kFlutterEngineSuccess && g_flutter_engine && p_FlutterEngineSendWindowMetricsEvent) {
            p_FlutterEngineSendWindowMetricsEvent(g_flutter_engine, &window_metrics);
            return 0;
        }
        return (int)res;
    }

    return 0; // Embedder preparado
}

// Despacho de Eventos de Mouse/Cursor para o Flutter
void bkn_flutter_send_mouse(double x, double y, int phase) {
    if (!g_flutter_engine || !p_FlutterEngineSendPointerEvent) return;

    FlutterPointerEvent event;
    memset(&event, 0, sizeof(event));
    event.struct_size = sizeof(FlutterPointerEvent);
    event.x = x;
    event.y = y;
    event.phase = (FlutterPointerPhase)phase;
    event.timestamp = 0;

    p_FlutterEngineSendPointerEvent(g_flutter_engine, &event, 1);
}
