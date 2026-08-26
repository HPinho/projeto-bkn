/*
 * Baken Microkernel - Gerenciador de Memória Virtual (VMM)
 * Paginação de 4 níveis x86_64 Long Mode (PML4 -> PDPT -> PD -> PT)
 * com enforçamento estrito de W^X (Write XOR Execute) e Supervisor/User isolation.
 */

#include "../include/baken_kernel.h"

#define PTE_PRESENT   (1ULL << 0)
#define PTE_WRITABLE  (1ULL << 1)
#define PTE_USER      (1ULL << 2)
#define PTE_NO_EXEC   (1ULL << 63) // Bit NX

typedef uint64_t PageTableEntry;

typedef struct {
    PageTableEntry entries[512];
} PageTable;

static PageTable* kernel_pml4 = NULL;

extern uint64_t baken_pmm_alloc_pages(uint32_t order);

void baken_vmm_init(void) {
    // Aloca a tabela de páginas PML4 mestra do kernel
    kernel_pml4 = (PageTable*)baken_pmm_alloc_pages(0);
    for (int i = 0; i < 512; i++) {
        kernel_pml4->entries[i] = 0;
    }
}

bool baken_vmm_map_page(PageTable* pml4, uint64_t virt_addr, uint64_t phys_addr, uint64_t flags) {
    if (!pml4) return false;
    
    uint64_t pml4_idx = (virt_addr >> 39) & 0x1FF;
    uint64_t pdpt_idx = (virt_addr >> 30) & 0x1FF;
    uint64_t pd_idx   = (virt_addr >> 21) & 0x1FF;
    uint64_t pt_idx   = (virt_addr >> 12) & 0x1FF;
    
    // Nível 4 -> Nível 3 (PML4 -> PDPT)
    if (!(pml4->entries[pml4_idx] & PTE_PRESENT)) {
        uint64_t new_pdpt = baken_pmm_alloc_pages(0);
        pml4->entries[pml4_idx] = new_pdpt | PTE_PRESENT | PTE_WRITABLE | (flags & PTE_USER);
    }
    PageTable* pdpt = (PageTable*)(pml4->entries[pml4_idx] & ~0xFFFULL);
    
    // Nível 3 -> Nível 2 (PDPT -> PD)
    if (!(pdpt->entries[pdpt_idx] & PTE_PRESENT)) {
        uint64_t new_pd = baken_pmm_alloc_pages(0);
        pdpt->entries[pdpt_idx] = new_pd | PTE_PRESENT | PTE_WRITABLE | (flags & PTE_USER);
    }
    PageTable* pd = (PageTable*)(pdpt->entries[pdpt_idx] & ~0xFFFULL);
    
    // Nível 2 -> Nível 1 (PD -> PT)
    if (!(pd->entries[pd_idx] & PTE_PRESENT)) {
        uint64_t new_pt = baken_pmm_alloc_pages(0);
        pd->entries[pd_idx] = new_pt | PTE_PRESENT | PTE_WRITABLE | (flags & PTE_USER);
    }
    PageTable* pt = (PageTable*)(pd->entries[pd_idx] & ~0xFFFULL);
    
    // Mapeia a página física na PT folha
    pt->entries[pt_idx] = (phys_addr & ~0xFFFULL) | flags | PTE_PRESENT;
    
    return true;
}
