# Especificação da Linguagem Sotlas

Este documento descreve a linguagem de programação Sotlas, projetada para desenvolvimento de sistemas operacionais e software de baixo nível, com foco em segurança, desempenho e expressividade.

## 1. Visão Geral

Sotlas é uma linguagem de tipagem estática com sintaxe inspirada em Rust e C, projetada para compilar para C11 estrito via seu compilador bootstrap. Ela fornece abstrações de baixo custo para programação de sistemas, mantendo controle preciso sobre recursos de hardware e memória.

## 2. Léxico

### 2.1 Comentários
- Comentário de linha: `//` até o final da linha
- Comentário de bloco: `/* ... */` (pode ser aninhado)

### 2.2 Tokens
Sotlas reconhece os seguintes tipos de tokens:

#### Palavras-chave
```
module import pub struct enum fn let mut return if else while
unsafe const static as null true false defer match loop break continue
```

#### Literais
- Inteiros: `42`, `0xFF`, `0b1010`
- Flutuantes: `3.14`, `1.0e-10`
- Caracteres: `'a'`, `'\n'`, `'\u{1F600}'`
- Strings: `"hello world"`, `r"raw string"`
- Booleanos: `true`, `false`
- Nulo: `null`

#### Operadores e Símbolos
- Aritméticos: `+ - * / %`
- Lógicos: `! && ||`
- Comparação: `== != < > <= <=`
- Bitwise: `& | ^ ~ << >>`
- Atribuição: `= += -= *= /= %= &= |= ^= <<= >>=`
- Ponteiro/Referência: `* &`
- Campo/Método: `. ::`
- Outros: `, ; : ? -> => { } ( ) [ ]`

#### Identificadores
Começam com letra ou underscore, seguidos por letras, dígitos ou underscores.
São case-sensitive.

## 3. Tipos

### 3.1 Tipos Primitivos
- Inteiros com sinal: `i8`, `i16`, `i32`, `i64`, `isize`
- Inteiros sem sinal: `u8`, `u16`, `u32`, `u64`, `usize`
- Ponto flutuante: `f32`, `f64`
- Booleano: `bool`
- Vazio: `void`
- Nulo: Representado pelo valor nulo de ponteiros

### 3.2 Tipos Compostos
- Tuplas: `(T1, T2, ...)`
- Arrays fixos: `[T; N]`
- Slices: `&[T]`, `&mut [T]`
- Estruturas: `struct Nome { campo: Tipo, ... }`
- Enumerações: `enum Nome { Variante1(Tipo), Variante2, ... }`
- Ponteiros: `*const T`, `*mut T`
- Referências: `&T`, `&mut T`
- Funções: `fn(Tipo1, Tipo2) -> TipoRetorno`

### 3.3 Tipos Compostos da Biblioteca Padrão
- `Option<T>`: `Some(T)` ou `None`
- `Result<T, E>`: `Ok(T)` ou `Err(E)`
- `String`: String UTF-8 heap-allocated
- `&str`: Slice de string UTF-8

## 4. Variáveis e Bindings

### 4.1 Declaração de Variáveis
```st
let nome: Tipo = expressão;    // Tipo explícito
let mut nome: Tipo = expressão; // Mutável
let nome = expressão;           // Inferência de tipo
```

### 4.2 Padrões de Binding
- `let x = expr;`           // Binding simples
- `let (x, y) = expr;`      // Desestruturação de tupla
- `let [x, y, ..] = expr;`  // Desestruturação de slice/array
- `let estrut {campo: x} = expr;` // Desestruturação de struct
- `let enum::Var(x) = expr;`    // Desestruturação de enum

### 4.3 Escopo e Vida
Variáveis seguem regras de escopo léxico.
O tempo de vida é determinado pelo escopo onde são declaradas.
Variáveis são descartadas automaticamente ao sair do escopo (similar a RAII).

## 5. Expressões

### 5.1 Expressões Primárias
- Literais: `42`, `"texto"`
- Variáveis: `x`
- Chamadas de função: `func(arg1, arg2)`
- Acesso a campo: `struct.campo`
- Indexação: `array[indice]`, `slice[indice]`
- Desreferenciamento: `*ponteiro`
- Referência: `&variavel`, `&mut variavel`
- Agrupamento: `(expressão)`

