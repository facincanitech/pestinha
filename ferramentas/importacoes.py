"""
Lista os módulos que o código importa (para o PyInstaller pôr dentro do lançador).

O lançador roda o código baixado como arquivos .py soltos; o que ele importar (PySide6, numpy, win32...)
precisa estar dentro do .exe. Uso: python ferramentas/importacoes.py  ->  imprime --hidden-import ...
"""
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTRAS = ["win32timezone", "PySide6.QtSvg", "PySide6.QtNetwork", "sqlite3", "csv", "hashlib", "uuid",
          "urllib.request", "urllib.error", "threading", "dataclasses", "datetime", "colorsys", "statistics"]


def modulos():
    achados = set()
    for arquivo in list((RAIZ / "pestinha").rglob("*.py")) + [RAIZ / "main.py"]:
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            if isinstance(no, ast.Import):
                achados.update(a.name for a in no.names)
            elif isinstance(no, ast.ImportFrom) and not no.level and no.module:
                achados.add(no.module)
                achados.update(f"{no.module}.{a.name}" for a in no.names if no.module == "PySide6")
    return sorted(m for m in achados | set(EXTRAS) if not m.startswith("pestinha"))


if __name__ == "__main__":
    print(" ".join(f"--hidden-import {m}" for m in modulos()))
    sys.exit(0)
