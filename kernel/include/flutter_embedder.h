/*
 * Baken OS - Flutter Custom Embedder API (flutter_embedder.h)
 * Definições oficiais da API C do Flutter Engine para Sistemas Operacionais Soberanos.
 */

#ifndef BAKEN_FLUTTER_EMBEDDER_H
#define BAKEN_FLUTTER_EMBEDDER_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    kFlutterEngineSuccess = 0,
    kFlutterEngineInvalidArguments = 1,
    kFlutterEngineInternalError = 2,
} FlutterResult;

typedef enum {
    kOpenGL = 0,
    kSoftware = 1,
    kVulkan = 2,
} FlutterRendererType;

// Callback de apresentação de frame no Framebuffer físico do Baken OS
typedef bool (*FlutterSoftwarePresentCallback)(void* user_data, const void* allocation, size_t row_bytes, size_t height);

typedef struct {
    size_t struct_size;
    FlutterSoftwarePresentCallback present_view_callback;
} FlutterSoftwareRendererConfig;

typedef struct {
    FlutterRendererType type;
    union {
        FlutterSoftwareRendererConfig software;
    };
} FlutterRendererConfig;

typedef struct {
    size_t struct_size;
    const char* assets_path;
    const char* icu_data_path;
    const char* isolate_snapshot_data;
    size_t isolate_snapshot_data_size;
    const char* vm_snapshot_data;
    size_t vm_snapshot_data_size;
    int custom_dart_entrypoint_argc;
    const char* const* custom_dart_entrypoint_argv;
} FlutterProjectArgs;

typedef struct {
    size_t struct_size;
    size_t width;
    size_t height;
    double pixel_ratio;
} FlutterWindowMetricsEvent;

typedef enum {
    kPointerPhaseDown = 0,
    kPointerPhaseMove = 1,
    kPointerPhaseUp = 2,
    kPointerPhaseCancel = 3,
} FlutterPointerPhase;

typedef struct {
    size_t struct_size;
    FlutterPointerPhase phase;
    double x;
    double y;
    int64_t timestamp;
} FlutterPointerEvent;

typedef void* FlutterEngine;

// Funções da API do Embedder
FlutterResult FlutterEngineRun(
    size_t version,
    const FlutterRendererConfig* config,
    const FlutterProjectArgs* args,
    void* user_data,
    FlutterEngine* engine_out
);

FlutterResult FlutterEngineShutdown(FlutterEngine engine);

FlutterResult FlutterEngineSendWindowMetricsEvent(
    FlutterEngine engine,
    const FlutterWindowMetricsEvent* event
);

FlutterResult FlutterEngineSendPointerEvent(
    FlutterEngine engine,
    const FlutterPointerEvent* events,
    size_t events_count
);

#ifdef __cplusplus
}
#endif

#endif // BAKEN_FLUTTER_EMBEDDER_H
