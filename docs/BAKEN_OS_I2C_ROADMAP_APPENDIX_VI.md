# Baken OS — I2C Roadmap Appendix VI

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores.

## Correction-only SMP — causa raiz do frame idle do AP

O SHA diagnóstico `6fb5e24953e44d48b330bed9b417aafb13afde6d` preservou o kernel funcional do candidato I2C-2a e confirmou que a falha SMP é intermitente. O workflow diagnóstico suplementar executou 3 boots sem reproduzir a exceção, mas o gate oficial SMP #325 voltou a falhar em uma execução independente.

Estado conhecido desse SHA:

- NVMe-only #422 ✅
- HID Dual-device #81 ✅
- SMP #325 ❌
- CI principal #1222 chegou a suíte/grafo/build/ISO verdes e permaneceu em smoke QEMU durante a análise; seu resultado terminal deve ser preservado quando disponível.

### Evidência de baixo nível

A symbolização do `BOOTX64.EFI` exato resolveu `RIP 0x10011BA5` para `__sotlas_x86_irq_common + 0x55`, precisamente a instrução `iretq`.

No segundo crash do SMP #325:

- exceção `#GP` (`0x0D`);
- error code `0x40`;
- CPU slot `1`;
- thread id do scheduler `0`;
- execução entre os checkpoints de migração `M:8` e `M:9`.

O selector `0x40` coincide com o vetor do LAPIC timer e está imediatamente além do limite da GDT (`0x3F`). Pelo layout do common IRQ frame, isso é compatível com retorno por um frame idle stale/corrompido: o vetor salvo passa a ser interpretado como `CS` durante o `iretq`.

### Causa raiz

`scheduler_on_secondary_interrupt()` publicava `SCHEDULER_CPU_IDLE_FRAME[cpu_slot]` somente quando o slot ainda era zero. Esse primeiro frame pertence à pilha do runtime do AP e, após o `iretq`, sua memória volta a ser pilha comum. Manter seu endereço indefinidamente permite que chamadas posteriores sobrescrevam o conteúdo e que uma thread futura tente retornar para um frame idle antigo.

### Correção

Enquanto `SCHEDULER_CPU_CURRENT_SLOT[cpu_slot] == SCHEDULER_INVALID_SLOT`, o scheduler deve sempre renovar `SCHEDULER_CPU_IDLE_FRAME[cpu_slot]` com o `frame_address` da IRQ atual **antes** de procurar uma thread runnable. Assim, quando essa IRQ despacha trabalho, o frame guardado representa exatamente o ponto idle fresco e seguro ao qual o AP poderá retornar depois.

Um guardrail em `tests/test_kernel_smp_timer_preemption.py` deve impedir a volta da condição histórica `if SCHEDULER_CPU_IDLE_FRAME[cpu_slot] == 0`.

## Gate de retomada

I2C-2b continua bloqueado. A correção só libera evolução funcional quando CI principal + SMP + NVMe-only + HID Dual-device passarem no mesmo SHA. O workflow diagnóstico permanece apenas suplementar; ele não substitui o gate SMP oficial de três boots.
