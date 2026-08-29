// Baken OS - UI Components (BakenFX)
// Implementação Orientada a Objetos para Elementos Visuais do Desktop

module kernel::baken_ui_oop;

import kernel::graphics_engine::*;
import kernel::baken_rasterizer::*;
import kernel::baken_animation::*;

pub class UIElement {
    pub mut x: i32 = 0;
    pub mut y: i32 = 0;
    pub mut width: u32 = 0;
    pub mut height: u32 = 0;
    pub mut is_visible: bool = true;

    pub fn draw() -> void {
        // Base virtual method
    }

    pub fn on_click(mx: i32, my: i32) -> bool {
        if (mx >= this.x && mx <= this.x + (this.width as i32) &&
            my >= this.y && my <= this.y + (this.height as i32)) {
            return true;
        }
        return false;
    }
}

pub class Window extends UIElement {
    pub mut title: *const u8 = null as *const u8;
    pub mut bg_color: u32 = 0xAA222222; // Vidro escuro translúcido
    pub mut is_active: bool = false;
    
    // Animação de Spring para a janela (bounce no startup)
    pub mut scale_spring: SpringState = SpringState {
        current_val: 0.0,
        target_val: 1.0,
        velocity: 0.0,
        stiffness: 200.0,
        damping: 15.0
    };

    pub fn update(dt: f32) -> void {
        spring_update(&mut this.scale_spring, dt);
    }

    pub override fn draw() -> void {
        if (!this.is_visible) { return; }

        let scale = this.scale_spring.current_val;
        if (scale <= 0.01) { return; } // Invisível

        let scaled_w = (this.width as f32 * scale) as u32;
        let scaled_h = (this.height as f32 * scale) as u32;
        let offset_x = (this.width - scaled_w) / 2;
        let offset_y = (this.height - scaled_h) / 2;

        let draw_x = (this.x as u32) + offset_x;
        let draw_y = (this.y as u32) + offset_y;

        // Animação usa Elevação Dinâmica
        let target_elevation = if (this.is_active) { ELEVATION_WINDOW_ACTIVE } else { ELEVATION_WINDOW_INACTIVE };
        let current_elevation = (target_elevation as f32 * scale) as u32;

        // Fundo Mica Dark com Sombra Física
        gfx_draw_smart_material(draw_x, draw_y, scaled_w, scaled_h, MATERIAL_MICA, current_elevation, 12);

        // 3. Barra de Título
        gfx_fill_rect_alpha(draw_x, draw_y, scaled_w, 30, 0x00000000, 100);

        // 4. Botões de Controle (Mac-style)
        let btn_y = draw_y + 15;
        gfx_draw_circle_button(draw_x + 20, btn_y, 6, 0xFFFF5F56); // Fechar (Vermelho)
        gfx_draw_circle_button(draw_x + 40, btn_y, 6, 0xFFFFBD2E); // Minimizar (Amarelo)
        gfx_draw_circle_button(draw_x + 60, btn_y, 6, 0xFF27C93F); // Maximizar (Verde)

        // 5. Título
        if (this.title != null as *const u8) {
            gfx_draw_text(draw_x + 80, draw_y + 9, this.title, 0xFFFFFFFF);
        }
    }
}

pub class Button extends UIElement {
    pub mut text: *const u8 = null as *const u8;
    pub mut bg_color: u32 = 0x88444444;
    pub mut hover_color: u32 = 0xAA666666;
    pub mut is_hovered: bool = false;

    pub override fn draw() -> void {
        if (!this.is_visible) { return; }

        let draw_x = this.x as u32;
        let draw_y = this.y as u32;
        let color = if (this.is_hovered) { this.hover_color } else { this.bg_color };

        gfx_draw_glass_rect(draw_x, draw_y, this.width, this.height, color, 200, 0x55FFFFFF, 6);

        if (this.text != null as *const u8) {
            // Centralizar texto (aproximado, assumindo fonte 8x12)
            // Aqui precisaríamos de strlen, vamos usar um offset fixo para simplificar
            gfx_draw_text(draw_x + 10, draw_y + (this.height / 2) - 6, this.text, 0xFFFFFFFF);
        }
    }
}

