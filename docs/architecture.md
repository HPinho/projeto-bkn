# Arquitetura canônica do Baken OS

## Regra principal

Há **uma única rota executável de interface**. O firmware UEFI só prepara o
hardware; nenhuma camada de boot desenha janelas, dock ou widgets.

```text
boot/uefi_bootloader.st
    -> Sotlas Compile: kernel/src/main.st + módulos Sotlas
    -> framebuffer GOP
    -> desktop Baken OS
```

`tools/build_uefi_desktop.ps1` chama o Sotlas Compile, que resolve a entrada Sotlas,
gera uma unidade C por módulo e vincula o EFI aceito pelos launchers
`run_baken.ps1`, `run_baken_iso.ps1` e `run_baken_vbox.ps1`.

O contrato `BakenBootInfo` é único em
`kernel/include/baken_boot_info.h` e é incluído pelo bootloader e pelo kernel;
asserções de layout protegem o handoff UEFI x86_64 contra divergência.

Os antigos launchers paralelos `test_in_virtualbox.ps1`,
`tools/test_fat16_boot.py` e `tools/scripts/run_qemu.py` foram removidos: eles
tinham mídia/boot próprios e podiam operar uma VM pessoal `BakenOS`.

Também não há bridge Electron/Antigravity/Wayland na rota oficial. Aplicativos
futuros devem usar serviços próprios do Baken, sempre por compositor e gerente
de janelas canônicos.

O diretório `bknc/` também não participa do boot nem da cadeia Sotlas modular.
Seu código remanescente é um protótipo de ferramenta hospedeira que só emite
LLVM IR textual preliminar; ele não assina, empacota nem instala executáveis.
O emissor legado, que preenchia uma assinatura fictícia, foi removido para que
artefatos de teste não sejam apresentados como seguros.

O BakenFS mínimo é montado no volume `Baken Data` da instalação virtual e
mantém arquivos, diretórios, preferências e notas após o boot. Não há registro
fixo `INSTALL1`/`BAKENSYS` na rota ativa.

## Mídia de instalação virtual

`tools/scripts/create_installed_disk.py` cria exclusivamente em `build/` uma
mídia virtual GPT com uma ESP FAT32 bootável e uma partição `Baken Data`.
Ela é a referência de layout para o instalador gráfico: nunca recebe caminho de
disco físico e não deve ser usada como ferramenta de particionamento do host.
O bootloader já entrega ao assistente UEFI um segundo disco bruto, gravável e
distinto da mídia de boot. A tela detecta esse alvo de forma explícita; a
subetapa seguinte é gravar o layout GPT/FAT32 nele a partir do pacote de
instalação, sem permitir que a mídia de origem seja formatada.

Não há compatibilidade POSIX, Win32, WASM ou LibC ativa nesta versão. Esses
subsystems só poderão retornar depois de um carregador e isolamento verificáveis.

Antes de qualquer geração de binário, valide o grafo Sotlas com:

```powershell
python tools/sotlas_compile/compiler.py check kernel/src/main.st --manifest build/sotlas-main.manifest.json
```

Esse comando resolve a entrada e audita todos os módulos Sotlas conhecidos: detecta
módulos duplicados, imports ausentes, auto-imports e dependências circulares,
gravando uma ordem de compilação reproduzível para a rota ativa.

## Teste de boot em VM

Após gerar `build/baken_disk.img`, execute:

```powershell
python tools/test_qemu_desktop.py
```

O teste inicializa o disco em QEMU sem abrir janela e captura o framebuffer em
`build/qemu-desktop.ppm`. Ele valida o caminho firmware UEFI -> GOP -> kernel
-> desktop; não substitui testes de particionamento ou instalação real.

Para iniciar a própria ISO óptica El Torito, em vez do disco gravável de
teste, execute:

```powershell
python tools/test_qemu_desktop.py --iso
```

Para validar a instalação virtual persistente:

```powershell
python tools/test_qemu_desktop.py --installed --create-files
python tools/test_qemu_desktop.py --installed --save-theme
python tools/test_qemu_desktop.py --installed --save-note q
```

