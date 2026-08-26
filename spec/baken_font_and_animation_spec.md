# Especificação de Tipografia Vetorial e Animações (BakenFont & BakenAnimation)
Versão: 1.0.0-SOVEREIGN
Arquitetura: Motor de Animação com Física Contínua e Rasterizador de Fontes Suaves em BKN Puro

---

## 1. BakenAnimation (Motor de Física e Interpolação)
O **BakenAnimation** implementa transições visuais com aceleração analítica em hardware:
1. **Curvas de Bézier Cúbicas (*Cubic Bezier Curves*):**
   * *Ease-In-Out:* $B(t) = (1-t)^3 P_0 + 3(1-t)^2 t P_1 + 3(1-t) t^2 P_2 + t^3 P_3$
   * Efeito *Magnify / Spring Physics* no Dock flutuante ao aproximar o cursor do mouse.
2. **Ciclo de Atualização a 60/120 FPS:**
   * Estados de interpolação atômicos armazenados por janela e por ícone.

---

## 2. BakenFont (Motor de Tipografia Suave)
1. **Anti-Aliasing Analítico (Subpixel Grayscale 8-bit):**
   * Transições de borda com suavização de alpha contínua de 0 a 255.
2. **Múltiplos Tamanhos de Escala:**
   * Títulos em 20px / 16px, Corpo em 14px e Rótulos em 11px.
