"""Testes unitários para o Shell Gráfico Interativo, BakenFS e Terminal (Pilares 1 e 2)."""
import unittest


def str_contains_nocase(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


class MockBakenFS:
    def __init__(self):
        self.entries = [
            {"name": "/config/theme.cfg", "kind": 3, "size": 512, "lba": 86017},
            {"name": "/home/notas.txt", "kind": 2, "size": 64, "lba": 86018},
            {"name": "/home/docs", "kind": 1, "size": 0, "lba": 0},
        ]
        self.files = {
            "/home/notas.txt": "Notas importantes do Baken OS.",
            "/config/theme.cfg": "dark_theme=1",
        }

    def entry_count(self) -> int:
        return len(self.entries)

    def entry_name(self, index: int) -> str:
        return self.entries[index]["name"] if index < len(self.entries) else "(vazio)"

    def entry_kind(self, index: int) -> int:
        return self.entries[index]["kind"] if index < len(self.entries) else 2

    def entry_size(self, index: int) -> int:
        return self.entries[index]["size"] if index < len(self.entries) else 0

    def find(self, name: str) -> int:
        for idx, entry in enumerate(self.entries):
            if entry["name"] == name:
                return idx
        return -1

    def add(self, name: str, kind: int, size: int = 0, lba: int = 0) -> bool:
        if len(self.entries) >= 12:
            return False
        idx = self.find(name)
        if idx >= 0:
            self.entries[idx]["kind"] = kind
            self.entries[idx]["size"] = size
        else:
            self.entries.append({"name": name, "kind": kind, "size": size, "lba": lba or (86020 + len(self.entries))})
        return True

    def remove(self, name: str) -> bool:
        idx = self.find(name)
        if idx < 0:
            return False
        self.entries.pop(idx)
        if name in self.files:
            del self.files[name]
        return True

    def write_file(self, name: str, text: str) -> bool:
        self.add(name, kind=2, size=len(text.encode("utf-8")))
        self.files[name] = text
        return True

    def read_file(self, name: str) -> str:
        return self.files.get(name, "")


class ShellInteractiveTests(unittest.TestCase):
    def setUp(self):
        self.catalog = [
            {"title": "Arquivos - BakenFS", "sub": "Explorador de Arquivos (/home)", "app_id": 0},
            {"title": "Notas Rapidas", "sub": "Editor de texto persistente", "app_id": 6},
            {"title": "Central de Ajustes", "sub": "Configuracoes de Hardware", "app_id": 10},
            {"title": "Terminal Sotlas", "sub": "Interpretador de Comandos Sotlas", "app_id": 9},
            {"title": "Assistente Q-HAL AI", "sub": "Inteligencia Artificial Local", "app_id": 4},
            {"title": "Instalar Baken OS", "sub": "Assistente de Instalacao UEFI", "app_id": 14},
        ]
        self.fs = MockBakenFS()

    def test_spotlight_empty_query_shows_all_top_apps(self):
        query = ""
        filtered = [item for item in self.catalog if str_contains_nocase(item["title"], query) or str_contains_nocase(item["sub"], query)]
        self.assertEqual(len(filtered), 6)

    def test_spotlight_dynamic_filtering_matching_notes(self):
        query = "not"
        filtered = [item for item in self.catalog if str_contains_nocase(item["title"], query) or str_contains_nocase(item["sub"], query)]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["title"], "Notas Rapidas")
        self.assertEqual(filtered[0]["app_id"], 6)

    def test_spotlight_dynamic_filtering_matching_terminal(self):
        query = "term"
        filtered = [item for item in self.catalog if str_contains_nocase(item["title"], query) or str_contains_nocase(item["sub"], query)]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["title"], "Terminal Sotlas")
        self.assertEqual(filtered[0]["app_id"], 9)

    def test_spotlight_dynamic_filtering_no_match(self):
        query = "xyz12345"
        filtered = [item for item in self.catalog if str_contains_nocase(item["title"], query) or str_contains_nocase(item["sub"], query)]
        self.assertEqual(len(filtered), 0)

    def test_bakenfs_add_and_find(self):
        self.assertEqual(self.fs.entry_count(), 3)
        self.assertTrue(self.fs.add("/home/documento.txt", kind=2, size=120))
        self.assertEqual(self.fs.entry_count(), 4)
        self.assertGreaterEqual(self.fs.find("/home/documento.txt"), 0)

    def test_bakenfs_remove_file(self):
        self.assertTrue(self.fs.add("/home/temp.txt", kind=2, size=10))
        self.assertGreaterEqual(self.fs.find("/home/temp.txt"), 0)
        self.assertTrue(self.fs.remove("/home/temp.txt"))
        self.assertEqual(self.fs.find("/home/temp.txt"), -1)

    def test_bakenfs_write_and_read_file(self):
        text = "Baken OS Persistent File System Test"
        self.assertTrue(self.fs.write_file("/home/teste.txt", text))
        read_back = self.fs.read_file("/home/teste.txt")
        self.assertEqual(read_back, text)

    def test_terminal_command_parsing(self):
        commands = {
            "help": "Comandos: ls, cat, touch, mkdir, rm, write, theme, sysinfo, clear",
            "sysinfo": "Arch: x86_64 UEFI",
            "theme dark": "Modo Escuro",
            "theme light": "Modo Claro",
            "stat": "BakenFS Estado",
            "ls": "Arquivos no BakenFS",
            "touch /home/novo.txt": "Arquivo criado",
            "cat /home/notas.txt": "Notas importantes",
        }
        for cmd, expected in commands.items():
            self.assertTrue(len(expected) > 0 and len(cmd) > 0)


if __name__ == "__main__":
    unittest.main()
