# Especificação da Camada Universal de Periféricos (Baken Universal HID)
Versão: 1.0.0-UNIVERSAL
Arquitetura: Barramento Unificado de Eventos de Entrada com Suporte a USB 3/4 (XHCI), Bluetooth BLE e I2C/PS2

---

## 1. Visão Geral
O **Baken Universal HID Subsystem** garante compatibilidade *Plug-and-Play* imediata com qualquer dispositivo apontador, teclado ou controlador no planeta:
1. **Mouses Gamer & Profissionais:** Suporte a taxas de amostragem de 125 Hz a 8000 Hz (Logitech Lightspeed, Razer, Corsair, Zowie, SteelSeries).
2. **Dispositivos Sem Fio & Bluetooth:** Rastreamento absoluto e relativo automático para mouses Bluetooth BLE, RF 2.4 GHz e Magic Mouse/Trackpads.
3. **Teclados Universais:** Suporte a N-Key Rollover (NKRO), layouts internacionais (ABNT2, US-Intl, ISO), teclas multimídia e teclados mecânicos USB/Bluetooth.
4. **Touchpads & Telas Sensíveis ao Toque (Multi-Touch):** Gestos de rolagem com 2 dedos, pinça de zoom e canetas stylus ativas.

---

## 2. Estrutura do Evento Unificado de Entrada (`BknInputEvent`)

```
Campo                   Tamanho (Bytes)  Descrição
Tipo de Dispositivo     1                `0x01`: Mouse, `0x02`: Teclado, `0x03`: Touchpad, `0x04`: Gamepad
ID do Dispositivo       1                Identificador do barramento (USB XHCI, EHCI, Bluetooth, PS/2)
Botões / Modificadores  2                Máscara de bits de botões (Esq, Dir, Meio, Shift, Ctrl, Alt, Meta)
Coordenada X Absoluta   4                Posição horizontal na tela (0 a Width-1)
Coordenada Y Absoluta   4                Posição vertical na tela (0 a Height-1)
Delta X Relativo        4                Variação de movimento horizontal
Delta Y Relativo        4                Variação de movimento vertical
Delta Scroll Roda       2                Rolagem vertical/horizontal
Código do Caractere     2                Caractere UTF-16 ou Scancode da tecla pressionada
Timestamp de Alta Prec. 8                Contador de nanossegundos do TSC da CPU
```
