#pragma once

/* Baken Lua Design System v1. Consulte docs/baken_lua_design_system.md.
 * Valores em pixels lógicos na prancha 1440x900. */
#define BKN_DESIGN_BASE_WIDTH       1440u
#define BKN_DESIGN_BASE_HEIGHT       900u
#define BKN_TEXT_AUXILIARY            12u
#define BKN_TEXT_BODY                 14u
#define BKN_TEXT_LABEL                14u
#define BKN_TEXT_TITLE                16u
#define BKN_TEXT_WINDOW               20u
#define BKN_TEXT_DISPLAY              32u
#define BKN_TEXT_NUMERIC              32u

/* Papéis de texto estáveis. O chamador escolhe hierarquia, nunca um tamanho
 * isolado; o rasterizador escolhe então o atlas Google Sans Flex adequado. */
#define BKN_TYPE_CAPTION                0u
#define BKN_TYPE_BODY                   1u
#define BKN_TYPE_LABEL                  2u
#define BKN_TYPE_TITLE                  3u
#define BKN_TYPE_WINDOW                 4u
#define BKN_TYPE_DISPLAY                5u
#define BKN_TYPE_NUMERIC                6u
#define BKN_ICON_SYSTEM               20u
#define BKN_ICON_WIDGET               32u
#define BKN_ICON_DOCK                 40u
#define BKN_ICON_DESKTOP              48u
#define BKN_ICON_REST                   0u
#define BKN_ICON_HOVER                  1u
#define BKN_ICON_PRESSED                2u
#define BKN_ICON_SELECTED               3u
#define BKN_ICON_DISABLED               4u
#define BKN_ICON_DESTRUCTIVE            5u
#define BKN_SPACE_1                    4u
#define BKN_SPACE_2                    8u
#define BKN_SPACE_3                   12u
#define BKN_SPACE_4                   16u
#define BKN_SPACE_5                   24u
#define BKN_SPACE_6                   32u
#define BKN_RADIUS_CONTROL            12u
#define BKN_RADIUS_CARD               18u
#define BKN_RADIUS_WINDOW             24u
#define BKN_RADIUS_DOCK               24u

/* Movimento Baken Lua. Os valores organizam feedback imediato, transição de
 * componente e transição de superfície; animações devem preservar contexto
 * espacial, nunca apenas decorar uma troca de tela. */
#define BKN_MOTION_FEEDBACK_MS         83u
#define BKN_MOTION_COMPONENT_MS       167u
#define BKN_MOTION_SURFACE_MS         250u
#define BKN_MOTION_WINDOW_MS          333u
#define BKN_MOTION_SPRING_STIFFNESS  150.0f
#define BKN_MOTION_SPRING_DAMPING     10.0f

/* Papéis semânticos: shells e apps usam estes IDs, não combinações livres
 * de RGB/alpha. A interpretação pertence exclusivamente ao BakenFX 2D. */
#define BKN_LUA_CANVAS                 0u
#define BKN_LUA_MICA                   1u
#define BKN_LUA_GLASS_REGULAR          2u
#define BKN_LUA_GLASS_CLEAR            3u
#define BKN_LUA_ELEVATED               4u
#define BKN_LUA_SMOKE                  5u

#define BKN_LUA_REST                   0u
#define BKN_LUA_HOVER                  1u
#define BKN_LUA_PRESSED                2u
#define BKN_LUA_FOCUS                  3u
#define BKN_LUA_SELECTED               4u
#define BKN_LUA_DISABLED               5u

/* A escala e configuravel pelo shell; o padrao automatico fica entre
 * 80% (VM pequena) e 200% (painel 2880x1800). */