O assistente só opera sobre Block I/O de mídia presente, gravável e distinta da
origem. Preferências, notas, arquivos e diretórios são gravados no BakenFS da
partição Baken Data.

## VirtualBox

A imagem crua não é anexada diretamente pelo VirtualBox. Para testar, converta
uma cópia com `VBoxManage convertfromraw build/baken_disk.img <arquivo>.vdi`,
anexe-a a uma VM EFI isolada e capture a tela com `controlvm screenshotpng`.
Use somente a VM de teste `BakenOS-MVP-Test`; o launcher usa esse nome por
padrão e não procura, desliga ou reutiliza uma VM pessoal chamada `BakenOS`.
O boot nessa VM é uma validação obrigatória antes de classificar uma ISO como
testável.

## Migração para Sotlas modular

O destino é manter uma única árvore em Sotlas:

```text
kernel::main
    -> graphics_engine
    -> desktop_compositor
    -> desktop_shell
    -> window_manager
    -> aplicações e widgets
```

Os oito arquivos Sotlas canônicos fazem parte do EFI: o Sotlas Compile valida o grafo,
emite um objeto por módulo, gera interfaces e executa o link. A entrada pública
é `kernel::main`; não há runtime C de desktop na rota oficial.

`kernel::desktop_compositor` é a fachada gráfica canônica e é a única função
de composição chamada por `kernel::main`. Ela inicializa o desktop shell, que
inicializa o `window_manager` canônico. A rota Sotlas validada contém oito módulos:
renderização, animação/UI, gerenciador de janelas, shell, compositor e entrada.
O `window_manager` não abre aplicativos de demonstração e não importa terminal,
rede ou armazenamento; aplicativos só entram quando tiverem serviços reais.

As pilhas paralelas `bakenfx`, `baken_ui`, `baken_compositor`, seus efeitos e
o `shell_cli` legado foram removidos. `graphics_engine` + `baken_rasterizer` +
`baken_ui_oop` são as únicas camadas visuais na rota Sotlas inicial.

Também foram removidas telas isoladas de central de controle, documentação,
busca, splash, menus, temas e widgets alternativos. Elas não eram abertas pelo
shell e não podem ser tratadas como aplicativos enquanto não houver lançador,
serviços e persistência reais.

## Limites claros de cada camada

- **Bootloader**: GOP, mouse/teclado UEFI e handoff. Sem interface de desktop.
- **Formato de vídeo do bridge**: GOP BGR de 32 bits; outros formatos ficam
  bloqueados até o compositor ter conversão de pixel testada.
- **Orçamento de vídeo**: o boot seleciona o maior modo BGRX de até 1920×1200.
  Esse teto mantém o backbuffer ativo e evita desenho parcial visível em modos
  4K que o compositor por software ainda não consegue sustentar.
- **Cadência**: o TSC é calibrado com o timer UEFI, o compositor recebe `dt`
  real limitado e o loop é cadenciado a aproximadamente 60 Hz quando o custo
  do quadro permite. Esperas ocupadas dependentes da CPU não fazem parte da
  rota.
- **Canvas e efeitos**: o wallpaper é armazenado por resolução/tema; blurs usam
  passagens separáveis com janela deslizante. O frame só chega ao GOP depois da
  composição completa no backbuffer.
- **Kernel/renderizador**: memória de vídeo, composição de quadros e entrada.
- **Desktop shell**: topbar, papel de parede, dock e encaminhamento de janelas.
- **Window manager**: estado e interação de janelas; não inicializa outro
  renderizador.
- **Apps**: desenham somente no contexto recebido do compositor; não escrevem
  diretamente no framebuffer.

## Critério para remover a ponte C atual

`baken_kernel_all.c` permanece apenas como referência histórica fora do build.
O build Sotlas atende aos critérios de substituição:

1. resolver importações transitivas;
2. gerar objetos separados por módulo;
3. detectar símbolos duplicados no link;
4. vincular `kernel::main` como a única entrada do kernel;
5. produzir o mesmo `BOOTX64.EFI` validado em QEMU/VirtualBox.

Ele não participa da ISO, do disco instalado nem do alvo `sotlas_build`.