pub class DesktopDock {
    pub mut y_offset: u32 = 20;
    pub mut icon_size: u32 = 48;
    pub mut item_count: u32 = 0;
    
    // Arrays fixos para simplicidade no bootloader
    pub mut item_labels: [*const u8; 10] = [null as *const u8; 10];
    pub mut item_springs: [SpringState; 10] = [SpringState {
        current_val: 1.0,
        target_val: 1.0,
        velocity: 0.0,
        stiffness: 150.0,
        damping: 10.0
    }; 10];

    pub fn add_item(label: *const u8) -> void {
        if (this.item_count < 10) {
            this.item_labels[this.item_count as usize] = label;
            this.item_count += 1;
        }
    }

    pub fn update(dt: f32, mouse_x: i32, mouse_y: i32) -> void {
        let sw = gfx_get_width();
        let sh = gfx_get_height();
        let dock_width = this.item_count * (this.icon_size + 15) + 15;
        let start_x = (sw - dock_width) / 2;
        let dock_y = sh - this.icon_size - this.y_offset;

        for mut i in 0 .. this.item_count {
            let item_x = start_x + 15 + i * (this.icon_size + 15);
            let center_x = (item_x + this.icon_size / 2) as i32;
            let center_y = (dock_y + this.icon_size / 2) as i32;

            let is_hover = (mouse_x >= item_x as i32 && mouse_x <= (item_x + this.icon_size) as i32 &&
                            mouse_y >= dock_y as i32 && mouse_y <= (dock_y + this.icon_size) as i32);

            let mag = calculate_dock_magnify(mouse_x, center_x, 150);
            
            // Se o mouse não está perto do dock no eixo Y, cancela o magnify
            let dist_y = abs_i32(mouse_y - center_y);
            let final_mag = if (dist_y > 100) { 1.0 } else { mag };

            this.item_springs[i as usize].target_val = final_mag;
            spring_update(&mut this.item_springs[i as usize], dt);
        }
    }

    pub fn draw() -> void {
        let sw = gfx_get_width();
        let sh = gfx_get_height();
        
        if (this.item_count == 0) { return; }

        // Desenha o fundo da Dock (Pill)
        let dock_width = this.item_count * (this.icon_size + 15) + 15;
        let dock_height = this.icon_size + 15;
        let dock_x = (sw - dock_width) / 2;
        let dock_y = sh - dock_height - 5; // Margem inferior

        // Fundo da dock: Acrílico transitório no nível DOCK
        gfx_draw_smart_material(dock_x, dock_y, dock_width, dock_height, MATERIAL_ACRYLIC, ELEVATION_DOCK, dock_height / 2);

        // Cores dos cartões dos aplicativos soberanos
        let icon_bg_colors: [u32; 6] = [0x0038BDF8, 0x000284C7, 0x00818CF8, 0x000EA5E9, 0x0010B981, 0x00F59E0B];

        // Desenha os ícones com Magnify (Spring Scale)
        for mut i in 0 .. this.item_count {
            let scale = this.item_springs[i as usize].current_val;
            let current_size = (this.icon_size as f32 * scale) as u32;
            
            let item_x = dock_x + 15 + i * (this.icon_size + 15) + (this.icon_size - current_size) / 2;
            let item_y = dock_y + 7 + (this.icon_size - current_size); // Alinha pela base

            let bg_col = icon_bg_colors[i as usize % 6];
            let icon_elevation = (ELEVATION_CARD as f32 * scale) as u32;

            // Gravidade no ícone (Sombra se desloca no eixo Z ao fazer hover)
            gfx_draw_physical_shadow(item_x, item_y, current_size, current_size, icon_elevation);
            gfx_draw_glass_rect(item_x, item_y, current_size, current_size, bg_col, 230, 0x00FFFFFF, 12);
            let icon_pad = if (current_size > 32) { (current_size - 32) / 2 } else { 0 };
            gfx_draw_app_icon(item_x + icon_pad, item_y + icon_pad, 32, i);
        }
    }
}
