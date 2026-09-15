"""Guardrails para checkpoints em RAM que não dependem de UART legado."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "scheduler_diagnostics": ROOT / "kernel/src/scheduler/diagnostics.sotlas",
    "sleep": ROOT / "kernel/src/scheduler/sleep.sotlas",
    "wait_queue": ROOT / "kernel/src/scheduler/wait_queue.sotlas",
    "wait_queue_probe": ROOT / "kernel/src/scheduler/wait_queue_probe.sotlas",
}


class RamDiagnosticsWithoutUartTests(unittest.TestCase):
    def test_scheduler_ram_markers_do_not_precheck_uart_transport(self):
        for name, path in SOURCES.items():
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "x86_serial_is_ready()",
                text,
                f"{name} voltou a condicionar o checkpoint em RAM à presença de UART",
            )

    def test_scheduler_markers_still_use_common_diagnostic_sink(self):
        for name, path in SOURCES.items():
            text = path.read_text(encoding="utf-8")
            self.assertTrue(
                "x86_serial_write_byte" in text or "x86_serial_write_buffer" in text,
                f"{name} não usa mais o sink diagnóstico comum",
            )


if __name__ == "__main__":
    unittest.main()
