# Especificação Técnica do Sistema de Arquivos BakenFS
Versão: 1.0.0-SOVEREIGN
Tipo: Árvore Merkle B-Tree com Criptografia de Blocos Pós-Quântica

---

## 1. Visão Geral
O **BakenFS** é o sistema de arquivos oficial do Baken OS, projetado com **zero dependência de FAT, ext4, NTFS ou VFS POSIX**. Ele une:
1. **Estrutura Merkle B-Tree:** Cada nó do sistema de arquivos tem seu hash SHA-3/256 encadeado até o Superbloco, tornando impossível a corrupção silenciosa de dados ou adulteração por rootkits.
2. **Criptografia Pós-Quântica Nativa:** Todos os blocos de dados são cifrados em repouso com chaves derivadas do **ML-KEM (Kyber-768)**.
3. **Controle de Acesso por Capabilities:** Arquivos só podem ser lidos ou gravados por processos que apresentem um *Capability Token* válido emitido pelo microkernel.

---

## 2. Layout Físico do Disco (Setores de 4 KB)

```
+-----------------------------------------------------------------------+
|  Offset (Bytes)   |  Tamanho  |  Estrutura                             |
+-------------------+-----------+---------------------------------------+
|  0x0000_0000      |  4 KB     |  Superbloco BakenFS (Magic, Merkle Root)|
+-------------------+-----------+---------------------------------------+
|  0x0000_1000      |  64 KB    |  Bitmap de Alocação de Blocos Livres  |
+-------------------+-----------+---------------------------------------+
|  0x0001_1000      |  2 MB     |  Tabela de Inodes Baseados em Cap     |
+-------------------+-----------+---------------------------------------+
|  0x0021_1000      |  Restante |  Área de Blocos de Dados Cifrados     |
+-----------------------------------------------------------------------+
```

---

## 3. Estrutura do Superbloco (4096 Bytes)

```
Campo                   Tamanho (Bytes)  Descrição
Magic Signature         8                `\x7f B K N F S 0 1`
Versão do Sistema       4                `0x00010000` (v1.0)
Tamanho do Bloco        4                `4096` bytes
Total de Blocos         8                Número total de blocos no dispositivo NVMe
Blocos Livres           8                Número de blocos disponíveis
Merkle Tree Root Hash   32               Hash SHA-3/256 raiz de integridade de todo o disco
Kyber Public Key Enc    1184             Chave pública ML-KEM para cifragem de volume
Assinatura Dilithium    3293             Assinatura pós-quântica do Superbloco
```

---

## 4. Estrutura de Inode do BakenFS (256 Bytes)

```
Campo                   Tamanho (Bytes)  Descrição
Inode ID                8                Identificador único de 64-bit
Capability Required     8                ID da Capability necessária para acesso
Tamanho do Arquivo      8                Tamanho exato em bytes
Timestamp de Criação    8                Timestamp de 64-bit do Kernel
Timestamp de Modificação8                Timestamp da última gravação
Flags de Segurança      4                `BIT 0`: Criptografado, `BIT 1`: Executável (.bkn_exec)
Apontadores Diretos     16 * 8 = 128     16 ponteiros diretos de blocos (até 64 KB)
Apontador Indireto      8                Ponteiro para bloco B-Tree de extensões
Hash de Integridade     32               Hash SHA-3/256 do arquivo
Nome do Arquivo (UTF-8) 48               Nome do arquivo (até 48 caracteres)
```
