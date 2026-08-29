# Baken Lua — plano de implementação visual

Este documento transforma a referência visual do Baken OS em um sistema de
design verificável. A interface não deve depender de ajustes isolados por tela:
tokens, componentes, assets e composição possuem um único contrato.

## 1. Governança de assets

- Manter apenas uma cópia canônica de cada pacote-fonte em `assets/`.
- Não extrair pacotes gigantes no repositório ou embuti-los integralmente na ISO.
- Criar um manifesto com nome semântico, origem, licença, variante e uso.
- Compilar somente os símbolos presentes no manifesto.
- Registrar toda dependência visual em `THIRD_PARTY_NOTICES.md`.
- Falhar o build quando um asset estiver ausente, duplicado ou sem licença.

Ionicons é a fonte canônica dos símbolos estáticos; Google Sans Flex é a fonte
canônica do texto. Os ZIPs Lottie/Morphicons ficam disponíveis exclusivamente
para estados animados. Nenhum pacote secundário entra no build.

## 2. Papéis visuais das bibliotecas

- **Ionicons filled:** ações, status, navegação, controles e aplicativos.
- **Morphicons/Lottie:** transições com significado, como play/pause, atualizar,
  expandir, confirmar e alternar estados.
- **Google Sans Flex:** tipografia variável inicial do sistema, com eixos
  adequados para hierarquia, largura e cantos arredondados.

Uma função não deve misturar famílias. O Ionicons sem sufixo é a variante
preenchida oficial; `outline` e `sharp` ficam fora do tema padrão.

## 3. Tokens Baken Lua

- Consolidar cor, tipografia, espaçamento, raio, elevação, opacidade e movimento.
- Proibir cores e coordenadas arbitrárias dentro dos componentes finais.
- Manter temas claro, escuro e alto contraste com os mesmos papéis semânticos.
- Definir escala lógica de 4 px e raios oficiais de controle, cartão e dock.
- Usar pixels lógicos no layout e pixels físicos somente na rasterização.

## 4. Tipografia

- Gerar Google Sans Flex em 12, 14, 16, 20, 24, 32, 48 e 64 px nativos.
- Preservar baseline, advance, kerning e altura de linha por estilo.
- Criar papéis `caption`, `body`, `label`, `title`, `display` e `numeric`.
- Implementar truncamento, quebra de linha e limite vertical no componente.
- Nunca posicionar texto por quantidade de espaços.

## 5. Sistema de ícones

- Selecionar inicialmente 80–120 ações realmente usadas pelo shell e apps.
- Preferir Ionicons sem sufixo como variante padrão do sistema.
- Gerar atlas 24, 32, 48, 64 e 96 px; nunca ampliar o atlas menor.
- Normalizar viewport, centro óptico, margem interna e espessura aparente.
- Criar estados rest, hover, pressed, selected, disabled e destructive.
- Manter fallback conhecido para builds sem o pacote-fonte.

## 6. Grade e responsividade

- Suportar 1024×768, 1440×900, 1920×1080 e 2880×1800.
- Validar escalas de 100%, 125%, 150%, 175% e 200%.
- Usar uma grade de 12 colunas para janelas e uma coluna fixa para widgets.
- Compartilhar a mesma geometria entre desenho, clique e acessibilidade.
- Definir tamanho mínimo; abaixo dele, ocultar conteúdo secundário em vez de
  comprimir coordenadas internas até ocorrer sobreposição.

## 7. Componentes e widgets

- Criar primitivas oficiais: superfície, cartão, botão de ícone, lista, badge,
  divisor, título, indicador, calendário e controle de mídia.
- Todos os cartões usam padding, título, baseline e gap derivados dos tokens.
- Calendários usam sete colunas matemáticas, não espaços em texto.
- Controles possuem hitbox mínima de 44×44 px lógicos, foco e estado pressionado.
- Conteúdo dinâmico sempre passa por elipse, wrapping ou clipping explícito.

## 8. Materiais e composição

- Compor em alpha premultiplicado e espaço de cor sRGB correto.
- Renderizar cada cartão/janela em camada off-screen recortada pelo seu raio.
- Aplicar blur gaussiano apenas ao conteúdo atrás do material.
- Construir sombras em passagens ambiente, contato e elevação.
- Usar ruído de baixa frequência para evitar banding sem sujar texto e ícones.
- Definir materiais oficiais: vidro claro, vidro escuro, mica, sólido e elevado.

## 9. Movimento

- Compilar SVG/Lottie no host; o kernel não interpreta JSON durante o boot.
- Usar tempo real ou passos adaptados ao custo do frame, nunca duração implícita.
- Limitar movimento a feedback, continuidade espacial e mudança de estado.
- Oferecer modo de movimento reduzido.
- Alvos iniciais: play/pause, anterior/próximo, refresh, settings e notificações.

## 10. Qualidade e acessibilidade

- Contraste mínimo WCAG AA para textos e controles essenciais.
- Navegação completa por teclado, foco visível e hitboxes consistentes.
- Testes de textos longos, ausência de dados, números máximos e idiomas diferentes.
- Nenhum texto ou ícone pode ultrapassar o clipping de seu componente.
- Capturas douradas automatizadas por resolução e estado interativo.

## 11. Orçamento de desempenho

- Medir custo de wallpaper, blur, sombras, texto, ícones e cópia do framebuffer.
- Invalidar somente regiões alteradas quando o compositor permitir.
- Compartilhar atlas e superfícies; proibir cópias por componente.
- Definir orçamento inicial de 33 ms por quadro em VM e 16,7 ms em hardware.
- Registrar memória ocupada por cada atlas e rejeitar crescimento não justificado.

## 12. Portões de conclusão

Uma tela só é considerada pronta quando:

1. Compila sem warnings e inicia pela ISO e pelo disco instalado.
2. Não apresenta sobreposição nas quatro resoluções-alvo.
3. Desenho e hitbox usam a mesma geometria.
4. Texto, ícones, materiais e movimento usam os tokens oficiais.
5. Estados rest, hover, pressed, focus e disabled foram testados.
6. A captura dourada está dentro do limite visual aprovado.
7. O consumo de memória e tempo de quadro está dentro do orçamento.
