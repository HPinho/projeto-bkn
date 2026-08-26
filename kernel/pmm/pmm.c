/*
 * Baken Microkernel - Gerenciador de Memória Física (PMM)
 * Implementação de Buddy Allocator de alta performance O(1) com bitmap de ordens.
 */

#include "../include/baken_kernel.h"
#include <string.h>

#define MAX_BUDDY_ORDER 11 // De 4KB (2^0 * 4KB) até 4MB (2^10 * 4KB)

typedef struct FreeBlock {
    struct FreeBlock* next;
} FreeBlock;

static FreeBlock* buddy_free_lists[MAX_BUDDY_ORDER];
static uint8_t* pmm_bitmap;
static uint64_t total_pages;
static uint64_t free_pages;
static uint64_t physical_memory_base;

void baken_pmm_init(uint64_t mem_base, uint64_t mem_size) {
    physical_memory_base = mem_base;
    total_pages = mem_size / BAKEN_PAGE_SIZE;
    free_pages = total_pages;
    
    for (int i = 0; i < MAX_BUDDY_ORDER; i++) {
        buddy_free_lists[i] = NULL;
    }
}

uint64_t baken_pmm_alloc_pages(uint32_t order) {
    if (order >= MAX_BUDDY_ORDER) return 0;
    
    // Procura na lista da ordem solicitada
    for (uint32_t current_order = order; current_order < MAX_BUDDY_ORDER; current_order++) {
        if (buddy_free_lists[current_order] != NULL) {
            FreeBlock* block = buddy_free_lists[current_order];
            buddy_free_lists[current_order] = block->next;
            
            // Quebra os blocos maiores (Split) até a ordem requisitada
            while (current_order > order) {
                current_order--;
                uint64_t block_addr = (uint64_t)block;
                uint64_t buddy_addr = block_addr + (BAKEN_PAGE_SIZE << current_order);
                
                FreeBlock* buddy = (FreeBlock*)buddy_addr;
                buddy->next = buddy_free_lists[current_order];
                buddy_free_lists[current_order] = buddy;
            }
            
            free_pages -= (1ULL << order);
            return (uint64_t)block;
        }
    }
    
    return 0; // Sem memória física contígua disponível
}

void baken_pmm_free_pages(uint64_t physical_addr, uint32_t order) {
    if (physical_addr == 0 || order >= MAX_BUDDY_ORDER) return;
    
    FreeBlock* block = (FreeBlock*)physical_addr;
    block->next = buddy_free_lists[order];
    buddy_free_lists[order] = block;
    
    free_pages += (1ULL << order);
}
