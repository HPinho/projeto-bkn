/*
 * Baken OS - Runtime de Inferência de IA, Auto-Reparo e Otimização Quântica em C Puro
 * Implementação Completa de Todas as 20 Fases da Arquitetura Soberana
 */

#ifndef BKN_AI_H
#define BKN_AI_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint32_t temperature;
    uint32_t max_tokens;
    bool use_avx512;
    bool use_gpu_accel;
    uint8_t security_ring;
} bkn_ai_config_t;

// Fases 1 a 5: Inferência On-Device e Otimização Quântica
int32_t bkn_ai_init_runtime(const bkn_ai_config_t *config);
int32_t bkn_ai_infer_tokens(const uint8_t *prompt, uint32_t prompt_len, uint8_t *output, uint32_t max_out);
float bkn_ai_optimize_quantum_circuit(uint32_t qubits, uint32_t depth);

// Fases 6 a 12: Self-Healing, mmap, AVX-512, Mesh P2P, OpenQASM
int32_t bkn_ai_heal_fault(uint8_t fault_type, uint32_t pid, uint64_t rip);
int32_t bkn_ai_mmap_tensor_weights(const char *path, uint64_t *out_vaddr);
uint32_t bkn_ai_superoptimize_asm(const uint32_t *in_asm, uint32_t count, uint32_t *out_asm);
int32_t bkn_ai_mesh_sync_gradients(const uint8_t *node_ip, const float *grad, uint32_t count);
int32_t bkn_ai_export_openqasm3(uint32_t qubits, char *out_qasm, uint32_t max_len);

// Fases 13 a 20: QN-Bus, Vector BakenFS, DynaJIT, Capabilities, BakenBridge, InstantBoot
uint32_t bkn_qn_bus_latency_ns(void);
int32_t bkn_bakenfs_vector_query(const float *query_embedding, uint32_t dims, char *out_path);
float bkn_dynajit_get_speedup(void);
bool bkn_capabilities_verify(uint32_t pid, uint64_t cap_mask);
int32_t bkn_baken_bridge_exec_elf(const char *elf_path);
uint32_t bkn_instant_boot_time_ms(void);

#endif // BKN_AI_H
