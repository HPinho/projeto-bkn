/*
 * Subsistema Q-HAL: Simulador Vetorial Quântico de Alta Precisão
 * Executa simulação matricial exata de estados quânticos no espaço de Hilbert C^(2^N)
 * com suporte à vetorização SIMD (AVX2/AVX-512 e ARM NEON).
 */

#ifndef BAKEN_QHAL_SIMULATOR_H
#define BAKEN_QHAL_SIMULATOR_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#define M_PI 3.14159265358979323846

typedef struct {
    double real;
    double imag;
} Complex64;

typedef struct {
    uint32_t num_qubits;
    uint64_t state_dim;      // 2^num_qubits
    Complex64* amplitudes;   // Vetor de amplitudes de probabilidade
} QuantumStateVector;

// Inicializa um registrador quântico no estado base |00...0>
QuantumStateVector* qhal_create_state_vector(uint32_t num_qubits);
void qhal_free_state_vector(QuantumStateVector* qsv);

// Aplicação de Portas Unitárias 1-Qubit
void qhal_apply_hadamard(QuantumStateVector* qsv, uint32_t target_qubit);
void qhal_apply_pauli_x(QuantumStateVector* qsv, uint32_t target_qubit);
void qhal_apply_pauli_y(QuantumStateVector* qsv, uint32_t target_qubit);
void qhal_apply_pauli_z(QuantumStateVector* qsv, uint32_t target_qubit);
void qhal_apply_phase(QuantumStateVector* qsv, uint32_t target_qubit, double theta);

// Aplicação de Portas 2-Qubits e 3-Qubits
void qhal_apply_cnot(QuantumStateVector* qsv, uint32_t control_qubit, uint32_t target_qubit);
void qhal_apply_toffoli(QuantumStateVector* qsv, uint32_t ctrl1, uint32_t ctrl2, uint32_t target);

// Operação de Medição e Colapso da Função de Onda de Von Neumann
uint8_t qhal_measure_qubit(QuantumStateVector* qsv, uint32_t target_qubit, double random_sample);

#endif // BAKEN_QHAL_SIMULATOR_H
