# Auditoria do legado — etapa 1

Esta lista separa funcionalidades verificadas de módulos que ainda são rascunhos. Ela existe para impedir que uma tela bonita seja confundida com uma instalação concluída.

## Rota que inicia hoje

`UEFI GOP -> kernel/src/baken_kernel_all.c -> compositor/desenho C de compatibilidade`.

O boot UEFI, o framebuffer e o desktop foram validados no QEMU em 27/08/2026
com o disco UEFI gravável e com a ISO El Torito. O registro mínimo foi escrito
no LBA reservado e reconhecido após novo boot. A validação no VirtualBox ainda
é necessária antes de qualquer entrega mais ampla. Esse registro não é um
sistema de arquivos nem torna a ISO instalável em uma máquina real.

## Rota Sotlas oficial em construção

`kernel::main -> graphics_engine -> desktop_compositor -> desktop_shell -> window_manager`.

O resolvedor Sotlas valida este grafo de oito módulos. Os demais módulos Sotlas legados
foram removidos, não apenas desativados: não há uma segunda UI, terminal,
aplicativo, driver ou serviço oculto fora da rota oficial.

## Proteções aplicadas nesta etapa

- `block_dev` não publica mais NVMe/SATA fictícios, suas capacidades ou modelos inventados.
- NVMe e AHCI não retornam sucesso para I/O que não aguarda conclusão do dispositivo.
- FAT32 e GPT usam a API correta de blocos e deixam de aceitar leitura falsa; GPT não inventa duas partições padrão.
- A tela Sotlas do instalador é explicitamente uma prévia até o backend de armazenamento ser implementado.
- O motor gráfico Sotlas inicial usa GOP diretamente; a alocação de backbuffer fica bloqueada até o PMM ser inicializado corretamente a partir do mapa UEFI.

## O que ainda não pode ser prometido

- Compilação e link completos de todos os módulos Sotlas para `BOOTX64.EFI`.
- Driver NVMe/AHCI com filas, DMA, doorbells, interrupções e confirmação de I/O.
- Leitura de entradas GPT, FAT32 completo ou BakenFS persistente.
- Particionamento, formatação e cópia segura de uma instalação.
- Fonte vetorial/anti-aliased e ícones finais idênticos à referência visual.
- Os drivers USB Mass Storage e VirtIO-GPU: agora falham explicitamente, pois
  seus transportes ainda não foram implementados.
- CMake produzir objetos Sotlas: CMake agora só executa verificações; ele não é um
  compilador Sotlas e não deve alegar que produz um kernel.
- `Sotlas build` agora falha explicitamente até o backend gerar objetos de
  todos os módulos e realizar o link; a antiga transpiração isolada foi
  removida para não mascarar falhas de compilação.
- A antiga ponte `libbkn/src/bkn_bridge.st` foi removida: não era importada nem
  construída, simulava telemetria/processos/chaves e executava código via
  caminhos antigos fora do workspace.
- A rede agora começa desligada: os esqueletos Intel/Realtek não fazem mais
  escrita MMIO parcial nem publicam link ativo; o Finder identifica o conteúdo
  atual como sessão temporária, não como BakenFS ou disco SATA.
- A ponte UEFI/C ativa valida dimensões/tamanho do framebuffer, aplica clipping
  a todos os pixels compostos e grava o registro de teste uma vez por clique.
  Seus widgets agora mostram apenas o estado que ela realmente conhece.
- Os empacotadores agora distinguem a ISO El Torito óptica do disco MBR/FAT16
  de teste e recusam gerar mídia com executáveis de fallback. A imagem USB/GPT
  híbrida continua fora do escopo até existir instalador e particionamento real.
- O launcher VirtualBox agora usa uma VM de teste isolada por padrão e não
  encerra processos globais nem reutiliza uma VM pessoal `BakenOS`.
- Os três launchers paralelos antigos de QEMU/VirtualBox foram removidos para
  impedir compilação, imagem e controle de VM fora da rota canônica.
- As pontes `linux_abi`, Wayland/Electron e renderização externa do Antigravity
  foram removidas: não pertenciam ao grafo ativo e simulavam integrações que o
  kernel não oferece. O registro de apps não instala pacotes até haver backend.
- Verificação de assinatura, autenticação, keyring, capabilities e IA agora
  falham fechados ou permanecem indisponíveis. Foram removidos root automático,
  chave literal e ponte de IA que simulava privilégios/telemetria.
- Os protótipos sem integração de agentes/IA distribuída, QPU físico, suíte
  Office com assinatura XOR e compatibilidade de binários foram removidos. Eles
  anunciavam execução, hardware, assinatura ou isolamento que não existiam.
- As camadas POSIX, Win32, WASM e LibC sem loader/runtime foram removidas. Elas
  devolviam handles e mapeamentos fictícios; compatibilidade futura exige
  carregador, isolamento e testes próprios antes de entrar no kernel.
- Os exemplos `bkn_terminal`, `bkn_calc` e `bkn_studio` e seu stub de syscall
  de user-mode foram removidos. Eles só abriam loops infinitos sobre uma ABI
  sem processo, syscall ou janela real no kernel.
- Os motores 3D/física alternativos, hypervisor, índice vetorial, JIT e
  “superotimizador” sem integração foram removidos. Eles declaravam VMX,
  aceleração AVX, índices persistentes ou desempenho que não eram implementados
  nem necessários para o desktop inicial.
- App store, gerenciador de pacotes, loader externo, identificação automática,
  mkfs/fsck, menu de boot alternativo e DNS de demonstração também foram
  removidos. Não há instalação, execução externa, formatação ou rede até que
  suas camadas tenham I/O e contratos testados.
- Os módulos de auto-reparo, auto-testes, crash dump, SMP e áudio foram
  removidos porque relatavam recuperação, aprovação criptográfica, registradores,
  CPUs ou reprodução sem validar o hardware e a execução correspondente.
- Loader ELF, rede TCP/IP, QN-Bus, pipes e IPC foram removidos da árvore Sotlas.
  Ainda não há processos, socket, scheduler ou driver vinculados para sustentar
  essas APIs; mantê-las daria a impressão errada de execução user-mode e rede.

## Critério para reativar um subsistema

Um subsistema sai desta lista somente com: teste automatizado de sucesso e falha, integração na rota Sotlas, e uma execução em QEMU antes de ser oferecido pelo instalador.
