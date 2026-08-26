# Especificação do Baken Shell Desktop & Window Manager
Versão: 1.0.0-PROD
Arquitetura: Compositor de Janelas em Árvore Z-Order com Menu Iniciar Glassmorphic e Central de Controle

---

## 1. Visão Geral
O **Baken Shell Desktop** é o ambiente gráfico definitivo do Baken OS. Ele fornece:
1. **Gerenciador de Janelas com Z-Order:** Múltiplas janelas sobrepostas que podem ser arrastadas com o mouse, minimizadas, maximizadas e focadas com transparência Alpha Blending.
2. **Menu Iniciar Aero-Quantum:** Painel suspenso translúcido com busca rápida, atalhos de ferramentas, monitoramento de saúde do microkernel e opções de energia.
3. **Central de Controle & Notificações:** Painel deslizante com status de Wi-Fi 7 MLO, túneis de segurança ML-KEM e controle de volume.

---

## 2. Estrutura do Estado de Janela (`BknWindowState`)

```
Campo                   Tamanho (Bytes)  Descrição
Window ID               4                Identificador único da janela no compositor
Posição X               4                Coordenada horizontal atual
Posição Y               4                Coordenada vertical atual
Largura (W)             4                Largura em pixels
Altura (H)              4                Altura em pixels
Z-Index                 2                Ordem de profundidade de sobreposição (0 = Fundo, 255 = Topo)
Flags de Estado         2                `BIT 0`: Focada, `BIT 1`: Minimizada, `BIT 2`: Maximizada, `BIT 3`: Arrastando
Título da Janela        32               String UTF-8 com o nome exibido na barra
```
