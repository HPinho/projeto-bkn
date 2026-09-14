# Baken OS — Kernel I2C Handoff Appendix XII

> Append-only. Este apêndice complementa a documentação técnica sem sobrescrever nenhum apêndice anterior.
> Documenta os contratos de interface e estruturas atualizadas do subsistema I2C-HID endurecido.

## 2026-09-14 — Contratos e Interfaces do Subsistema I2C-HID Hardened

### 1. Assinaturas e Funções Públicas Atualizadas

#### `kernel::drivers::i2c_hid_acpi`
- `pub fn i2c_hid_acpi_scan_devices() -> usize`: Varredura idempotente de dispositivos ACPI com `_CID`/`_HID` PNP0C50 ou ACPI0C50.
- `pub fn i2c_hid_acpi_device_count() -> usize`: Retorna a quantidade de dispositivos descobertos sem disparar nova varredura.
- `pub fn i2c_hid_acpi_get_device(index: usize) -> I2cHidAcpiDescriptor`: Retorna cópia thread-safe do descritor ACPI, incluindo `gpio_resource_index`.

#### `kernel::drivers::i2c_hid_command`
- `pub fn i2c_hid_command_set_power(device_id: u32, generation: u32, command_register: u16, power_state: u8) -> u8`: Valida estritamente se `power_state` é `I2C_HID_POWER_ON` (0) ou `I2C_HID_POWER_SLEEP` (1).
- `pub fn i2c_hid_command_reset(device_id: u32, generation: u32, command_register: u16) -> u8`: Dispara o comando de reinicialização do dispositivo.
- `pub fn i2c_hid_command_get_report(device_id: u32, generation: u32, command_register: u16, data_register: u16, report_type: u8, report_id: u8, out_buf: *mut u8, read_len: usize) -> u8`: Suporta IDs < 15 e >= 15 com framing canônico Microsoft.
- `pub fn i2c_hid_command_set_report(device_id: u32, generation: u32, command_register: u16, data_register: u16, report_type: u8, report_id: u8, report_data: *const u8, report_length: usize) -> u8`: Framing de gravação com prefixo de tamanho de 2 bytes LE.

#### `kernel::drivers::i2c_hid_input`
- `pub fn i2c_hid_input_fetch_report(device_index: usize, out_buf: *mut u8, buf_capacity: usize, out_report_len: *mut usize) -> u8`: Executa transação pura `i2c_device_read()`, valida `wLength`, trata `wLength == 0` (reset ACK) e despacha relatórios para `hid_input_events_process_report_for_device()`.
- `pub fn i2c_hid_input_notify_irq(gpio_pin: u16) -> void`: Sinaliza interrupção recebida para processamento diferido.
- `pub fn i2c_hid_input_has_pending_irq(device_index: usize) -> bool`: Consulta se o dispositivo possui requisição pendente.

#### `kernel::drivers::i2c_hid_manager`
- `pub fn i2c_hid_manager_init() -> usize`: Inicializa e conecta descoberta ACPI, registro GPIO, leitura de descritor, handshake de reset, parsing de relatórios e anexação ao modelo genérico de dispositivos de entrada.
- `pub fn i2c_hid_manager_service_once() -> usize`: Executado em cada quadro no runtime, consome interrupções GPIO e drena relatórios I²C pendentes.
- `pub fn i2c_hid_manager_device_count() -> usize`: Retorna a quantidade de dispositivos I2C-HID gerenciados.

#### `kernel::drivers::i2c_device`
- `pub fn i2c_device_set_gpio(device_id: u32, generation: u32, gpio_connection_id: u32, gpio_generation: u32) -> bool`: Associa conexão de interrupção GPIO ao dispositivo I2C.

---

### 2. Fluxo Canônico do Dispositivo Físico I2C-HID

```
ACPI DSDT (PNP0C50 / ACPI0C50)
        │
        ▼
_DSM(Function 0 -> Function 1 [Integer only])
        │
        ▼
i2c_device_attach() & i2c_device_activate()
        │
        ▼
gpio_connection_register_from_acpi()
        │
        ▼
i2c_hid_read_descriptor_physical() [30 bytes LE]
        │
        ▼
SET_POWER(ON) ──► OK?
        │
        ▼
RESET ──────────► OK?
        │
        ▼
Polling Handshake ACK (wLength == 0x0000) ──► OK?
        │
        ▼
i2c_hid_read_report_descriptor_physical() [<= 2048 bytes]
        │
        ▼
hid_report_descriptor_parse() [Mouse, Touchpad, Keyboard]
        │
        ▼
input_device_attach() -> input_device_activate()
        │
        ▼
hid_input_device_map_build() -> hid_input_events_bind_device()
        │
        ▼
[Runtime Frame Loop]
        │
        ▼
i2c_hid_manager_service_once()
        │
        ├── gpio_connection_consume_pending() ──► i2c_hid_input_notify_irq()
        └── i2c_hid_input_fetch_report() [Pure READ]
                 │
                 ▼
        hid_input_events_process_report_for_device()
                 │
                 ▼
        input_event_publish_for_device() -> Sistema Gráfico / Shell / Desktop
```
