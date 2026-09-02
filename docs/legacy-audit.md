# Auditoria do legado — lowering Sotlas nativo

## Rota executável atual

`UEFI -> kernel::main -> desktop_compositor -> desktop_shell -> window_manager`

O compilador resolve os quinze módulos ativos, gera uma interface e uma unidade
C para cada AST Sotlas e compila objetos separados. `baken_kernel_all.c` foi
removido; sua implementação duplicada não participa mais do build nem dos testes.

`kernel/src/baken_runtime.c` é um adaptador de plataforma, não uma camada de UI.
Ele somente traduz teclado/mouse UEFI, mede a duração dos quadros, limita a
cadência a aproximadamente 60 Hz e vincula os atlas à API pública Sotlas.

## Separação de responsabilidades verificada

| Camada | Responsabilidade | Desenha UI |
|---|---|---|
| `boot/uefi_bootloader.sotlas` | descoberta de hardware e handoff | não |
| `tools/sotlas_compile/compiler.py` | grafo, interfaces, lowering e link | não |
| `tools/sotlas_compile/bootstrap.py` | lexer, AST, tipos e emissão C genérica | não |
| `graphics_engine.sotlas` | framebuffer e double buffering | pixels apenas |
| `baken_rasterizer.sotlas` | primitivas, texto, materiais e wallpaper | sim |
| `baken_ui_oop.sotlas` | layout/animação do dock | sim |
| `window_manager.sotlas` | janelas e despacho de apps | sim |
| `desktop_shell.sotlas` | topbar, dock, cursor e quadro | sim |

Um teste de arquitetura rejeita `gfx_*`, `draw_*`, `wallpaper`, `dock`, `tela`
ou `screen` em `compiler.py`, e também rejeita o retorno da ponte monolítica.

## Armazenamento

Os testes de layout GPT/FAT32/BakenFS agora validam diretamente
`tools/scripts/create_installed_disk.py`, incluindo LBA 86016, magic, entradas,
preferências e notas. Eles não tratam mais uma ponte de UI removida como fonte
de verdade do formato em disco.

O gerador opera apenas em imagens dentro de `build/`. Isso não equivale a um
particionador seguro para disco físico. A UI do instalador em Sotlas apresenta
o fluxo planejado; gravação real em hardware exige backend Block I/O separado,
testes de falha e proteção explícita da mídia de origem.

## Limites ainda válidos

- A produção do PE/COFF deve usar o toolchain UEFI do projeto; um linker ELF
  comum não aceita `--subsystem,10`.
- QEMU e VirtualBox continuam sendo validações necessárias antes de publicar ISO.
- NVMe/AHCI completos, instalação em disco físico, rede e processos user-mode
  não devem ser anunciados enquanto não tiverem implementação e testes próprios.

## Critério para novos subsistemas

Um subsistema só entra na rota canônica com testes de sucesso e falha, import
explícito no grafo Sotlas e validação de execução em VM. Código de ferramenta
não pode sintetizar interface específica de produto.
