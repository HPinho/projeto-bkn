# Baken Lua Design System

Status: canônico — versão 1.0.

## Propósito

Baken Lua é a linguagem visual e de interação do Baken OS: luminosa, calma e técnica.

Esta especificação é a fonte de verdade. Nenhuma tela introduz cor, raio, sombra, duração ou comportamento sem token semântico aprovado aqui.

## Princípios

1. Clareza antes de efeito: conteúdo e foco continuam legíveis sem blur.
2. Profundidade tem significado: cada material pertence a uma camada fixa.
3. Vidro é escasso: reservado para navegação e superfícies flutuantes.
4. Um sistema: desktop, instalador e apps usam tokens e estados iguais.
5. Movimento explica mudança: origem, destino, duração e causa são claros.
6. Escala é lógica: layout usa pixels lógicos; assets usam atlas nativo.

## Camadas

| Nível | Material | Uso |
|---:|---|---|
| 0 | Lua Canvas | wallpaper e fundo |
| 1 | Lua Mica | janela e conteúdo persistente |
| 2 | Lua Glass | barra, dock, popover e card elevado |
| 3 | Lua Elevated | seleção e janela focada |
| 4 | Lua Focus | foco, hover e execução |
| 5 | Lua Smoke | bloqueio modal |

Backdrop blur é amostrado antes da superfície e recortado pela mesma máscara arredondada. Sombra fica fora da máscara; material, borda e conteúdo ficam dentro dela. O frame é apresentado apenas depois do double-buffer completo.

## Tokens

Todos os valores são pixels lógicos na prancha 1440×900 e passam por `ui_px`.

| Família | Valores |
|---|---|
| space | 4, 8, 12, 16, 24, 32 |
| radius | control 12, card 18, window 24, dock 24 |
| ícones | sistema 20, controle 24, widget 32, dock 40, desktop 48 |

### Tipografia Google Sans Flex

| Papel | Tamanho / linha | Peso |
|---|---|---|
| Caption | 12 / 16 | Regular |
| Body | 14 / 20 | Regular |
| Body Strong | 14 / 20 | Semibold |
| Subtitle | 16 / 22 | Semibold |
| Window Title | 20 / 26 | Semibold |
| Title | 24 / 32 | Semibold |
| Display | 32 / 40 | Semibold |

## Cor e materiais

Cor é semântica: `text-primary`, `text-secondary`, `surface-base`, `surface-raised`, `action-primary`, `selection`, `success`, `warning`, `danger`, `separator` e `focus-ring`.

Cada papel terá variante Light, Dark e High Contrast. Contraste mínimo é 4.5:1 para Body/controles e 3:1 para texto ou ícone grande. Cor sozinha nunca comunica estado.

| Material | Opacidade | Blur | Uso |
|---|---:|---:|---|
| Lua Canvas | 100% | não | fundo |
| Lua Mica | 92–98% | não | conteúdo persistente |
| Lua Glass Regular | 72–86% | 4–8 px | navegação e cards com texto |
| Lua Glass Clear | 48–68% | 4–8 px | mídia, uso raro |
| Lua Elevated | 88–96% | não | seleção/foco |
| Lua Smoke | preto 42–56% | não | modal |

## Estados e movimento

Todo componente implementa `rest`, `hover`, `pressed`, `focus`, `selected`, `disabled` e, quando aplicável, `running` e `danger`.

Hover usa elevação/halo; Pressed reduz elevação; Focus tem anel independente de cor; Disabled não captura entrada; Running usa indicador discreto.

| Classe | Duração | Curva | Uso |
|---|---:|---|---|
| instant | 83 ms | ease-out | pressed e toggle |
| fast | 167 ms | ease-out | hover e menu |
| normal | 250 ms | ease-out | abrir card/janela |
| dismiss | 167 ms | ease-in | fechar |
| spring | 250–350 ms | amortecida | dock |

Entrada desacelera; saída acelera. Reduzir movimento desativa spring, parallax e transições não essenciais.

## DPI, acessibilidade e contrato

- Testes obrigatórios: 1024×768, 1440×900 e 2880×1800; escalas 80–250%.
- Alvo mínimo: 32 px lógico; dock prefere 40 px.
- Todo fluxo funciona por teclado; foco é sempre visível.
- Alto contraste, transparência reduzida, movimento reduzido e escala são preferências do sistema, não de um único app.
- Tokens públicos vivem em `kernel/include/baken_design_tokens.h`.
- Somente BakenFX 2D desenha materiais, blur, alpha, sombras, texto e ícones.
- Apps pedem componentes semânticos; não desenham pixels ou cores arbitrárias.
- Um componente novo exige tokens, estados, foco, redução de movimento e screenshot de validação antes de entrar na ISO.

## Aceite Baken Lua 1.0

- Sem vazamento de blur, banding perceptível ou borda retangular fora de máscara.
- Desktop, instalador, Arquivos e Notas usam materiais e tipografia iguais.
- Ícones ficam nítidos em 100%, 150% e 200%.
- Foco e seleção não dependem apenas de cor.
- Desktop utilizável em 1024×768 e confortável em 2880×1800.

## Implementação atual: fundações 1–3

- **Geometria:** dock e grade de aplicativos possuem contratos únicos; os
  mesmos limites são usados para desenho, foco e clique. A grade reserva o
  espaço do painel de widgets antes de decidir colunas, células e ícones.
- **Elevação:** superfícies semânticas escolhem a própria sombra por nível.
  A elevação combina lobo ambiente e lobo de contato, com deslocamento menor
  para `pressed` e maior para `hover`, evitando sombras arbitrárias por tela.
- **Materiais:** Mica, Glass Regular, Glass Clear, Elevated e Smoke são
  compostos pela API BakenFX. Cada um define alpha, blur, borda, realce
  superior e oclusão inferior, em vez de cada aplicativo desenhar vidro à mão.

Esses contratos são a base para as próximas fases: componentes completos,
tipografia refinada, animação e preferências de acessibilidade.