### 5.2 Expressões Pós-fixadas
- Chamada de método: `obj.metodo(arg)`
- Acesso a campo mutável: `obj.mut_campo`
- Conversão: `expressão as Tipo`

### 5.3 Expressões Unárias
- Negação: `-expr`, `!expr`
- Dereferenciação: `*expr`
- Referência: `&expr`, `&mut expr`

### 5.4 Expressões Binárias
Operadores com precedência e associatividade padrão (similar a C/Rust).

### 5.5 Expressões de Controle como Expressões
Blocos `if`, `match` e `loop` podem produzir valores:
```st
let x = if cond { 1 } else { 2 };
let y = match valor {
    Ok(v) => v * 2,
    Err(e) => handle_error(e)
};
```

## 6. Declarações (Statements)

### 6.1 Declaração de Let
Já descrita na seção 4.

### 6.2 Expressões como Statements
Qualquer expressão pode ser usada como statement (seu valor é descartado).

### 6.3 Estruturas de Controle

#### If-Else
```st
if condição {
    // then branch
} else if outra_condição {
    // else if branch
} else {
    // else branch
}
```

#### Loop
```st
loop {
    // corpo repetido até break
    if cond { break; }
}
```

#### While
```st
while condição {
    // corpo executado enquanto condição true
}
```

#### Match
```st
match valor {
    Padrão1 => expressão1,
    Padrão2 => expressão2,
    _ => expressão_padrão // curinga
}
```

### 6.4 Controle de Fluxo
- `break`: Sai do loop mais interno
- `continue`: Pula para a próxima iteração do loop mais interno
- `return`: Sai da função atual, retornando um valor opcional
- `defer`: Agenda execução para saída do escopo atual

## 7. Funções

### 7.1 Sintaxe
```st
fn nome(param1: Tipo1, param2: Tipo2) -> TipoRetorno {
    // corpo da função
}
```

Funções sem retorno explícito retornam `()`.

### 7.2 Parâmetros
- Por valor: `param: Tipo`
- Por referência: `param: &Tipo` ou `param: &mut Tipo`
- Padrão: Todos os parâmetros são imutáveis por default; use `mut` para tornar mutável dentro da função

### 7.3 Visibilidade
- `pub`: Função visível fora do módulo
- Sem `pub`: Função privada ao módulo

### 7.4 Atributos de Função
- `@system`: Indica que a função pode ser chamada em contexto de sistema (kernel, interrupções)
- `@export`: Torna a função visível para linkagem externa (C linker)
- `@inline`: Sugere inlining da chamada
- `@naked`: Função sem prólogo/epílogo padrão (para assembly inserto)

## 8. Módulos

### 8.1 Declaração
```st
mod nome_do_modulo {
    // conteúdo do módulo
}
```

### 8.2 Estrutura de Arquivos
Cada módulo normalmente reside em seu próprio arquivo:
- `nome_do_modulo.sotlas` contém `mod nome_do_modulo { ... }`
- Ou o arquivo pode ser apenas o conteúdo, com o módulo definido pelo caminho

### 8.3 Importação
```st
import nome_do_modulo;           // Importa módulo inteiro
import nome_do_modulo::item;     // Importa item específico
import nome_do_modulo::{item1, item2}; // Importa múltiplos itens
import nome_do_modulo::*;        // Importa todos os itens públicos
```

### 8.4 Visibilidade
- `pub`: Item visível fora do módulo
- Sem `pub`: Item privado ao módulo
- `pub(crate)`: Visível dentro do crate (Pacote)
- `pub(super)`: Visível no módulo pai
- `pub(in caminho::de::modulo)`: Visível em módulo específico

## 9. Estruturas e Enumerações

### 9.1 Estruturas
```st
struct Ponto {
    x: i32,
    y: i32
}

struct Retangulo {
    superior_esquerdo: Ponto,
    inferior_direito: Ponto
}

// Métodos
impl Retangulo {
    fn area(&self) -> u32 {
        let largura = (self.inferior_direito.x - self.superior_esquerdo.x) as u32;
        let altura = (self.inferior_direito.y - self.superior_esquerdo.y) as u32;
        largura * altura
    }
    
    fn contenir(&self, ponto: &Ponto) -> bool {
        ponto.x >= self.superior_esquerdo.x &&
        ponto.x <= self.inferior_direito.x &&
        ponto.y >= self.superior_esquerdo.y &&
        ponto.y <= self.inferior_direito.y
    }
}
```

