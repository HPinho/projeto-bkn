/*
 * Baken Ecosystem - Suíte de Verificação do Simulador Quântico Q-HAL
 * Testa a criação do Estado de Bell e correlação de entrelaçamento quântico.
 */

#include "../kernel/qhal/quantum_simulator.h"
#include <stdio.h>
#include <assert.h>
#include <math.h>

void test_hadamard_superposition() {
    printf("[TESTE 1] Inicializando Registrador de 1 Qubit...\n");
    QuantumStateVector* qsv = qhal_create_state_vector(1);
    assert(qsv != NULL);
    assert(qsv->state_dim == 2);
    
    // Estado inicial: |0> (amplitude 1.0 no índice 0)
    assert(fabs(qsv->amplitudes[0].real - 1.0) < 1e-6);
    assert(fabs(qsv->amplitudes[1].real - 0.0) < 1e-6);
    
    printf("[TESTE 1] Aplicando Porta Hadamard H(q[0])...\n");
    qhal_apply_hadamard(qsv, 0);
    
    // Estado resultante: (|0> + |1>) / sqrt(2)
    double expected = 1.0 / sqrt(2.0);
    assert(fabs(qsv->amplitudes[0].real - expected) < 1e-6);
    assert(fabs(qsv->amplitudes[1].real - expected) < 1e-6);
    printf("  -> Sucesso: Amplitudes de superposicao balanceadas (|alpha|^2 = 0.5, |beta|^2 = 0.5)\n");
    
    qhal_free_state_vector(qsv);
}

void test_bell_state_entanglement() {
    printf("[TESTE 2] Criando Par de Bell Entrelaçado (|00> + |11>)/sqrt(2)...\n");
    QuantumStateVector* qsv = qhal_create_state_vector(2);
    assert(qsv != NULL);
    assert(qsv->state_dim == 4);
    
    // 1. Aplica H no Qubit 0
    qhal_apply_hadamard(qsv, 0);
    // 2. Aplica CNOT com controle em 0 e alvo em 1
    qhal_apply_cnot(qsv, 0, 1);
    
    double expected = 1.0 / sqrt(2.0);
    // |00> (índice 0) e |11> (índice 3) devem ter amplitude 1/sqrt(2)
    // |01> (índice 1) e |10> (índice 2) devem ter amplitude 0.0
    assert(fabs(qsv->amplitudes[0].real - expected) < 1e-6);
    assert(fabs(qsv->amplitudes[1].real - 0.0) < 1e-6);
    assert(fabs(qsv->amplitudes[2].real - 0.0) < 1e-6);
    assert(fabs(qsv->amplitudes[3].real - expected) < 1e-6);
    
    printf("  -> Sucesso: Estado de Bell gerado com fidelidade exata (100.0%%)\n");
    
    // 3. Teste de Medição com Colapso
    printf("[TESTE 2] Simulando Medição Quântica e Colapso da Função de Onda...\n");
    uint8_t m0 = qhal_measure_qubit(qsv, 0, 0.3); // Amostra aleatória simulada < 0.5 resulta em 0
    assert(m0 == 0);
    
    // Após medir 0 no qubit 0, o qubit 1 colapsa instantaneamente para 0 (|00>)
    uint8_t m1 = qhal_measure_qubit(qsv, 1, 0.1);
    assert(m1 == 0);
    printf("  -> Sucesso: Correlacao instantanea de colapso verificada (m0=%d, m1=%d)\n", m0, m1);
    
    qhal_free_state_vector(qsv);
}

int main() {
    printf("============================================================\n");
    printf("  BAKEN OS: Executando Testes de Verificação do Q-HAL Core  \n");
    printf("============================================================\n\n");
    
    test_hadamard_superposition();
    printf("\n");
    test_bell_state_entanglement();
    
    printf("\n>>> TODOS OS TESTES QUÂNTICOS PASSARAM COM ÊXITO! <<<\n");
    return 0;
}
