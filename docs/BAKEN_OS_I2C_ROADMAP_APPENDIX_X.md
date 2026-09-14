# Baken OS — I2C Roadmap Appendix X

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores (preservando integralmente os Apêndices VIII e IX).

## 2026-09-14 — Início da Subtrilha I2C-HID: Descoberta ACPI e Avaliação de _DSM (I2C-HID-0)

Com a fundação arquitetural (I2C-0 a I2C-4) e o backend físico (I2C-5 a I2C-5F) plenamente certificados, foi aberta oficialmente a subtrilha **I2C-HID**, iniciando pela fase **I2C-HID-0**:

### 1. Extensão Cirúrgica do Avaliador AML (AML-6b)
- **Módulo**: `kernel/src/acpi/aml_evaluator.sotlas`
- **Testes**: `tests/test_aml_evaluator_dsm.py`
- **Motivação**: Firmware real de touchpads e touchscreens declara o método `_DSM` com `Method (_DSM, 4, Serialized)` e executa comparações com o UUID Microsoft HIDI2C usando `LEqual(Arg0, ToUUID(...))`.
- **Entregas**:
  1. **Flag `Serialized` (`0x08`)**: Admitido em `aml_evaluator_execute_method()` com validação `(flags & 0xF0) != 0` (SyncLevel 0).
  2. **Operador `LEqual` com Suporte a Buffers**: Comparação segura byte-a-byte (`aml_eval_buffers_equal`) de dois Buffers (`AML_EVAL_VALUE_BUFFER`) ou Strings, viabilizando a validação exata do GUID.
  3. **Construtores Públicos**: `aml_eval_buffer()` e `aml_eval_package()` para montagem tipada dos argumentos de invocação de métodos AML.

### 2. Driver de Descoberta e Avaliação ACPI (I2C-HID-0)
- **Módulo**: `kernel/src/drivers/i2c_hid_acpi.sotlas`
- **Testes**: `tests/test_i2c_hid_acpi.py`, `tests/test_i2c_hid_contract.py`
- **Entregas**:
  1. **Identificação de Dispositivos**: Reconhece dispositivos com `_HID` ou `_CID` compatíveis com `PNP0C50` ou `ACPI0C50`.
  2. **Associação de Recursos de Barramento e GPIO**:
     - Extrai `I2CSerialBusConnection` do `_CRS`: endereço do escravo, velocidade de conexão (100 kHz / 400 kHz) e barramento pai.
     - Extrai `GpioInt` do `_CRS`: pino de interrupção, polaridade (ActiveLow / ActiveHigh) e trigger (Edge / Level).
  3. **Avaliação Canônica de `_DSM` (Microsoft HIDI2C)**:
     - UUID canônico: `3cdff6f7-4267-4555-ad05-b30a3d8938de` (16 bytes, RFC 4122 mixed-endian).
     - **Function 0 (Query)**: Executa com `Arg2 = 0` e valida se o bit 1 da bitmask está ativo.
     - **Function 1 (Descriptor Address)**: Executa com `Arg2 = 1` e extrai o registrador 16-bit do HID Descriptor (suportando retorno tanto como Integer quanto como Buffer).
  4. **Vinculação com o Controlador I2C**: Associação generation-safe do dispositivo com o controlador catalogado via `i2c_discovery_bridge_find_by_namespace()`.
  5. **Tabela Estática Generation-Safe**: Capacidade limitada a `I2C_HID_MAX_DEVICES = 4`, com zero alocação dinâmica (`no heap`, `no alloc`).

### 3. Integração na Rota de Boot e QEMU Smoke Gate
- **Módulos**: `kernel/src/baken_native_runtime.sotlas`, `kernel/src/main.sotlas`
- Invocação oportuna de `i2c_hid_acpi_scan_devices()` na sequência canônica de boot:
  `Platform Catalog ➔ I2C ACPI Controllers ➔ I2C Physical Discovery ➔ I2C-HID ACPI Scan`.
- Totalmente não-bloqueante e fail-safe: plataformas sem dispositivos I2C-HID (como QEMU padrão) retornam 0 imediatamente, preservando 100% dos 42 marcos de boot smoke.

---

## Matriz de Conformidade do Roadmap I2C-HID

| Fase | Escopo | Status |
|---|---|---|
| **I2C-HID-0** | Descoberta ACPI + Avaliador AML-6b _DSM (PNP0C50, _CRS, Function 1) | ✅ **Concluído e Certificado** |
| **I2C-HID-1** | Leitura Física do HID Descriptor (30 bytes via I2C-5F backend) | 🎯 **Próxima Etapa** |
| **I2C-HID-2** | Leitura do Report Descriptor & Convergência com Generic HID Core | ⏸️ Aguardando I2C-HID-1 |
| **I2C-HID-3** | Backend Físico de GPIO & Roteamento de IRQ | ⏸️ Aguardando I2C-HID-2 |
| **I2C-HID-4** | Pipeline Assíncrono de Input (Hard IRQ ➔ Deferred Worker ➔ Events) | ⏸️ Aguardando I2C-HID-3 |
| **I2C-HID-5** | Ciclo de Vida e Comandos de Protocolo (Reset, Power, Get/Set Report) | ⏸️ Aguardando I2C-HID-4 |
| **I2C-HID-6** | Certificação Comportamental Completa & Concorrência USB + I2C | ⏸️ Aguardando I2C-HID-5 |

---

## Estado da Trilha B2
- **Grafo Modular do Kernel**: **180 módulos resolvidos**, 0 fora da rota ativa, 0 raízes órfãs.
- **Suítes I2C & HID**: **89 testes com 100% de aprovação**.
- **Próxima Etapa Autorizada**: **I2C-HID-1** (Leitura física do HID Descriptor através do registrador obtido via `_DSM`).