### 9.2 Enumerações
```st
enum Resultado<T, E> {
    Ok(T),
    Err(E)
}

enum Cor {
    Vermelho,
    Verde,
    Azul,
    RGB(u8, u8, u8),
    HSV(u8, u8, u8)
}

// Métodos em enums
impl Cor {
    fn eh_primaria(&self) -> bool {
        match self {
            Cor::Vermelho | Cor::Verde | Cor::Azul => true,
            _ => false
        }
    }
}
```

## 10. Sistema de Tipos Avançado

### 10.1 Genéricos
```st
struct Ponte<T> {
    dados: T
}

impl<T> Ponte<T> {
    fn novo(dados: T) -> Ponte<T> {
        Ponte { dados }
    }
    
    fn obter(&self) -> &T {
        &self.dados
    }
}

// Associação de tipos para métodos específicos
impl Ponte<String> {
    fn comprimento(&self) -> usize {
        self.dados.len()
    }
}
```

### 10.2 Traits (Interfaces)
```st
trait Drawable {
    fn desenhar(&self);
    fn limites(&self) -> Rect;
}

struct Circulo {
    centro: Ponto,
    raio: u32,
    cor: u32
}

impl Drawable for Circulo {
    fn desenhar(&self) {
        // implementação de desenho de círculo
    }
    
    fn limites(&self) -> Rect {
        // calcular limites do círculo
    }
}

// Uso genérico com trait bound
fn renderizar<T: Drawable>(item: &T) {
    item.desenhar();
}
```

### 10.3 Tipos Associados
```st
trait Container {
    type Item;
    fn inserir(&mut self, item: Self::Item);
    fn obter(&self) -> Option<&Self::Item>;
}

impl<T> Container for Ponte<T> {
    type Item = T;
    
    fn inserir(&mut self, item: Self::Item) {
        self.dados = item;
    }
    
    fn obter(&self) -> Option<&Self::Item> {
        Some(&self.dados)
    }
}
```

## 11. Gerenciamento de Memória e Operador Defer

### 11.1 Modelo de Memória
Sotlas segue um modelo de ownership similar ao Rust:
- Cada valor tem um único dono
- Quando o dono sai do escopo, o valor é descartado
- Referências (&T e &mut T) não transferem ownership
- Referências mutáveis têm exclusividade (&mut T implica que não há outras referências ativas ao mesmo dado)

### 11.2 Operador Defer
O operador `defer` agenda a execução de uma expressão ou bloco para quando o escopo atual for encerrado.

#### Sintaxe Básica
```st
defer expressão;
// ou
defer {
    // múltiplas statements
}
```

#### Semântica
1. **Ordem LIFO**: Múltiplos defer no mesmo escopo são executados na ordem inversa à declaração
2. **Escopo Aninhado**: Defers de escopos internos são executados antes dos escopos externos
3. **Saída por return/break/continue**: Todos os defers ativos são executados antes do salto/retorno
4. **Avaliação na Saída**: A expressão/bloco é executada exatamente na fronteira de saída do escopo
5. **Tratamento de Erros**: Se um defer gerar um panic, ele é propagado normalmente (mesma que qualquer expressão)

#### Exemplos
```st
fn processar_arquivo(caminho: *const u8) -> Result<i32, ErrorCode> {
    let arquivo = abrir_arquivo(caminho)?;
    defer fechar_arquivo(arquivo); // Garante fechamento mesmo se houver erro
    
    let dados = ler_dados(arquivo)?;
    defer liberar_buffer(dados);   // Libera buffer antes de retornar
    
    processar(dados)
}

fn exemplo_loop() {
    let mut contador = 0;
    loop {
        defer println!("Iteração {}", contador); // Executado a cada iteração
        if contador >= 5 { break; }
        contador += 1;
    }
    // Defer NÃO é executado aqui porque o break pula para fora do loop
}

fn exemplo_panic() {
    defer println!("Isso será executado mesmo após panic");
    panic!("Erro intencional"); // Defer executado antes de propagar panic
}
```

