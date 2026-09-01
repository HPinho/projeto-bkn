// Fixture: Grafo de Posse SRG em Sotlas
// Demonstra: sole, co-owned, island, whisper, handover, quarantine
module srg::graph_demo;

// Estrutura com posse exclusiva (sole)
struct Node {
    var value: Int64;
    var next: sole Node?;      // sole: cada nó é dono do próximo — lista encadeada zero-overhead
}

// Estrutura com posse compartilhada via grafo de escopo
struct SharedBuffer {
    var data: co-owned [UInt8; 1024];
    var len: UInt32;
}

// Função que recebe posse sole e a transfere de volta
pub fn create_node(val: Int64) -> sole Node {
    let node: sole Node = val as sole Node;
    // 'handover' transfere a posse para o chamador sem destruir
    handover node;
}

// Função que lê via referência fraca (sem afetar contagem)
pub fn peek_value(node: whisper Node) -> Int64 {
    return node.value;
}

// Função que demonstra isolamento island
pub fn process_isolated(buf: island SharedBuffer) -> UInt32 {
    // buf é totalmente isolado — nenhum outro contexto pode acessá-lo
    let result: UInt32 = 0;
    // quarantine isola explicitamente e garante que buf entra em região protegida
    quarantine buf;
    return result;
}

// Função que demonstra co-owned em grafo de escopo
pub fn share_buffer() -> co-owned SharedBuffer {
    // Retorno de referência co-owned (sem literais de struct no MVP)
    return nil as co-owned SharedBuffer;
}

// Spec (protocolo/interface) para tipos com posse gerenciada
spec Owned {
    fn drop() -> Void;
    fn clone() -> sole Self;
}

// Struct que adota o protocolo Owned
struct ManagedBuffer adopts Owned {
    var data: sole [UInt8; 512];
    var capacity: UInt32;

    fn drop() -> Void {
        // destruição determinística do buffer sole
        return;
    }

    fn clone() -> sole ManagedBuffer {
        let copy: sole ManagedBuffer = capacity as sole ManagedBuffer;
        handover copy;
    }
}
