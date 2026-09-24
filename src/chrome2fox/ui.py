"""UI — Estilo munder/openmobile: ayuda en espanol, dashboard ASCII,
menu interactivo y logs con prefijo. Todo stdlib, sin dependencias.
El JSON de cada comando sigue saliendo limpio por stdout; lo humano va a stderr.
"""

import sys

WIDTH = 80


def log(msg: str) -> None:
    """Linea de progreso estilo `openmobile:` (a stderr, no rompe JSON)."""
    print(f"chrome2fox: {msg}", file=sys.stderr)


def box(title: str, rows: list[tuple[str, str]]) -> str:
    """Caja ASCII de 80 cols: [(etiqueta, valor)]. Valores largos se recortan."""
    top = "┌" + "─" * (WIDTH - 2) + "┐"
    sep = "├" + "─" * (WIDTH - 2) + "┤"
    bot = "└" + "─" * (WIDTH - 2) + "┘"

    def line(text: str) -> str:
        text = text[: WIDTH - 4]
        return "│ " + text.ljust(WIDTH - 4) + " │"

    out = [top, line(title), sep]
    for label, value in rows:
        if label:
            out.append(line(f"{label}:  {value}"))
        else:
            out.append(line(value))
    out.append(bot)
    return "\n".join(out)


def dash(status_ok: bool, title: str, rows: list[tuple[str, str]]) -> str:
    """Dashboard con primera fila de estado ● OK/✗."""
    dot = "● OK" if status_ok else "✗ FALLO"
    return box(title, [("status", dot), *rows])


def menu(options: list[tuple[str, str]]) -> int | None:
    """Menu numerado (1..N, 0 salir). None si no hay TTY o se aborta."""
    if not sys.stdin.isatty():
        return None
    print("▚ CHROME2FOX  (elige con numero + Enter)", file=sys.stderr)
    for i, (name, desc) in enumerate(options, 1):
        print(f"  {i}. {name:<12} {desc}", file=sys.stderr)
    print("  0. salir", file=sys.stderr)
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not choice.isdigit():
        return None
    n = int(choice)
    return n - 1 if 1 <= n <= len(options) else None


HELP_EPILOG = """Sin args y con TTY: menu interactivo.
Sin TTY se muestra esta ayuda (no se lanza nada).

env:
  AMO_API_KEY / AMO_API_SECRET  claves de https://addons.mozilla.org/developers/addon/api/key/
  CHROME2FOX_CONFIG             dir del registro de envios (def. ~/.config/chrome2fox)

Ejemplos:
  chrome2fox                                    # menu interactivo
  chrome2fox up ./mi-extension/ -o ./salida/    # ★ FLUJO COMPLETO
  chrome2fox status ./salida/
  chrome2fox my-addons
"""
