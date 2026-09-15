# Evidências comunitárias I²C do Baken OS

Esta pasta aceita evidências **anonimizadas** de máquinas físicas e fixtures
sintéticas. Evidência física pode certificar uma combinação de controlador e
revisão; fixture sintética testa parsing/falhas, mas não pode declarar `pass`.

Nunca envie serial, UUID, hostname, MAC, usuário, dump de BIOS ou ACPI bruto.
Converta somente os campos necessários para o JSON versionado e execute:

```text
python tools/scripts/validate_i2c_hardware_fixture.py arquivo.json
```

Resultados aceitos: `pass`, `fail`, `not-tested` e `not-applicable`. Um backend
só pode sair do modo fail-closed depois de evidência física para a mesma identidade
ACPI/PCI, revisão do controlador e versão do componente.
