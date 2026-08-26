/*
 * Baken Microkernel - Escalonador Híbrido Clássico-Quântico
 * Gerencia threads clássicas preemptivas e suspensões quânticas assíncronas.
 */

#include "../include/baken_kernel.h"

static BakenThread* ready_queue_head = NULL;
static BakenThread* ready_queue_tail = NULL;
static BakenThread* current_thread = NULL;
static BakenThread* quantum_wait_queue = NULL;

void baken_scheduler_init(void) {
    ready_queue_head = NULL;
    ready_queue_tail = NULL;
    current_thread = NULL;
    quantum_wait_queue = NULL;
}

void baken_scheduler_enqueue(BakenThread* thread) {
    if (!thread) return;
    
    thread->state = THREAD_STATE_READY;
    thread->next = NULL;
    
    if (ready_queue_tail == NULL) {
        ready_queue_head = thread;
        ready_queue_tail = thread;
    } else {
        ready_queue_tail->next = thread;
        ready_queue_tail = thread;
    }
}

// Suspende a thread clássica quando ela dispara uma rotina quântica longa
void baken_scheduler_suspend_for_quantum(BakenThread* thread, uint64_t job_id) {
    if (!thread) return;
    
    thread->state = THREAD_STATE_SUSPENDED_QUANTUM;
    thread->quantum_job_id = job_id;
    thread->next = quantum_wait_queue;
    quantum_wait_queue = thread;
}

// Notificação de conclusão de medição/colapso quântico vinda do Q-HAL ou QPU
void baken_scheduler_resume_quantum_job(uint64_t job_id) {
    BakenThread** curr = &quantum_wait_queue;
    
    while (*curr != NULL) {
        if ((*curr)->quantum_job_id == job_id) {
            BakenThread* ready_thread = *curr;
            *curr = ready_thread->next;
            
            baken_scheduler_enqueue(ready_thread);
            break;
        }
        curr = &((*curr)->next);
    }
}

BakenThread* baken_scheduler_schedule_next(void) {
    if (ready_queue_head == NULL) {
        return NULL; // CPU Idle
    }
    
    BakenThread* next_thread = ready_queue_head;
    ready_queue_head = ready_queue_head->next;
    if (ready_queue_head == NULL) {
        ready_queue_tail = NULL;
    }
    
    next_thread->state = THREAD_STATE_RUNNING;
    current_thread = next_thread;
    return next_thread;
}
