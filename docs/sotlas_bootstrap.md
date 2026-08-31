# Especificação da Linguagem Sotlas Bootstrap Stage 0

O **Sotlas Bootstrap Stage 0** é o frontend procedural normativo da linguagem Cq para o Baken OS, fornecendo tipagem estática forte, gerenciamento de escopo sem overhead e compilação para C11 estrito.

---

## 1. Operador `defer`

O operador `defer` agenda a execução de uma expressão para quando o escopo léxico atual for encerrado.

### Sintaxe
```cq
defer <expression>;
```

### Semântica Normativa
1. **Ordem LIFO (Last-In, First-Out)**: Múltiplas declarações `defer` dentro do mesmo bloco são executadas na ordem inversa à sua declaração ao final do bloco.
2. **Saída por `return`**: Todos os `defer` ativos em todos os escopos aninhados da função atual são executados em ordem LIFO antes do retorno efetivo da função. Se o `return` contiver uma expressão de valor, este valor é avaliado antes dos defers serem executados.
3. **Saída por `break` ou `continue`**: Quando um `break` ou `continue` é atingido em um laço de repetição (`while`), os `defer` declarados dentro do corpo do laço (até o escopo do laço) são executados em ordem LIFO antes do salto.
4. **Avaliação na Saída**: A expressão em `defer` é executada na fronteira de saída do escopo.

### Exemplo
```cq
module core::demo;

pub fn process_resource() -> i64 {
    let mut status: i64 = 1;
    defer cleanup();
    defer status = 0;
    
    if status == 1 {
        return status; // Retorna 1, executando status = 0 e cleanup() antes da saída
    }
    return 0;
}
```
