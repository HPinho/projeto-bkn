# Baken OS — I2C Roadmap Appendix XII

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores (preservando integralmente os Apêndices VIII, IX, X e XI).
> Registra historicamente a supersessão e o endurecimento (*hardening*) de paridade com hardware real do subsistema I2C-HID após a revisão do commit `7972ad9f`.

## 2026-09-14 — Hardening e Paridade com Hardware Real do Subsistema I2C-HID

Após a fundação arquitetural introduzida nos estágios I2C-HID-0 a 5, foi conduzida uma auditoria aprofundada de hardware real identificando 9 bloqueadores essenciais para operação física e confiável. Todas as correções foram implementadas, validadas e integradas de forma estritamente *fail-closed*, com zero alocação dinâmica de heap.

---

### 1. Eliminação do Double-Scan ACPI e Idempotência Estrita
- **Módulos**: `kernel/src/drivers/i2c_hid_acpi.sotlas`, `kernel/src/drivers/i2c_hid_manager.sotlas`
- **Problema**: `i2c_hid_manager_init()` executava novamente `i2c_hid_acpi_scan_devices()`, duplicando entradas e distorcendo a contagem de dispositivos gerenciados.
- **Solução**:
  - `i2c_hid_acpi.sotlas` recebeu a flag estática `I2C_HID_SCANNED` e deduplicação de dispositivos por `namespace_index` (`already_enrolled`).
  - `i2c_hid_manager.sotlas` agora consulta `i2c_hid_acpi_device_count()` diretamente. Se não houver varredura prévia, realiza uma única chamada idempotente.

---

### 2. Transação READ Pura na Leitura de Relatórios de Entrada
- **Módulo**: `kernel/src/drivers/i2c_hid_input.sotlas`
- **Problema**: O driver de referência do Linux (`i2c-hid-core.c`) executa `i2c_master_recv()` puro no escravo I²C para consumir relatórios após IRQ. A implementação anterior tentava uma transação combinada `write(wInputRegister) -> read`, que não é aceita pela maioria dos touchpads físicos.
- **Solução**: `i2c_hid_input_fetch_report()` foi refatorado para utilizar estritamente `i2c_device_read()` diretamente no endereço do escravo, sem gravação preliminar de registrador.

---

### 3. Conexão e Despacho de Interrupções GPIO Físicas
- **Módulos**: `kernel/src/drivers/i2c_hid_manager.sotlas`, `kernel/src/drivers/i2c_device.sotlas`, `kernel/src/drivers/gpio_core.sotlas`
- **Problema**: O discovery ACPI extraía pin, polaridade e trigger, mas deixava `gpio_connection_id = 0` no `I2cDeviceConfig` e nunca registrava a conexão de interrupção no núcleo GPIO.
- **Solução**:
  - O descritor ACPI agora preserva `gpio_resource_index`.
  - `i2c_hid_manager_init()` invoca `gpio_connection_register_from_acpi()` e vincula o identificador generation-safe através da nova primitiva `i2c_device_set_gpio()`.
  - No loop de serviço, interrupções pendentes são consumidas via `gpio_connection_consume_pending()` e despachadas para `i2c_hid_input_notify_irq()`.

---

### 4. Protocolo e Handshake Estrito de RESET
- **Módulo**: `kernel/src/drivers/i2c_hid_manager.sotlas`
- **Problema**: Os comandos `SET_POWER(ON)` e `RESET` tinham seus códigos de retorno ignorados e o dispositivo era marcado como operacional sem aguardar a confirmação de reset.
- **Solução**:
  - Validação estrita de status: falha em `SET_POWER` ou `RESET` aborta a inicialização do dispositivo.
  - Implementado handshake bounded de confirmação: o host realiza polling bounded no escravo aguardando o relatório nulo de comprimento zero (`wLength == 0x0000`), confirmando o término do reset conforme a especificação Microsoft HID-over-I2C. Apenas com handshake confirmado o dispositivo prossegue.

---

