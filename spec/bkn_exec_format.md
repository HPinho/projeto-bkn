# Especificação do Formato Executável Nativo `.bkn_exec`

O formato `.bkn_exec` é o padrão binário soberano do Baken OS, substituindo integralmente formatos legados (ELF do Unix/Linux e PE do Windows).

---

## 1. Estrutura do Cabeçalho de 128 Bytes (BKN Header)

```
Offset (Hex)  Tamanho (Bytes)  Campo                   Descrição
0x00          8                Magic Signature         `\x7f B K N E X E C \x00`
0x08          2                Versão do Formato       `0x0100` (v1.0)
0x0A          2                Arquitetura Alvo        `0x01` (x86_64), `0x02` (ARM64), `0x03` (RISC-V)
0x0C          4                Flags de Segurança      `BIT 0`: Signed (ML-DSA), `BIT 1`: Encrypted Text
0x10          8                Entry Point Clássico    Endereço virtual relativo (RVA) do início da execução
0x18          8                Entry Point Quântico    RVA para tabela de inicialização de circuitos Q-HAL
0x20          8                Offset Seção .bkn_meta  Metadados de Sandbox e Capabilities do processo
0x28          8                Tamanho Seção .bkn_meta Em bytes
0x30          8                Offset Seção .bkn_text  Instruções de máquina clássicas
0x38          8                Tamanho Seção .bkn_text Em bytes
0x40          8                Offset Seção .bkn_qir   Tabela de circuitos quânticos em bytecode QIR
0x48          8                Tamanho Seção .bkn_qir  Em bytes
0x50          8                Offset Seção .bkn_rodata Constantes e dados estáticos
0x58          8                Tamanho Seção .bkn_rodata Em bytes
0x60          8                Offset Seção .bkn_sig   Assinatura digital Pós-Quântica (ML-DSA / Dilithium)
0x68          8                Tamanho Seção .bkn_sig  Em bytes
0x70          16               Hash SHA-3/512 (Header) Hash de integridade dos cabeçalhos
```

---

## 2. Seções do Binário

### 2.1 `.bkn_meta` (Descritores de Capacidade e Sandbox)
Define os privilégios estritos do processo no Ring 3:
- Permissão de acesso a portas MMIO específicas (para drivers).
- Canais IPC autorizados (IDs de Endpoints).
- Quota máxima de memória física e threads quânticas/clássicas.

### 2.2 `.bkn_text` (Código de Máquina com Ofuscação de Fluxo de Controle)
- O compilador `bknc` aplica **Control Flow Flattening**: cada função tem suas instruções básicas reorganizadas dentro de um despachante central com chaves pseudo-aleatórias em tempo de execução.
- Blocos são criptografados estaticamente com chave derivada de assinatura e são decifrados em páginas estritamente efêmeras (W^X ativado).

### 2.3 `.bkn_qir` (Bytecode Quântico Q-IR)
Armazena a descrição em grafo acíclico dirigido (DAG) das portas quânticas, topologia de acoplamento de qubits e parâmetros de fase para despacho pelo `Q-HAL`.

### 2.4 `.bkn_sig` (Assinatura Pós-Quântica ML-DSA)
Garante que nenhum binário não autorizado, adulterado ou infectado seja carregado pelo microkernel:
- Utiliza **ML-DSA-65 (Dilithium3)** com segurança de 128-bit pós-quântica.
- O Kernel VMM recusa o mapeamento de páginas caso a assinatura não confira com a autoridade de certificação do Baken OS.
