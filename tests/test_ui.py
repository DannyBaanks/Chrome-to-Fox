"""Tests UI estilo munder/openmobile + comando up (offline, sin red)."""

from argparse import Namespace
from unittest.mock import patch

from chrome2fox import ui
from chrome2fox.ui import box, dash, menu


def test_box_renders_frame():
    out = box("▚ T", [("a", "1"), ("", "suelto")])
    assert out.startswith("┌") and out.endswith("┘")
    assert "▚ T" in out and "a:  1" in out and "suelto" in out
    assert all(len(line) == 80 for line in out.splitlines())


def test_dash_status_dot():
    assert "● OK" in dash(True, "T", [])
    assert "✗ FALLO" in dash(False, "T", [])


def test_menu_no_tty_returns_none():
    with patch.object(ui.sys.stdin, "isatty", return_value=False):
        assert menu([("up", "x")]) is None


def test_up_offline_success(simple_popup_dir, tmp_path, monkeypatch, capsys):
    """up corre el pipeline sin claves (sin sign) y deja dashboard + xpi."""
    from chrome2fox.cli import cmd_up
    for v in ("AMO_API_KEY", "AMO_API_SECRET"):
        monkeypatch.delenv(v, raising=False)
    out = tmp_path / "fox-out"
    rc = cmd_up(Namespace(input=str(simple_popup_dir), output=str(out),
                          api_key=None, api_secret=None, timeout=300))
    assert rc == 0
    assert (tmp_path / "fox-out.xpi").exists()
    err = capsys.readouterr().err
    assert "chrome2fox: flujo completo" in err


def test_up_missing_dir(tmp_path, capsys):
    from chrome2fox.cli import cmd_up
    rc = cmd_up(Namespace(input=str(tmp_path / "noexiste"), output=str(tmp_path / "o"),
                          api_key=None, api_secret=None, timeout=300))
    assert rc == 1
