# Baken OS — I2C Roadmap Appendix V

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores.

## Correction-only após I2C-2a 3/4

O candidato I2C-2a `022bbec682d6ea5730c110919f21f044ffec8849` permanece **não certificado**: CI #1220 ✅, NVMe #420 ✅, HID #79 ✅ e SMP #323 ❌.

O primeiro commit diagnóstico `521f1dcc3d3a3c31ef34ccddbb21cc5add2c8203` adicionou apenas observabilidade de CI, sem alterar código funcional do kernel. O workflow `baken_smp_fault_diag.yml` falhou antes de criar qualquer job devido a um heredoc Python fora da indentação válida de YAML. Essa falha é de infraestrutura diagnóstica e permanece registrada; não reclassifica o resultado SMP anterior.

### Correction-only atual

A próxima correção mantém o kernel funcionalmente inalterado e corrige somente a infraestrutura de diagnóstico:

- remove o heredoc Python do workflow;
- adiciona `tools/scripts/symbolize_pe_rip.py` para resolver o RIP pelo `nm -n` do `BOOTX64.EFI`;
- executa QEMU com `-d int` para capturar o contexto de #PF/CR2;
- imprime `nm`/símbolo mais próximo e `objdump` em torno do RIP;
- mantém I2C-2b bloqueado até a causa do #PF do AP ser identificada e corrigida.

## Gate de retomada

Nenhum novo microcorte funcional de I2C deve ser publicado enquanto a sequência correction-only não produzir um SHA com CI principal + SMP + NVMe-only + HID Dual-device verdes. Se o #PF reproduzir, a próxima alteração deve ser exclusivamente a correção mínima da causa raiz.