#### Defer com Tratamento de Erros (similar a named returns em Go)
```st
fn funcao_com_erro(res: *mut u32) -> Result<(), ErrorCode> {
    defer {
        if let Some(e) = ultimo_erro() {
            // Manipular erro registrado durante a função
            registrar_erro(e)
        }
    }
    
    // corpo da função...
    Ok(())
}
```

### 11.3 Alocação e Desalocação
- Alocação na stack: Variáveis locais
- Alocação na heap: `box` expression (futuro) ou funções de allocator explícitas
- Desalocação automática: Via drop/gc quando ownership sai do escopo
- Desalocação manual: Funções como `free`, `dealloc` para interoperação com C

## 12. Atributos

Sotlas usa atributos anotados com `@` para modificar declarações.

### 12.1 Atributos de Função
- `@system`: Função pode ser chamada em contexto privilegiado (kernel, ISR)
- `@export`: Símbolo visível para linkagem externa
- `@inline`: Dica para o compilador tentar inlining
- `@naked`: Função sem prólogo/epílogo padrão
- `@no_mangle`: Preserva nome exato no símbolo (evita name mangling)
- `@interrupt`: Função é um handler de interrupção

### 12.2 Atributos de Tipo
- `@packed`: Layout sem padding (para estruturas de dados de hardware)
- `@align(N)`: Alinhamento específico em bytes
- `@repr(C)`: Layout compatível com C
- `@repr(packed)`: Mesmo que `@packed`

### 12.3 Atributos de Variável
- `@static`: Duração de vida estática (mesmo que `static`)
- `@thread_local`: Armazenamento local à thread
- `@volatile`: Acesso não otimizado (para registradores de hardware)

