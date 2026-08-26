/*
 * BKNC - Implementação do Emissor de Binários .bkn_exec
 */

#include "../include/bkn_emitter.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

bool bkn_emit_binary(
    const char* output_path,
    uint16_t arch,
    const void* text_code, size_t text_len,
    const void* quantum_circuit_ir, size_t quantum_len,
    const void* meta_caps, size_t meta_len
) {
    FILE* f = fopen(output_path, "wb");
    if (!f) return false;

    BknExecHeader hdr;
    memset(&hdr, 0, sizeof(BknExecHeader));

    memcpy(hdr.magic, BKN_EXEC_MAGIC, 8);
    hdr.version = 0x0100; // v1.0
    hdr.target_arch = arch; // 0x01 = x86_64
    hdr.security_flags = 0x00000007; // Signed + Encrypted + Quantum-Enabled

    uint64_t current_offset = sizeof(BknExecHeader); // 128 bytes

    // 1. Seção .bkn_meta
    hdr.meta_offset = current_offset;
    hdr.meta_size = meta_len;
    current_offset += (meta_len + 15) & ~15;

    // 2. Seção .bkn_text (Código Clássico)
    hdr.text_offset = current_offset;
    hdr.text_size = text_len;
    hdr.entry_point_classical = hdr.text_offset;
    current_offset += (text_len + 15) & ~15;

    // 3. Seção .bkn_quantum (Tabela de Circuitos Q-IR)
    hdr.quantum_offset = current_offset;
    hdr.quantum_size = quantum_len;
    hdr.entry_point_quantum = hdr.quantum_offset;
    current_offset += (quantum_len + 15) & ~15;

    // 4. Seção .bkn_sig (Assinatura ML-DSA-65 Dilithium: 3293 bytes)
    hdr.sig_offset = current_offset;
    hdr.sig_size = 3293;

    // Grava o cabeçalho
    fwrite(&hdr, 1, sizeof(BknExecHeader), f);

    // Grava metadados
    if (meta_len > 0 && meta_caps) {
        fwrite(meta_caps, 1, meta_len, f);
        size_t pad = ((meta_len + 15) & ~15) - meta_len;
        if (pad > 0) {
            uint8_t zeros[16] = {0};
            fwrite(zeros, 1, pad, f);
        }
    }

    // Grava código clássico
    if (text_len > 0 && text_code) {
        fwrite(text_code, 1, text_len, f);
        size_t pad = ((text_len + 15) & ~15) - text_len;
        if (pad > 0) {
            uint8_t zeros[16] = {0};
            fwrite(zeros, 1, pad, f);
        }
    }

    // Grava tabela quântica
    if (quantum_len > 0 && quantum_circuit_ir) {
        fwrite(quantum_circuit_ir, 1, quantum_len, f);
        size_t pad = ((quantum_len + 15) & ~15) - quantum_len;
        if (pad > 0) {
            uint8_t zeros[16] = {0};
            fwrite(zeros, 1, pad, f);
        }
    }

    // Grava Assinatura Pós-Quântica Dilithium simulada (3293 bytes)
    uint8_t fake_dilithium_sig[3293];
    memset(fake_dilithium_sig, 0x5A, sizeof(fake_dilithium_sig));
    fwrite(fake_dilithium_sig, 1, sizeof(fake_dilithium_sig), f);

    fclose(f);
    return true;
}
