# Especificação da Extensão Orientada a Objetos da Linguagem BKN (BKN OOP v2.0)
Versão: 2.0.0-PROD
Arquitetura: Classes, Interfaces, Herança Simples, Polimorfismo por V-Tables e Composição Reativa de Widgets

---

## 1. Visão Geral
Para permitir a construção de interfaces visuais de altíssima complexidade (análogas ao SwiftUI da Apple, WinUI 3 da Microsoft e Qt), a linguagem **BKN** incorpora suporte nativo de primeira classe à **Orientação a Objetos Soberana**:

1. **`class` & `extends`:** Definição de classes com atributos encapsulados, construtores e métodos com suporte a herança simples.
2. **`interface` & `implements`:** Contratos polimórficos com tabelas virtuais (*Zero-Cost V-Tables*) adequadas para ambientes bare-metal `@system`.
3. **Árvore de Widgets Reativa:** Hierarquia profunda de herança onde cada elemento visual é uma instância de um objeto especializado (`Widget` -> `Container` -> `GlassWindow` -> `IdeWindow`).
4. **Ciclo de Vida de Renderização e Eventos:** Métodos virtuais `layout(constraints)`, `paint(ctx: &mut RenderContext)` e `handle_event(event: UiEvent)`.

---

## 2. Sintaxe Oficial BKN OOP

```bkn
// Exemplo de Interface e Classes em BKN Puro
pub interface Renderable {
    fn paint(ctx: &mut RenderContext);
    fn layout(w: u32, h: u32);
}

pub class Widget implements Renderable {
    pub x: i32;
    pub y: i32;
    pub width: u32;
    pub height: u32;
    pub is_visible: bool;

    pub fn new(x: i32, y: i32, w: u32, h: u32) -> Self {
        return Widget {
            x: x,
            y: y,
            width: w,
            height: h,
            is_visible: true,
        };
    }

    pub fn paint(ctx: &mut RenderContext) {
        // Implementação base
    }

    pub fn layout(w: u32, h: u32) {
        self.width = w;
        self.height = h;
    }
}

pub class GlassWindow extends Widget {
    pub title: str;
    pub has_shadow: bool;
    pub border_glow: u32;

    pub fn new(title: str, x: i32, y: i32, w: u32, h: u32) -> Self {
        let mut win = GlassWindow {
            x: x,
            y: y,
            width: w,
            height: h,
            is_visible: true,
            title: title,
            has_shadow: true,
            border_glow: 0x0000E5FF,
        };
        return win;
    }

    pub override fn paint(ctx: &mut RenderContext) {
        ctx.draw_drop_shadow(self.x, self.y, self.width, self.height, 12);
        ctx.fill_glass_panel(self.x, self.y, self.width, self.height, 0x000B1021, 245, self.border_glow);
        ctx.draw_title_bar(self.x, self.y, self.width, 32, self.title);
    }
}
```