### 12.4 Atributos de Impl/Block
- `@target("arch")`: Código específico para arquitetura
- `@cfg(condition):` Compilação condicional (similar a #[cfg] em Rust)

## 13. Expressões Constantes e Tempo de Compilação

### 13.1 Avaliação em Tempo de Compilação
Algumas expressões podem ser avaliadas em tempo de compilação:
- Operações aritméticas em constantes
- Funções marcadas como `const`
- Manipulação de tipos e traits

### 13.2 Funções Const
```st
const fn tamanho_de_pagina() -> usize {
    4096
}

const MAX_BUFFER: usize = tamanho_de_pagina() * 4;
```

### 13.3 Block Const
```st
const {
    let TABELA_CRC: [u32; 256] = gerar_tabela_crc();
    // TABELA_CRC disponível em tempo de compilação
}
```

## 14. Inserção de Assembly (Inline Assembly)

Para acesso direto a hardware ou instruções específicas:
```st
unsafe {
    asm!("cli" :::: "volatile"); // Limpar interrupções (x86)
    asm!("mov {0}, cr3" : "=r"(reg) ::: "volatile"); // Ler registrador
}
```

## 15. Interoperação com C

### 15.1 Chamando Funções C
```st
extern "C" {
    fn malloc(size: size_t) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn printf(fmt: *const c_char, ...) -> c_int;
}
```

### 15.2 Estruturas Compatíveis com C
```st
#[repr(C)]
struct Ponto2D {
    x: f32,
    y: f32
}

// Pode ser passada diretamente para funções C que esperam struct Ponto2D { float x, float y; }
```

### 15.3 Callbacks para C
Funções marcadas com `@export` podem ser passadas como ponteiros de função para C.

## 16. Segurança e Blocos Unsafe

### 16.1 Blocos Unsafe
Operações que o compilador não pode verificar de forma segura devem estar dentro de blocos `unsafe`:
```st
unsafe {
    let ptr: *mut u32 = 0x1000 as *mut u32;
    *ptr = 42; // Escritura direta em memória
}
```

Operações que requerem `unsafe`:
- Desreferenciação de ponteiros raw (`*const T`, `*mut T`)
- Chamada de funções `unsafe` ou extern
- Implementação de traits unsafe
- Acesso a campos de union
- Inserção de assembly inline

### 16.2 Abstrações Seguras
Sotlas incentiva o uso de abstrações seguras em vez de `unsafe` quando possível:
- Referências (`&T`, `&mut T`) em vez de ponteiros raw
- Containers da biblioteca padrão (`Vec<T>`, `String`) em vez de gerenciamento manual de memória
- Traits para encapsular operações perigosas

## 17. Biblioteca Padrão

A biblioteca padrão Sotlas fornece:

### 17.1 Módulo Core
- Tipos básicos: `Option<T>`, `Result<T,E>`
- Funções de memória: `memcpy`, `memset`, `memmove`
- Funções de string: versões seguras de operações em C-strings

### 17.2 Módulo Alloc
- Alocadores de memória: allocators de heap
- Tipos de alocação: `Box<T>`, `Vec<T>`, `String`

### 17.3 Módulo Coleções
- Estruturas de dados: listas ligadas, hash maps, árvores
- Iteradores e adapters

### 17.4 Módulo IO
- Operações de entrada/saída bufferizadas
- Trabalhando com arquivos, sockets, consoles

### 17.5 Módulo Sync
- Primitivos de sincronização: mutexes, semáforos, canais
- Tipos atomicos para programação concorrente

## 18. Comentários e Documentação

### 18.1 Comentários de Documentação
```st
/// Isso é um comentário de documentação para o item que segue
/// 
/// # Exemplos
/// 
/// ```st
/// let x = 5;
/// /// ```
pub fn minha_função() {
    // ...
}
```

### 18.2 Comentários de Linha e Bloco
Como descrito na seção 2.1.

## 19. gramática Formal (EBNF Simplificado)

```
programa := item*;
item := módulo | import | fn | struct | enum | const | static | trait | impl;
módulo := "mod" identificador "{" item* "}";
import := "import" caminho ( "::" identificador | "::" "*" )?;
fn := "fn" identificador "(" parâmetro* ")" "->" tipo? bloco;
parâmetro := "mut"? identificador ":" tipo;
struct := "struct" identificador "{" campo* "}";
campo := "mut"? identificador ":" tipo;
enum := "enum" identificador "{" variante* "}";
variante := identificador ( "(" tipo* ")" )?;
const := "const" identificador ":" tipo "=" expressão ";";
static := "static" identificador ":" tipo "=" expressão ";";
trait := "trait" identificador "{*" assinatura_método* "}";
impl := "impl" tipo? "{" método* "}";
bloco := "{" statement* "}";
statement := 
    | let_decl
    | expressão ";"
    | if_statement
    | loop_statement
    | while_statement
    | match_statement
    | break ";"
    | continue ";"
    | return expressão? ";"
    | defer expressão ";"
    | defer bloco
    | unsafe bloco
let_decl := "let" "mut"? identificador ( ":" tipo )? ( "=" expressão )? ";";
if_statement := "if" expressão bloco ( "else if" expressão bloco )* ( "else" bloco )?;
loop_statement := "loop" bloco;
while_statement := "while" expressão bloco;
match_statement := "match" expressão "{" ramo* "}";
ramo := padrão "=>" expressão ","?;
expressão := literal | identificador | chamada | campo | index | unário | binário | grupo;
```

## 20. Compatibilidade e Versionamento

Sotlas segue versionamento semântico:
- Versões mayores (X.0.0): Podem quebrar compatibilidade
- Versões menores (0.X.0): Adicionam funcionalidades mantendo compatibilidade
- Versões de patch (0.0.X): Correções de bugs e melhorias menores

### 20.1 Escrita de Código Portável
- Use apenas funcionalidades estáveis da especificação
- Evite recursos marcados como experimentais
- Teste em múltiplas arquiteturas alvo quando possível

## 21. Conclusão

Esta especificação define a linguagem Sotlas como uma ferramenta poderosa para desenvolvimento de sistemas, combinando o controle baixo nível de C com as abstrações de segurança e expressividade de linguagens modernas como Rust.

A implementação bootstrap atual fornece um sólido fundamento, e esta especific Trilha o caminho para uma linguagem completa e madura adequada para construir sistemas operacionais, drivers, embarcados e outros softwares de sistemas críticos.

Para questões específicas sobre implementação ou extensões, consulte a documentação do compilador bootstrap e os exemplos no repositório.