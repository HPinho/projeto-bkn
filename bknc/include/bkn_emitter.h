/*
 * BKNC - Emissor de Binários Executáveis Nativos .bkn_exec
 * Constrói o cabeçalho soberano, tabelas Q-IR e assinaturas Dilithium.
 */

#ifndef BKNC_EMITTER_H
#define BKNC_EMITTER_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define BKN_EXEC_MAGIC "\x7f" "BKNEXEC"

typedef struct __attribute__((packed)) {
    char magic[8];              // \x7fBKNEXEC\0
    uint16_t version;           // 0x0100 (v1.0)
    uint16_t target_arch;       // 0x01 (x86_64), 0x02 (ARM64), 0x03 (RISC-V)
    uint32_t security_flags;    // Bit 0: Signed, Bit 1: Encrypted, Bit 2: Quantum-Enabled
    uint64_t entry_point_classical;
    uint64_t entry_point_quantum;
    uint64_t meta_offset;
    uint64_t meta_size;
    uint64_t text_offset;
    uint64_t text_size;
    uint64_t quantum_offset;
    uint64_t quantum_size;
    uint64_t rodata_offset;
    uint64_t rodata_size;
    uint64_t sig_offset;
    uint64_t sig_size;
    uint8_t header_hash[16];
    uint8_t reserved[16];
} BknExecHeader;

bool bkn_emit_binary(
    const char* output_path,
    uint16_t arch,
    const void* text_code, size_t text_len,
    const void* quantum_circuit_ir, size_t quantum_len,
    const void* meta_caps, size_t meta_len
);

#endif // BKNC_EMITTER_H
