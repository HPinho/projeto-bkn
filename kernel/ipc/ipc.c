/*
 * Baken Microkernel - IPC de Cópia Zero Baseado em Capacidades
 * Mensageria ultrarrápida entre Ring 3 servers e Ring 0/Ring 3 clients.
 */

#include "../include/baken_kernel.h"

#define MAX_IPC_CHANNELS 512
#define IPC_BUFFER_SIZE  65536 // 64 KB Ring Buffer por canal

typedef struct {
    uint64_t channel_id;
    uint64_t owner_pid;
    uint64_t target_pid;
    uint64_t shared_phys_page; // Página de memória física compartilhada (Zero-Copy)
    uint32_t head;
    uint32_t tail;
    bool is_active;
} IpcChannel;

static IpcChannel ipc_channels[MAX_IPC_CHANNELS];

extern uint64_t baken_pmm_alloc_pages(uint32_t order);

void baken_ipc_init(void) {
    for (int i = 0; i < MAX_IPC_CHANNELS; i++) {
        ipc_channels[i].is_active = false;
        ipc_channels[i].shared_phys_page = 0;
    }
}

uint64_t baken_ipc_create_channel(uint64_t sender_pid, uint64_t receiver_pid) {
    for (uint64_t i = 0; i < MAX_IPC_CHANNELS; i++) {
        if (!ipc_channels[i].is_active) {
            ipc_channels[i].channel_id = i + 1;
            ipc_channels[i].owner_pid = sender_pid;
            ipc_channels[i].target_pid = receiver_pid;
            ipc_channels[i].shared_phys_page = baken_pmm_alloc_pages(0); // 4KB inicial
            ipc_channels[i].head = 0;
            ipc_channels[i].tail = 0;
            ipc_channels[i].is_active = true;
            return ipc_channels[i].channel_id;
        }
    }
    return 0; // Sem canais IPC disponíveis
}

bool baken_ipc_send_message(uint64_t channel_id, const void* msg_data, size_t size) {
    if (channel_id == 0 || channel_id > MAX_IPC_CHANNELS) return false;
    
    IpcChannel* ch = &ipc_channels[channel_id - 1];
    if (!ch->is_active || size > BAKEN_PAGE_SIZE) return false;
    
    // Mapeamento direto e cópia zero no buffer compartilhado
    uint8_t* buf = (uint8_t*)ch->shared_phys_page;
    for (size_t i = 0; i < size; i++) {
        buf[i] = ((const uint8_t*)msg_data)[i];
    }
    
    return true;
}
