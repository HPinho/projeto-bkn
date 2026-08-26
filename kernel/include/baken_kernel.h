/*
 * Baken Microkernel - Cabeçalho Mestre do Sistema
 * Zero dependência de Unix/Linux/POSIX/Windows
 */

#ifndef BAKEN_KERNEL_H
#define BAKEN_KERNEL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define BAKEN_PAGE_SIZE 4096
#define MAX_CORES       256
#define MAX_CAPABILITIES 1024

// Identificadores de Chamadas de Sistema (Syscalls Nativas Baken)
typedef enum {
    SYS_YIELD            = 0x01,
    SYS_THREAD_CREATE    = 0x02,
    SYS_THREAD_EXIT      = 0x03,
    SYS_CAP_GRANT        = 0x10,
    SYS_CAP_REVOKE       = 0x11,
    SYS_IPC_SEND         = 0x20,
    SYS_IPC_RECEIVE      = 0x21,
    SYS_IPC_CALL         = 0x22,
    SYS_VMM_MAP_PAGE     = 0x30,
    SYS_VMM_UNMAP_PAGE   = 0x31,
    SYS_QPU_ALLOC_QREG   = 0x40,
    SYS_QPU_SUBMIT_DAG   = 0x41,
    SYS_QPU_MEASURE_SYNC = 0x42
} BakenSyscallNumber;

// Estados de Thread no Scheduler Híbrido
typedef enum {
    THREAD_STATE_READY,
    THREAD_STATE_RUNNING,
    THREAD_STATE_BLOCKED_IPC,
    THREAD_STATE_SUSPENDED_QUANTUM, // Aguardando colapso de circuito QPU/Q-HAL
    THREAD_STATE_TERMINATED
} BakenThreadState;

// Token de Capacidade (Controle de Acesso em Ring 3)
typedef struct {
    uint64_t object_id;
    uint32_t permissions; // READ, WRITE, EXECUTE, MMIO_ACCESS, DMA_GRANT
    uint32_t generation;
} BakenCapability;

// Estrutura de Contexto de Thread (Registradores x86_64)
typedef struct {
    uint64_t r15, r14, r13, r12, r11, r10, r9, r8;
    uint64_t rbp, rdi, rsi, rdx, rcx, rbx, rax;
    uint64_t rip, cs, rflags, rsp, ss;
    uint64_t cr3; // Diretório de páginas VMM exclusivo do processo
} BakenCpuContext;

// Estrutura de Thread
typedef struct BakenThread {
    uint64_t thread_id;
    uint64_t process_id;
    uint32_t priority;
    BakenThreadState state;
    BakenCpuContext context;
    uint64_t quantum_job_id; // Se suspenso em computação quântica
    struct BakenThread* next;
} BakenThread;

// Funções Principais do Núcleo
void baken_kernel_init(void* uefi_boot_info);
void baken_hal_init(void);
void baken_pmm_init(uint64_t mem_base, uint64_t mem_size);
void baken_vmm_init(void);
void baken_scheduler_init(void);
void baken_ipc_init(void);
void baken_qhal_init(void);

#endif // BAKEN_KERNEL_H
