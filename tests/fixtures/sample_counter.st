// Fixture: Contador simples em Sotlas (equivalente ao cq01_sample.cq)
module core::counter;

pub struct Counter {
    var value: Int64;
}

pub fn sum(limit: Int64) -> Int64 {
    let total: Int64 = 0;
    let i: Int64 = 0;
    while i < limit {
        total = total + i;
        i = i + 1;
    }
    if total > 0 {
        return total;
    } else {
        return 0;
    }
}
