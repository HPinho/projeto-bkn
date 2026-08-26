# Especificação da Engine de Aplicações e Ports (Baken App Engine)
Versão: 1.0.0-PROD
Arquitetura: Sandboxing Baseado em Capabilities, Wasm-Direct e Vulkan/DRM Compositor

---

## 1. Visão Geral
O **Baken App Engine** é a camada de execução de aplicações de usuário do Baken OS. Ele permite executar com máxima performance:
1. **Aplicações Nativas BKN (.bkn_exec):** Código compilado diretamente pelo `bknc` com acesso nativo ao Q-HAL e BakenFS.
2. **Ports de Produtividade & Jogos:** Suítes de escritório (Office), navegadores web modernos, ferramentas de mídia e engines de jogos 3D via Vulkan direto sem sobrecarga de APIs legadas do Windows (Win32) ou Linux (X11/Wayland).
3. **Isolamento de Segurança:** Toda aplicação roda em uma Sandbox isolada com memória virtual exclusiva alocada pelo VMM e canais IPC monitorados por Capabilities.

---

## 2. O Compositor Gráfico Baken (`bkn-compositor`)
- **Direct-to-Display DRM:** O compositor gráfico comunica-se diretamente com o framebuffer GOP ou driver de GPU acelerado por hardware, eliminando servidores intermediários lentos.
- **Double-Buffering & V-Sync:** Taxas de atualização fluidas de 60 a 144 Hz com renderização livre de screen tearing.
- **Estética Aero-Quantum Glassmorphic:** Efeitos de refração de luz, desfoque gaussiano em tempo real e sombreamento volumétrico.
