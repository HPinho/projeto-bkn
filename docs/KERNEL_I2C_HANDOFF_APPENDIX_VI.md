# Baken OS — Kernel I2C Handoff Appendix VI

> Append-only. Preservar integralmente todos os apêndices e resultados anteriores.

## Estado correction-only

`main` entrou nesta etapa em `6fb5e24953e44d48b330bed9b417aafb13afde6d`. I2C-2a continua funcionalmente presente, mas não certificado devido ao gate SMP.

Resultados já fechados ou observados no SHA:

- NVMe-only #422 ✅
- HID Dual-device #81 ✅
- SMP #325 ❌
- CI #1222: suíte completa, grafo modular, build nativo e ISO ✅; smoke QEMU ainda em execução quando a causa raiz foi fechada.
- `SMP Fault Diagnostic #2`: 3/3 boots sem reprodução (`FAULT_REPRODUCED=0`).

A ausência de falha no diagnóstico suplementar não invalida SMP #325: a corrida depende de timing/stack reuse e o gate oficial reproduziu novamente o erro.

## Diagnóstico fechado

Artifact do diagnóstico forneceu o `BOOTX64.EFI` exato e símbolos. `0x10011BA5` resolve para:

`__sotlas_x86_irq_common + 0x55` → `iretq`

No SMP #325 proof 2, após `M:8` e antes de `M:9`:

- `E=0x0D` (#GP)
- error code `0x40`
- RIP `0x10011BA5`
- CS interrompido `0x08`
- CPU slot `1`
- scheduler thread id `0`

A GDT tem limite `0x3F`. O error code `0x40` é, portanto, selector inválido e coincide exatamente com `IRQ_VECTOR_TIMER`. Pelo layout do common IRQ frame, isso demonstra que o `iretq` consumiu um frame deslocado/stale no qual o vetor do timer apareceu na posição de CS.

## Causa raiz no scheduler

Em `scheduler_on_secondary_interrupt()` o caminho idle do AP era:

```text
if current == INVALID:
    if idle_frame == 0:
        idle_frame = frame_address
    procurar próxima thread
```

O problema é de lifetime. O frame salvo por uma IRQ idle vive na pilha permanente do runtime do AP. Depois que o `iretq` consome esse frame e retorna ao loop do AP, aquela região abaixo do RSP não permanece reservada e pode ser reutilizada por chamadas normais. Guardar para sempre o primeiro endereço cria um return target stale.

## Correction-only a publicar

Alterar somente o caminho `current == SCHEDULER_INVALID_SLOT` para:

```text
SCHEDULER_CPU_IDLE_FRAME[cpu_slot] = frame_address
procurar próxima thread
```

A publicação deve ocorrer em toda IRQ recebida enquanto o AP está realmente idle e antes da seleção de uma nova thread. Se não houver dispatch, a IRQ retorna pelo próprio frame atual. Se houver dispatch, esse frame fresco fica preservado como destino seguro até a thread deixar o CPU.

Adicionar guardrail em `tests/test_kernel_smp_timer_preemption.py` exigindo a atribuição incondicional antes de `scheduler_find_next_ready_for_cpu()` e proibindo a condição histórica `idle_frame == 0` nesse caminho.

## Regras após publicação

- Nenhum I2C-2b enquanto o correction-only não fechar 4/4.
- Nenhuma mudança LangSotlas esperada.
- Se o novo SHA falhar, permanecer correction-only e diagnosticar a nova assinatura; não afrouxar o gate.
- Se CI + SMP + NVMe + HID ficarem verdes no mesmo SHA, registrar a certificação e então liberar a continuação do I2C-2.
