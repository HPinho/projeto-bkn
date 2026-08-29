// Baken OS - Motor de Animação e Física em Cq (@system)
// Interpolação Bézier, Spring Physics para Dock Magnify e Transições de Janela

module kernel::baken_animation;

pub struct SpringState {
    pub current_val: f32;
    pub target_val: f32;
    pub velocity: f32;
    pub stiffness: f32;
    pub damping: f32;
}

pub struct DockIconAnim {
    pub scale: f32;
    pub glow_intensity: u8;
    pub bounce_offset: i16;
}

// Funcao auxiliar abs
@inline
fn abs_i32(x: i32) -> i32 {
    if (x < 0) { return -x; }
    return x;
}

// Fluent Design Easing: Fast Out, Slow In (Entrada) - cubic-bezier(0, 0, 0, 1)
// Aproximação polinomial para t em [0, 1]
@system
pub fn ease_fast_out_slow_in(t: f32) -> f32 {
    let inv = 1.0 - t;
    return 1.0 - (inv * inv * inv * inv); // 1 - (1-t)^4 (Fricção forte no final)
}

// Fluent Design Easing: Slow Out, Fast In (Saída) - cubic-bezier(1, 0, 1, 1)
// Aproximação polinomial para t em [0, 1]
@system
pub fn ease_slow_out_fast_in(t: f32) -> f32 {
    return t * t * t * t; // t^4 (Acelera rapidamente no final)
}

@system
pub fn spring_update(spring: *mut SpringState, dt: f32) -> f32 {
    unsafe {
        let force = -(*spring).stiffness * ((*spring).current_val - (*spring).target_val);
        let damping_force = -(*spring).damping * (*spring).velocity;
        let acceleration = force + damping_force;

        (*spring).velocity += acceleration * dt;
        (*spring).current_val += (*spring).velocity * dt;
        return (*spring).current_val;
    }
}

@system
pub fn calculate_dock_magnify(cursor_x: i32, icon_center_x: i32, max_radius: i32) -> f32 {
    let dist = abs_i32(cursor_x - icon_center_x);
    if (dist >= max_radius) {
        return 1.0;
    }
    let ratio = (max_radius - dist) as f32 / max_radius as f32;
    // Interpolação suave em sino (Gaussian Bell Curve aproximada)
    return 1.0 + (ratio * ratio * 0.45);
}
