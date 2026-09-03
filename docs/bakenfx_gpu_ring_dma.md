# Arquitetura Barecore: GPU Command Ring Buffers & DMA no Baken OS

Esta especificação define a camada de comunicação direta entre o microkernel Sotlas (`target barecore`) e o hardware gráfico acelerador (iGPU integrada ou dGPU discreta), substituindo loops de scanline na CPU por submissão de pacotes assíncronos via **DMA Command Ring Buffers**.

---

## 1. Topologia de Memória e Canais de Comunicação

No modelo de execução freestanding do Baken OS, a CPU nunca escreve diretamente nos registradores internos da GPU para cada operação gráfica. Em vez disso, opera através de três primitivas de arquitetura:

1. **`*dmazone` (DMA Command Ring Buffer):** Área circular de memória física contígua e não-cacheável (Write-Combining) compartilhada entre a CPU e o controlador DMA da GPU.
2. **`*portwire` (MMIO Doorbell Register):** Registrador de disparo mapeado em memória que avisa a GPU sobre novos comandos enfileirados no anel.
3. **Hardware Fence & MSI-X (Sincronização Assíncrona):** A GPU emite um Fence Sequence ID e gera uma interrupção MSI-X quando uma fila de comandos é concluída.

```
+------------------+         DMA Ring Buffer (*dmazone)          +------------------+
|                  |  ---------------------------------------->  |                  |
|    CPU Core      |                                             |    GPU Engine    |
| (Sotlas Kernel)  |  --[ Doorbell MMIO (*portwire) ]--------->  | (2D Blit / 3D)   |
|                  |  <--[ Fence IRQ / MSI-X Completion ]------  |                  |
+------------------+                                             +------------------+
```

---

## 2. Formato do Pacote de Comandos (`BakenGpuCommandPacket`)

Cada comando no anel é composto por uma estrutura de 32 bytes alinhada em 64 bits:

```c
typedef struct __attribute__((aligned(32))) {
    uint16_t opcode;        // 0x01: FastBlit, 0x02: Convolve5Tap, 0x03: SquircleFill, 0x04: Fence
    uint16_t flags;         // BITS: [0]: BlendAlpha, [1]: ClipEn, [2]: SignalFence
    uint32_t sequence_id;   // Identificador de Fence emitido na conclusão
    uint64_t src_phys_addr; // Endereço físico do buffer de origem (ex: backdrop scratch)
    uint64_t dst_phys_addr; // Endereço físico do destino (framebuffer / backbuffer)
    uint16_t clip_x;
    uint16_t clip_y;
    uint16_t clip_w;
    uint16_t clip_h;
    uint32_t param_kernel;  // Parâmetros de convolução (raio, pesos, cor de tingimento)
} BakenGpuCommandPacket;
```

---

## 3. Anel de Comandos Circular (`GpuCommandRing`)

O anel opera com ponteiros de leitura (GPU `Head`) e escrita (CPU `Tail`):

```sotlas
pub struct GpuCommandRing {
    pub ring_phys_base: u64;
    pub ring_virt_base: *mut BakenGpuCommandPacket;
    pub ring_capacity: u32;    // Tipicamente 1024 a 4096 slots
    pub tail_index: u32;       // Gerenciado pela CPU
    pub doorbell_mmio: *mut u32;
}

@system
pub fn gpu_ring_submit_blur_convolve(
    ring: *mut GpuCommandRing,
    src_phys: u64,
    dst_phys: u64,
    clip: Rect,
    blur_radius: u32
) -> u32 {
    unsafe {
        let tail = (*ring).tail_index;
        let slot = (*ring).ring_virt_base.add(tail as usize);
        
        (*slot).opcode = 0x02; // Convolve5Tap
        (*slot).flags = 0x0003; // Blend + Clip
        (*slot).sequence_id = tail + 1;
        (*slot).src_phys_addr = src_phys;
        (*slot).dst_phys_addr = dst_phys;
        (*slot).clip_x = clip.x as u16;
        (*slot).clip_y = clip.y as u16;
        (*slot).clip_w = clip.width as u16;
        (*slot).clip_h = clip.height as u16;
        (*slot).param_kernel = blur_radius;

        // Avança o ponteiro circular
        let next_tail = (tail + 1) % (*ring).ring_capacity;
        (*ring).tail_index = next_tail;

        // Dispara o Doorbell Register da GPU via MMIO (*portwire)
        *(*ring).doorbell_mmio = next_tail;

        return (*slot).sequence_id;
    }
}
```

---

## 4. Benefícios de Latência e CPU

1. **Zero CPU Overhead:** A CPU não itera por scanlines ou faz amostragens por pixel. Ela apenas gasta ~15 ciclos para preencher o descritor de 32 bytes.
2. **Paralelismo Real:** Enquanto a GPU executa a convolução ou blit diretamente na VRAM, a CPU executa física de molas (`bakenfx_tick_spring_physics`), despacho de eventos e árvore de layout.
3. **Pipeline Pipelined:** Várias superfícies (janelas, dock, sombras) são enfileiradas em um único burst e a GPU executa tudo em uma passagem sem trocas de contexto.
