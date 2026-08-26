/*
 * Subsistema Q-HAL: Implementação dos Algoritmos Matriciais Quânticos
 * Cálculos vetoriais de produtos tensoriais e transformações unitárias.
 */

#include "quantum_simulator.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

static inline Complex64 complex_add(Complex64 a, Complex64 b) {
    Complex64 res = { a.real + b.real, a.imag + b.imag };
    return res;
}

static inline Complex64 complex_sub(Complex64 a, Complex64 b) {
    Complex64 res = { a.real - b.real, a.imag - b.imag };
    return res;
}

static inline Complex64 complex_mul(Complex64 a, Complex64 b) {
    Complex64 res = { 
        a.real * b.real - a.imag * b.imag,
        a.real * b.imag + a.imag * b.real
    };
    return res;
}

static inline double complex_norm_sq(Complex64 a) {
    return a.real * a.real + a.imag * a.imag;
}

QuantumStateVector* qhal_create_state_vector(uint32_t num_qubits) {
    if (num_qubits == 0 || num_qubits > 30) return NULL; // Limite de 30 qubits em RAM (16GB)
    
    QuantumStateVector* qsv = (QuantumStateVector*)malloc(sizeof(QuantumStateVector));
    if (!qsv) return NULL;
    
    qsv->num_qubits = num_qubits;
    qsv->state_dim = 1ULL << num_qubits;
    
    qsv->amplitudes = (Complex64*)calloc(qsv->state_dim, sizeof(Complex64));
    if (!qsv->amplitudes) {
        free(qsv);
        return NULL;
    }
    
    // Estado inicial puro |0...0> = amplitude 1.0 no índice 0
    qsv->amplitudes[0].real = 1.0;
    qsv->amplitudes[0].imag = 0.0;
    
    return qsv;
}

void qhal_free_state_vector(QuantumStateVector* qsv) {
    if (qsv) {
        if (qsv->amplitudes) free(qsv->amplitudes);
        free(qsv);
    }
}

// Porta Hadamard: H = 1/sqrt(2) * [[1, 1], [1, -1]]
void qhal_apply_hadamard(QuantumStateVector* qsv, uint32_t target_qubit) {
    if (!qsv || target_qubit >= qsv->num_qubits) return;
    
    const double inv_sqrt2 = 0.7071067811865475;
    uint64_t target_mask = 1ULL << target_qubit;
    
    for (uint64_t i = 0; i < qsv->state_dim; i++) {
        if ((i & target_mask) == 0) {
            uint64_t i0 = i;
            uint64_t i1 = i | target_mask;
            
            Complex64 a0 = qsv->amplitudes[i0];
            Complex64 a1 = qsv->amplitudes[i1];
            
            qsv->amplitudes[i0].real = (a0.real + a1.real) * inv_sqrt2;
            qsv->amplitudes[i0].imag = (a0.imag + a1.imag) * inv_sqrt2;
            
            qsv->amplitudes[i1].real = (a0.real - a1.real) * inv_sqrt2;
            qsv->amplitudes[i1].imag = (a0.imag - a1.imag) * inv_sqrt2;
        }
    }
}

// Porta Pauli-X: X = [[0, 1], [1, 0]]
void qhal_apply_pauli_x(QuantumStateVector* qsv, uint32_t target_qubit) {
    if (!qsv || target_qubit >= qsv->num_qubits) return;
    
    uint64_t target_mask = 1ULL << target_qubit;
    
    for (uint64_t i = 0; i < qsv->state_dim; i++) {
        if ((i & target_mask) == 0) {
            uint64_t i0 = i;
            uint64_t i1 = i | target_mask;
            
            Complex64 temp = qsv->amplitudes[i0];
            qsv->amplitudes[i0] = qsv->amplitudes[i1];
            qsv->amplitudes[i1] = temp;
        }
    }
}

// Porta CNOT: Inverte o target se o control for 1
void qhal_apply_cnot(QuantumStateVector* qsv, uint32_t control_qubit, uint32_t target_qubit) {
    if (!qsv || control_qubit >= qsv->num_qubits || target_qubit >= qsv->num_qubits) return;
    if (control_qubit == target_qubit) return;
    
    uint64_t ctrl_mask = 1ULL << control_qubit;
    uint64_t target_mask = 1ULL << target_qubit;
    
    for (uint64_t i = 0; i < qsv->state_dim; i++) {
        if ((i & ctrl_mask) != 0 && (i & target_mask) == 0) {
            uint64_t i0 = i;
            uint64_t i1 = i | target_mask;
            
            Complex64 temp = qsv->amplitudes[i0];
            qsv->amplitudes[i0] = qsv->amplitudes[i1];
            qsv->amplitudes[i1] = temp;
        }
    }
}

// Medição e Colapso da Função de Onda (Postulado de Born)
uint8_t qhal_measure_qubit(QuantumStateVector* qsv, uint32_t target_qubit, double random_sample) {
    if (!qsv || target_qubit >= qsv->num_qubits) return 0;
    
    uint64_t target_mask = 1ULL << target_qubit;
    double prob_zero = 0.0;
    
    for (uint64_t i = 0; i < qsv->state_dim; i++) {
        if ((i & target_mask) == 0) {
            prob_zero += complex_norm_sq(qsv->amplitudes[i]);
        }
    }
    
    uint8_t outcome = (random_sample < prob_zero) ? 0 : 1;
    double norm_factor = outcome == 0 ? 1.0 / sqrt(prob_zero) : 1.0 / sqrt(1.0 - prob_zero);
    
    // Colapsa o estado e normaliza
    for (uint64_t i = 0; i < qsv->state_dim; i++) {
        bool has_target = (i & target_mask) != 0;
        if ((outcome == 0 && has_target) || (outcome == 1 && !has_target)) {
            qsv->amplitudes[i].real = 0.0;
            qsv->amplitudes[i].imag = 0.0;
        } else {
            qsv->amplitudes[i].real *= norm_factor;
            qsv->amplitudes[i].imag *= norm_factor;
        }
    }
    
    return outcome;
}
