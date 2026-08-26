# 🌌 Manual do Desenvolvedor Soberano — Baken OS & Linguagem BKN

Bem-vindo ao guia oficial do **Baken OS**, um sistema operacional soberano de última geração escrito do zero em **BKN**, com zero dependências externas, suporte nativo à computação quântica (Q-HAL), criptografia pós-quântica (PQC), motor gráfico 3D e interface declarativa de alta fidelidade (BakenUI).

---

## 🏛️ 1. Arquitetura do Sistema Operacional

O Baken OS opera em uma arquitetura de **Microkernel Soberano por Capacidades**, dividida em anéis de privilégio de hardware:

```
 +-------------------------------------------------------------------+
 |                   APLICAÇÕES DE USUÁRIO (RING 3)                  |
 |  BKN Studio IDE  |  Terminal CLI  |  Control Center  |  Q-HAL 3D  |
 +-------------------------------------------------------------------+
                                  |
              [ Fast Syscalls & Capability IPC Bus ]
                                  |
 +-------------------------------------------------------------------+
 |                    MICROKERNEL SOBERANO (RING 0)                  |
 |  - PMM: Buddy Memory Allocator (11 Ordens)                        |
 |  - VMM: Paginação Virtual x86_64 Higher-Half (PML4)               |
 |  - Scheduler: Preemptivo Híbrido com APIC Timer (1000 Hz)         |
 |  - Storage: BakenFS + BakenDB + Drivers NVMe PCIe & SATA AHCI     |
 |  - Graphics: Swapchain Double-Buffering + Rasterizador Vetorial   |
 |  - Q-HAL: Simulador Vetorial + Detecção de QPU PCIe Física        |
 +-------------------------------------------------------------------+
                                  |
 +-------------------------------------------------------------------+
 |                   HYPERVISOR NATIVO (RING -1)                     |
 |  BakenVM: Isolamento e Virtualização de Hardware Intel VT-x       |
 +-------------------------------------------------------------------+
```

---

## 💻 2. Guia da Linguagem BKN

A linguagem **BKN** unifica a programação clássica de sistemas bare-metal com computação quântica e criptografia pós-quântica.

### 2.1 Módulo Clássico de Sistema (`@system`)
Para código de kernel, drivers e funções de baixo nível sem *Garbage Collector*:

```bkn
module main;

import kernel::graphics_engine::*;
import kernel::rtc::*;

@system
pub fn saudacao_sistema() {
    let hora = rtc_get_short_time();
    gfx_draw_text(100, 100, b"Ola Mundo no Baken OS!\0".as_ptr(), 0x0000E5FF, 2);
}
```

### 2.2 Módulo Quântico (`@quantum`)
Para manipulação de registradores quânticos (`qubit`, `qreg`), superposição e emaranhamento:

```bkn
module teleport;

import kernel::qhal::*;

@quantum
pub fn criar_par_de_bell() -> (u8, u8) {
    let q0 = qubit::new();
    let q1 = qubit::new();

    // Aplica porta Hadamard em q0 (Superposição)
    qhal_apply_hadamard(0);

    // Aplica porta CNOT entre q0 (controle) e q1 (alvo) -> Emaranhamento Quântico
    qhal_apply_cnot(0, 1);

    // Medição no colapso da função de onda
    let m0 = qhal_measure_qubit(0);
    let m1 = qhal_measure_qubit(1);

    return (m0, m1); // Sempre correlacionados (0,0) ou (1,1)
}
```

---

## 🎨 3. Construindo Interfaces com o BakenUI

O **BakenUI** é o toolkit declarativo soberano (estilo Flutter / SwiftUI) que permite criar interfaces elegantes com sombras volumétricas e cantos arredondados contínuos (*SDF squircles*):

```bkn
module meu_app;

import kernel::baken_ui::*;

pub fn construir_interface() {
    let root = UiNode::card(360, 240, 0x000B1021, 0x0000E5FF)
        .with_child(UiNode::text(b"Painel Quantum\0".as_ptr(), 0x00FFFFFF))
        .with_child(UiNode::button(b"Executar Circuito\0".as_ptr(), 0x006366F1));

    baken_ui_render_tree(&root);
}
```

---

## 🖴 4. Armazenamento com BakenFS & BakenDB

* **BakenFS**: Sistema de arquivos com suporte a Inodes, alocação de blocos por *extents* e compatibilidade universal com **SSDs NVMe M.2**, **SSDs SATA** e **HDDs mecânicos**.
* **BakenDB**: Banco de dados relacional e chave-valor integrado em memória com sincronização atômica para disco (`system.db`).

---

## 🚀 5. Como Testar e Rodar no seu PC

### Passo 1: Atualizar o Repositório
No seu terminal local:
```powershell
git pull origin main
```

### Passo 2: Compilar e Rodar no Emulador QEMU
Execute o script unificado com 1 comando:
```powershell
.\run_baken.ps1
```
*O script compilará o bootloader UEFI `BOOTX64.EFI`, gerará a imagem de disco FAT32 ESP `build\baken_disk.img` e iniciará a máquina virtual com aceleração gráfica GOP.*

### Passo 3: Gravação em Pendrive para Boot Bare-Metal em PC Real
Para inicializar o Baken OS diretamente na placa-mãe do seu PC:
1. Insira um pendrive USB.
2. Abra o aplicativo **Rufus** (ou use o utilitário `dd`):
   - **Dispositivo**: Seu pendrive USB.
   - **Tipo de Boot**: Selecione o arquivo `build\baken_disk.img`.
   - **Esquema de Partição**: GPT / UEFI.
3. Conecte o pendrive no PC, ligue o computador e pressione `F11` ou `F12` para selecionar o boot pelo pendrive!
