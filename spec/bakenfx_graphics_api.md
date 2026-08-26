# Especificação da API Gráfica Soberana BakenFX (Q-Render Graphics API)
Versão: 1.0.0-PROD
Arquitetura: API Gráfica de Baixa Latência e Próxima Geração em BKN Puro (Análoga a DirectX 12, Vulkan e Metal)

---

## 1. Visão Geral
A **BakenFX** é a API gráfica de baixo nível e alto desempenho do Baken OS. Ela substitui dependências externas por um pipeline gráfico em BKN puro com controle total do hardware:
1. **Command Buffers & Queues Assíncronas:** Gravação concorrente de comandos de desenho com submissão em lote (Zero Driver Overhead).
2. **Pipeline State Objects (PSO):** Compilação antecipada de estados de rasterização, alpha blending e shaders (`@vertex`, `@fragment`, `@compute`).
3. **Double Buffering & V-Sync:** Troca atômica de ponteiros de tela (*Page Flipping*) para eliminar qualquer *screen tearing* (cintilação) a 120 FPS.
4. **Compositor Glassmorphic por Hardware:** Shaders nativos para *Kawase Dual Blur*, atenuação de luz em sombras *Drop Shadow* e iluminação especular Aero-Quantum.

---

## 2. Estrutura do Pipeline Gráfico (`BknFxPipeline`)

```
Campo                   Tamanho (Bytes)  Descrição
Tipo de Topologia       1                `0x01`: Triângulos, `0x02`: Quads, `0x03`: Linhas, `0x04`: Pixels
Modo de Blending        1                `0x01`: Alpha Blend Linear, `0x02`: Aditivo, `0x03`: Multiplicativo
Antialiasing            1                `0x00`: Nenhum, `0x02`: MSAA 2x, `0x04`: MSAA 4x
Formato de Cor          1                `0x01`: B8G8R8A8_UNORM, `0x02`: R16G16B16A16_FLOAT
Raio de Blur (Kawase)   2                Número de passagens de desfoque gaussiano/kawase
Cor da Borda/Glow       4                Valor RGBA de iluminação externa (Halo Glow)
```
