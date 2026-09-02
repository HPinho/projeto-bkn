# Lowering Sotlas nativo — relatório de alterações

Esta mudança remove a última implementação visual paralela da cadeia de build.
O compilador agora transforma o AST de cada módulo Sotlas em C11 genérico; ele
não conhece wallpaper, dock, janelas ou telas do Baken OS.

## O que mudou

- `graphics_engine.sotlas`: lowering real, backbuffer de alta resolução,
  apresentação atômica do quadro e snapshot/composição de transições.
- `baken_rasterizer.sotlas`: lowering real, acesso corrigido aos atlas,
  cache do wallpaper por resolução e cópia linear nos quadros seguintes.
- `baken_animation.sotlas`: lowering real das curvas smootherstep e molas com
  subpassos e limite de `dt` para quadros atrasados.
- `baken_ui_oop.sotlas`: o protótipo de classes não executado foi substituído
  pelo componente procedural real do dock, compatível com o frontend atual.
- `window_manager.sotlas`: lowering real de criação, foco, arraste,
  redimensionamento, renderização e despacho dos aplicativos.
- `desktop_shell.sotlas`: lowering real, frame delta limitado, atualização das
  molas em cada quadro, bounce do dock e conexão de todas as rotas de janela.
- `main.sotlas` e `desktop_compositor.sotlas`: agora são a entrada e a fachada
  efetivamente compiladas, sem um segundo `baken_kernel_main` em C.
- `baken_runtime.c`: adaptador não visual para eventos UEFI, frame pacing e
  ligação dos atlas de fonte/logo. Descobre separadamente os protocolos de
  ponteiro simples e absoluto, sem inferir seus layouts.

Os buffers estáticos são dimensionados para 1920×1200, o mesmo teto aplicado
pelo bootloader. Backbuffer, snapshot de transição e cache de wallpaper ocupam
cerca de 28 MiB no total, em vez de reservar memória para um modo que a rota
canônica nunca seleciona.

## Mudanças no frontend

O bootstrap ganhou interfaces C derivadas da AST, imports por cabeçalho,
constantes válidas para tamanhos de array, acesso correto a membros de ponteiro,
atribuições de arrays zerados, `loop {}` e retorno `!`. A análise semântica agora
visita expressões aninhadas, argumentos, condições, retornos e atribuições.

Os milhares de linhas de C visual específico foram removidos de
`tools/sotlas_compile/compiler.py`. O arquivo apenas coordena resolução,
interfaces, emissão, compilação e linkedição.

## Ponte e armazenamento

`kernel/src/baken_kernel_all.c` foi removido. O histórico continua recuperável
no Git. Os testes BakenFS foram transferidos para o gerador que realmente define
o disco instalado, `tools/scripts/create_installed_disk.py`, e verificam o
layout binário produzido.

## Proteção contra regressão

`tests/test_compiler_ui_boundary.py` falha se o compilador voltar a conter
`gfx_*`, `draw_*`, wallpaper, dock, tela ou screen, se o preâmbulo bootstrap
voltar a declarar UI, ou se a ponte monolítica reaparecer.

## Validação

```bash
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
python -m unittest discover -s tests
```

Em ambiente com o toolchain PE/COFF/UEFI, o build completo continua sendo:

```powershell
./tools/build_uefi_desktop.ps1
```

Em Linux/ELF, a geração e compilação de todos os objetos pode ser verificada,
mas o link final esperado falha se o `ld` local não oferecer `--subsystem,10`.
Isso é uma limitação do linker escolhido, não do lowering dos módulos.

Nesta auditoria, a suíte executou 270 testes e o link estrutural dos 17 objetos
(15 módulos, adaptador e bootloader) passou com símbolos indefinidos proibidos.

O GitHub Actions usa o mesmo resolvedor modular para conferir `main.sotlas`,
compila o PE/COFF com MinGW, exige uma ISO não vazia e só aceita o smoke test
QEMU quando a VM permanece executando até o timeout esperado. Falhas de build,
empacotamento ou QEMU não são mais ocultadas por `|| true`.
