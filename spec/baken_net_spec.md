# Especificação Técnica da Pilha de Rede Soberana do Baken OS
Versão: 1.0.0-SOVEREIGN
Arquitetura: Zero-Copy Network Streams com Criptografia Pós-Quântica Nativa

---

## 1. Visão Geral
A pilha de rede do Baken OS substitui integralmente a arquitetura arcaica de BSD Sockets e pilha TCP/IP dos anos 80 por:
1. **Fluxos de Pacotes Orientados a Capabilities:** Processos de rede não abrem portas arbitrariamente; o acesso à interface é concedido via *Network Capability Tokens*.
2. **Cifragem Pós-Quântica de Camada de Enlace (L2/L3):** Todo pacote trocado entre nós Baken utiliza encapsulamento **ML-KEM-768 (Kyber)** com assinaturas digitais **ML-DSA-65 (Dilithium)**.
3. **Agregação de Banda Wi-Fi 7 (802.11be MLO):** Suporte nativo a Multi-Link Operation agregando canais de $2.4\text{ GHz}$, $5\text{ GHz}$ e $6\text{ GHz}$ com latências determinísticas inferiores a $1\text{ ms}$.

---

## 2. Estrutura do Cabeçalho de Pacote Baken (`.bkn_packet`)

```
Campo                   Tamanho (Bytes)  Descrição
Magic Protocol Header   4                `\x7f B N E T`
Protocol Version        2                `0x0100` (v1.0)
Flow Priority / QoS     2                Prioridade de tráfego de ultra-baixa latência
Source Node ID          16               Identificador GUID do nó transmissor
Destination Node ID     16               Identificador GUID do nó receptor
Capability Token ID     8                Token de autorização de tráfego emitido pelo Kernel
Kyber Ephemeral Nonce   32               Nonce criptográfico para cifra simétrica de sessão
Payload Length          4                Tamanho do payload (até 64 KB por quadro Jumbo)
Dilithium Signature     3293             Assinatura de integridade do cabeçalho
```
