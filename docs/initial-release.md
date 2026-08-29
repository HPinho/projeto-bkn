# Baken OS — versão inicial (MVP)

## O que é entregue

- Rota de boot UEFI validada no QEMU em 27/08/2026, tanto pelo disco UEFI
  gravável quanto pela ISO óptica El Torito. VirtualBox continua sendo a
  próxima porta de validação antes de distribuir uma imagem mais ampla.
- Uma única rota de interface em execução: bootloader -> kernel gráfico ->
  desktop. A árvore Cq tem `kernel::main -> desktop_compositor` como rota
  canônica validada pelo VortexC.
- Desktop gráfico com wallpaper, topbar, dock, widgets e cursor. O dock ainda
  é layout visual; não abre aplicativos até o lançador e os serviços existirem.
- Prévia do assistente de instalação no mesmo tema do desktop; ela não grava
  discos nem avança para uma instalação concluída.
- Persistência mínima de teste: confirmação no assistente grava `INSTALL1`
  na imagem virtual via UEFI Block I/O; o registro é reconhecido após reboot.
- Testes automatizados do grafo de módulos Cq, contratos de segurança e
  empacotamento. O boot em VM é executado separadamente antes de uma ISO.

## Como validar

```powershell
python -m unittest tests/test_vortexc_resolver.py
python tools/vortexc/vortexc.py check kernel/src/main.cq --manifest build/cq-main.manifest.json
./tools/build_uefi_desktop.ps1
python tools/scripts/create_fat32_img.py
python tools/test_qemu_desktop.py --install
```

## Limites conhecidos

Esta é uma versão inicial, não uma distribuição de produção. O registro
persistente ainda não é um BakenFS completo: arquivos de usuário, permissões,
diretórios e cópia do rootfs continuam sendo a próxima etapa. A ISO El Torito
é mídia óptica para VM, não uma imagem híbrida para pendrive. O VortexC resolve
e valida o grafo Cq, mas a ISO ainda usa a ponte C documentada enquanto o
backend de geração de objetos Cq é ampliado.