### 5. Scratch Bounded de 2048 Bytes para Report Descriptor
- **Módulo**: `kernel/src/drivers/i2c_hid_manager.sotlas`
- **Problema**: O descritor permitia relatórios de até 4096 bytes, mas o buffer local truncava silenciosamente em 512 bytes.
- **Solução**:
  - Estabelecido `pub const I2C_HID_CERTIFIED_REPORT_MAX: usize = 2048;`.
  - Alocado armazenamento estático bounded `I2C_HID_REPORT_SCRATCH: [u8; 2048]`.
  - Tratamento fail-closed: se `wReportDescLength > I2C_HID_CERTIFIED_REPORT_MAX` ou igual a 0, o dispositivo é rejeitado com status não suportado, sem truncamento silencioso.

---

### 6. Suporte a Digitizer/Touchpad e Convergência com Subsistema Genérico de Entrada
- **Módulos**: `kernel/src/drivers/hid_report_descriptor.sotlas`, `kernel/src/drivers/i2c_hid_manager.sotlas`, `kernel/src/drivers/i2c_hid_input.sotlas`
- **Problema**:
  - O parser de descritores não reconhecia Usage Page Digitizer (`0x0D`) nem touchpads, e presumia incorretamente todo dispositivo como mouse.
  - O subsistema I2C-HID não despachava para a infraestrutura unificada de eventos HID (`hid_input_events`).
- **Solução**:
  - Adicionadas constantes `HID_USAGE_PAGE_DIGITIZER`, `HID_USAGE_DIGITIZER_TOUCH_PAD` e campo `has_touchpad_application` no `HidReportDescriptorInfo`.
  - Inicialização fail-closed de classes: `mouse = false`, `keyboard = false`, `touchpad = false`. Apenas aplicações comprovadamente parseadas ativam a classe correspondente.
  - Conexão direta com `input_device_attach()`, `hid_input_device_map_build()` e `hid_input_events_bind_device()`.
  - Despacho unificado: em `i2c_hid_input_fetch_report()`, payloads válidos são entregues diretamente a `hid_input_events_process_report_for_device()`.

---

### 7. Ciclo de Serviço Contínuo no Runtime Nativo
- **Módulos**: `kernel/src/drivers/i2c_hid_manager.sotlas`, `kernel/src/baken_native_runtime.sotlas`
- **Problema**: O runtime nativo inicializava o manager no boot, mas seu loop de renderização de frames não possuía chamada de serviço para drenar filas I2C-HID.
- **Solução**:
  - Implementada a rotina `pub fn i2c_hid_manager_service_once() -> usize`.
  - Invocada continuamente no loop de quadros `baken_native_runtime_run()`, ao lado do serviço de hotplug USB xHCI.

---

### 8. Validação Robusta de `wLength` e Proteção de `pending_irq`
- **Módulo**: `kernel/src/drivers/i2c_hid_input.sotlas`
- **Solução**:
  - `wLength == 0`: confirmação de reset ou frame vazio (status OK).
  - `wLength == 1` ou `wLength > read_len`: pacote malformado (rejeição com `I2C_STATUS_INVALID`).
  - `pending_irq` só é limpo após leitura bem-sucedida; leituras com NACK ou timeout preservam a pendência para retry bounded.

---

### 9. Implementação Completa dos Comandos I2C-HID-5
- **Módulo**: `kernel/src/drivers/i2c_hid_command.sotlas`
- **Solução**:
  - `SET_POWER`: validação estrita rejeitando qualquer valor que não seja `I2C_HID_POWER_ON` ou `I2C_HID_POWER_SLEEP`.
  - `GET_REPORT` e `SET_REPORT`: framing canônico Microsoft suportando identificadores de relatório < 15 e >= 15 (com byte de extensão `0x0F` e framing em Data Register).
  - Avaliação `_DSM` Function 1 restrita unicamente a `AML_EVAL_VALUE_INTEGER` (ACPI_TYPE_INTEGER).
