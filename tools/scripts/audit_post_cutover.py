"""Conservative direct-call audit of the post-ExitBootServices roots.

Not a whole-program indirect-call proof: report opaque calls for review.
The entry trampoline and CPU ISR stubs are the reviewed external boundary.
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.sotlas_compile.compiler import parse_module_ast

ROOTS = ('sotlas_x86_post_cutover_entry', 'sotlas_x86_irq_dispatch')
FORBIDDEN = re.compile(r'\b(?:baken_efi_\w*|uefi_\w*|Efi\w*|BootServices|RuntimeServices|Stall|LocateProtocol|ReadBlocks|WriteBlocks|baken_runtime_run)\b')
SAFE_DATA_SYMBOLS = {'EfiMemoryDescriptor'}
CALL = re.compile(r'(?<![\w.])([A-Za-z_]\w*)\s*\(')
KEYWORDS = {'if', 'while', 'for', 'loop', 'unsafe', 'sizeof', 'return', 'match'}


def audit(root=ROOT):
    functions = {}
    for path in (root / 'kernel/src').rglob('*.sotlas'):
        ast = parse_module_ast(path.read_text(encoding='utf-8'))
        for fn in ast.functions:
            functions.setdefault(fn.name, []).append((path, fn.body))
    pending = list(ROOTS)
    seen, opaque, violations = set(), set(), []
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        if name not in functions:
            opaque.add(name)
            continue
        for path, body in functions[name]:
            body = re.sub(r'//[^\n]*|/\*.*?\*/', '', body, flags=re.S)
            body = re.sub(r'"(?:\\.|[^"\\])*"', '""', body)
            for match in FORBIDDEN.finditer(body):
                # EfiMemoryDescriptor is a copied boot-map POD record, not a
                # callable firmware interface. Keep the broad Efi* guardrail
                # for every other symbol so post-cutover service reentry still fails.
                if match[0] in SAFE_DATA_SYMBOLS:
                    continue
                violations.append(f'{path.relative_to(root)}:{name}: {match[0]}')
            pending.extend(set(CALL.findall(body)) - KEYWORDS)
    return {'roots': list(ROOTS), 'reachable_functions': len(seen - opaque),
            'opaque_calls': sorted(opaque), 'firmware_violations': violations}


if __name__ == '__main__':
    report = audit()
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report['firmware_violations']))
