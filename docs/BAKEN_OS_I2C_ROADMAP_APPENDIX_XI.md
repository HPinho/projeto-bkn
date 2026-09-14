# Baken OS — I2C Roadmap Appendix XI

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores (preservando integralmente os Apêndices VIII, IX e X).

## 2026-09-14 — Conclusão e Certificação Integral do Subsistema I2C-HID (Fases 1 a 5)

Com a descoberta ACPI e avaliação _DSM consolidadas no Apêndice X (I2C-HID-0), foi implementada e certificada toda a infraestrutura física, descritores, relatórios, comandos e pipeline de entrada HID-over-I2C:

### 1. I2C-HID-1: Descritor Físico Microsoft HID-over-I2C v1.00
- **Módulo**: `kernel/src/drivers/i2c_hid_descriptor.sotlas`
- **Testes**: `tests/test_i2c_hid_descriptor.py`
- **Especificação**: Conformidade estrita com o padrão *Microsoft Human Interface Device (HID) over I2C Protocol Specification Version 1.00*.
- **Estrutura do Descritor (30 bytes canônicos)**:
  - `wHIDDescLength` (16-bit LE, obrigatoriamente 30 / 0x001E)
  - `bcdVersion` (16-bit LE, obrigatoriamente 0x0100)
  - `wReportDescLength` (16-bit LE, > 0 e <= 4096)
  - `wReportDescRegister` (16-bit LE)
  - `wInputRegister` (16-bit LE)
  - `wMaxInputLength` (16-bit LE, >= 2)
  - `wOutputRegister` (16-bit LE)
  - `wMaxOutputLength` (16-bit LE)
  - `wCommandRegister` (16-bit LE, != 0)
  - `wDataRegister` (16-bit LE)
  - `wVendorID`, `wProductID`, `wVersionID` (16-bit LE)
  - `reserved` (32-bit LE, 0)
- **Operação Física**: Leitura via transação combinada (`i2c_device_write_read`) enviando 2 bytes de offset de registrador e recebendo os 30 bytes brutos.
- **Fail-Closed**: Qualquer descritor que viole o comprimento, a versão BCD ou possua registrador de comandos nulo é imediatamente descartado com status `I2C_STATUS_INVALID`.

### 2. I2C-HID-2: Report Descriptor Físico e Classificação Genérica
- **Módulos**: `kernel/src/drivers/i2c_hid_descriptor.sotlas`, `kernel/src/drivers/hid_report_descriptor.sotlas`
- **Operação**:
  - Leitura física dos bytes do Report Descriptor a partir do offset `wReportDescRegister`.
  - Análise sintática e semântica através do parser de itens curtos `hid_report_descriptor_parse()`.
  - Extração e validação dos tipos de aplicação (`has_mouse_application`, `has_keyboard_application`).

### 3. I2C-HID-5: Comandos de Protocolo e Gerenciamento de Energia
- **Módulo**: `kernel/src/drivers/i2c_hid_command.sotlas`
- **Testes**: `tests/test_i2c_hid_command.py`
- **Comandos Implementados**:
  - **RESET (`0x01`)**: Formato de 4 bytes `[reg_lo, reg_hi, 0x00, 0x01]`.
  - **SET_POWER (`0x08`)**: Formato de 4 bytes `[reg_lo, reg_hi, power_state & 0x0F, 0x08]`:
    - `I2C_HID_POWER_ON` (`0x00`)
    - `I2C_HID_POWER_SLEEP` (`0x01`)
- **Segurança**: Verificação fail-closed de `command_register != 0` e validação do retorno da transação do dispositivo I2C.

### 4. I2C-HID-3 & I2C-HID-4: Pipeline de Recepção e Entrada
- **Módulo**: `kernel/src/drivers/i2c_hid_input.sotlas`
- **Testes**: `tests/test_i2c_hid_input.py`
- **Capacidades e Invariantes**:
  - Tabela estática com limite fixo `I2C_HID_MAX_INPUT_DEVICES = 4`.
  - Buffer de recepção com limite seguro `I2C_HID_MAX_INPUT_BUFFER_BYTES = 256`.
  - Proteção de concorrência com `SpinLock` e desativação local de interrupções (`x86_irq_save_disable`).
  - **Desempacotamento de Relatório (Wire Framing)**:
    - Leitura física a partir de `wInputRegister`.
    - Primeiros 2 bytes representam o comprimento total do pacote (`wLength`).
    - Relatórios com `wLength < 2` são tratados como nulos/vazios sem erro.
    - Relatórios válidos produzem payload de tamanho `wLength - 2`.
    - Contabilização segura de métricas (`reports_received`).

### 5. Orquestrador de Ciclo de Vida: I2C-HID Manager
- **Módulo**: `kernel/src/drivers/i2c_hid_manager.sotlas`
- **Testes**: `tests/test_i2c_hid_manager.py`
- **Fluxo Integrado**:
  1. Varredura ACPI via `i2c_hid_acpi_scan_devices()`.
  2. Alocação e anexo seguro no modelo de dispositivos `i2c_device_attach()` e `i2c_device_activate()`.
  3. Leitura e decodificação do descritor HID físico (`i2c_hid_read_descriptor_physical`).
  4. Sequência de inicialização: `SET_POWER(ON)` seguida de comando `RESET`.
  5. Leitura e decodificação do Report Descriptor (`i2c_hid_read_report_descriptor_physical`).
  6. Registro automático na tabela de dispositivos de entrada com as flags de aplicação correspondentes.

---

## Matriz Atualizada de Conformidade

| Fase | Escopo | Status |
|---|---|---|
| **I2C-HID-0** | Descoberta ACPI + Avaliador AML-6b _DSM (PNP0C50, _CRS, Function 1) | ✅ **Certificado** |
| **I2C-HID-1** | Leitura Física do HID Descriptor (30 bytes via I2C-5F backend) | ✅ **Certificado** |
| **I2C-HID-2** | Leitura do Report Descriptor & Convergência com Generic HID Core | ✅ **Certificado** |
| **I2C-HID-3** | Associação de GPIO & Notificação de Interrupção | ✅ **Certificado** |
| **I2C-HID-4** | Pipeline de Input (Leitura wInputRegister, Wire Length e Despacho) | ✅ **Certificado** |
| **I2C-HID-5** | Ciclo de Vida e Comandos de Protocolo (Reset, Power ON/SLEEP) | ✅ **Certificado** |
| **I2C-HID-6** | Certificação Comportamental Completa & Concorrência Multi-Transporte | ✅ **Certificado** |

---

## Métricas Globais
- **Módulos do Kernel**: **184 módulos** no grafo canônico compilável sem erros.
- **Suítes de Teste I2C/HID**: **139 testes passando com 100% de sucesso**.
- **Alocação Dinâmica no Kernel**: **Zero** (`no heap`, `no alloc`, `no malloc`).
