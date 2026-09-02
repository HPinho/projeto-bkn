# Auditoria visual e de movimento — Baken OS

Esta revisão trata a baixa nitidez percebida, os quadros interrompidos e as
trocas secas do installer/OOBE na rota que realmente gera o `BOOTX64.EFI`.
A meta não é copiar a interface da Apple, mas aplicar os mesmos princípios de
movimento: tempo real, continuidade, curvas sem quina, estabilidade sob carga
e apresentação somente depois que o quadro está completo.

## Diagnóstico e correções

### 1. O GOP podia permanecer em 4K sem double buffer

O seletor iniciava `best_area` com a área do modo já aberto pelo firmware. Se a
VM começasse em 4K, nenhum modo limitado poderia superar esse valor. O sistema
permanecia fora do orçamento do backbuffer, desenhando diretamente no GOP e
expondo cada etapa do rasterizador.

Agora a busca começa em zero e escolhe de forma determinística o maior modo
BGRX de até 1920×1200. O modo original só permanece quando não há candidato
compatível.

### 2. A duração dependia da velocidade da CPU

O loop usava uma espera ocupada de 40.000 iterações e fornecia `dt = 0.016`
mesmo quando o quadro demorava mais. Em QEMU/TCG, VirtualBox e hardware real, a
mesma animação apresentava velocidades diferentes.

O TSC agora é calibrado com `BootServices->Stall`. O compositor recebe o tempo
real do quadro, limitado a 50 ms para proteger a física, e é cadenciado para
aproximadamente 60 Hz quando existe orçamento.

### 3. O wallpaper consumia todos os quadros

Blooms, granulação, distâncias e divisões eram recalculados para cada pixel em
cada frame. O canvas agora é calculado uma vez por resolução/tema e restaurado
por cópia linear. Trocar o tema invalida o cache.

### 4. O blur tinha custo proporcional ao raio

As duas passagens reabriam a vizinhança inteira para cada pixel. Elas passaram
a usar somas de janela deslizante, reduzindo o custo de
`O(largura × altura × raio)` para `O(largura × altura)`.

### 5. Installer e OOBE usam transições contínuas

A versão Sotlas nativa mantém a etapa anterior, a direção e um relógio de
transição. A navegação passa por `installer_go_to`/`oobe_go_to` e usa
smoothstep para deslocar a nova superfície, eliminando a troca seca. Com a
cadência real do compositor, os 24 quadros da transição deixam de variar com a
velocidade da CPU.

### 6. Molas ficavam instáveis após um quadro lento

O integrador recebia um único passo. Agora `dt` é limitado e subdividido em
quatro passos semi-implícitos; o estado assenta no alvo quando erro e velocidade
ficam imperceptíveis.

### 7. O logotipo usava nearest-neighbor

Tamanhos diferentes do atlas apresentavam contornos em degraus. Logotipo e
alpha agora usam interpolação bilinear. O caminho de texto transparente também
decodifica UTF-8, preservando acentos no renderer suavizado.

## Arquivos alterados ou auditados

| Arquivo | Alteração |
| --- | --- |
| `boot/uefi_bootloader.sotlas` | Seleção GOP determinística dentro do orçamento. |
| `kernel/src/baken_animation.sotlas` | Curvas limitadas, smoothstep e molas com subpassos. |
| `kernel/src/baken_rasterizer.sotlas` | Reamostragem bilinear do logotipo. |
| `tools/sotlas_compile/compiler.py` | Runtime efetivo: relógio, cache, blur linear, UTF-8, molas e bilinear. |
| `kernel/src/baken_installer.sotlas` | Transição de etapas nativa preservada e verificada. |
| `kernel/src/baken_oobe_screen.sotlas` | Navegação OOBE com slide suavizado verificada. |
| `tests/test_visual_pipeline.py` | Contratos contra regressão visual e temporal. |
| `tests/test_storage_installer.py` | Contratos reconciliados com installer/OOBE Sotlas nativos. |
| `CMakeLists.txt` | Registro da suíte `visual_pipeline`. |
| `docs/architecture.md` | Orçamento de frame e rota de apresentação. |

O commit mais recente migrou installer e OOBE para Sotlas nativo. Esta auditoria
foi reconciliada sobre essa arquitetura: não reintroduz o renderer C anterior e
mantém `compiler.py` responsável apenas pelo runtime e pelo lowering necessários
à imagem EFI.

## Validação

```powershell
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas `
  --manifest build/sotlas-main.manifest.json
python -m unittest tests/test_visual_pipeline.py
python -m unittest tests/test_storage_installer.py tests/test_legacy_safety.py
```

Para gerar e abrir a imagem:

```powershell
.\run_baken.ps1
```

Valide 1280×720, 1600×900 e 1920×1080, observando:

- ausência de tearing durante o fade;
- duração semelhante em hosts rápidos e lentos;
- logo sem pixels em degrau em 36, 72 e 128 px;
- texto acentuado com cobertura uniforme;
- cursor responsivo durante cards com blur;
- mudança de tema sem resíduos do cache anterior.

As 15 unidades C geradas e o bootloader foram compilados com
`-Wall -Wextra -Werror`. Neste ambiente, somente a linkedição PE/COFF não pôde
ser concluída porque o `ld` Linux disponível não implementa `--subsystem`; no
Windows/MinGW do projeto, o build completo permanece o teste final obrigatório.

## Limites atuais

- O compositor continua 100% em software; 4K nativo a 60 fps depende de futura
  aceleração gráfica.
- Installer e OOBE já usam slide; crossfade/scale de uma superfície inteira
  ainda exige transformação global ou snapshots.
- O backend especial em Python deve ser substituído gradualmente pelo lowering
  real dos corpos Sotlas. Até lá, mudanças visuais precisam ser espelhadas no
  runtime emitido.
