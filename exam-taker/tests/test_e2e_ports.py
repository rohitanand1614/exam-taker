"""Batch 10b.1, second cause: the e2e fixtures asked the OS for a random free port, and once it returned 6665.
Chromium refuses a handful of ports (IRC 6665-6669, ...) with net::ERR_UNSAFE_PORT, so every test of that module
failed at once. All e2e servers now take their port from tests/e2e/ports.py, which skips those ports."""
import re
from pathlib import Path

import pytest

from tests.e2e import ports

TESTS = Path(__file__).resolve().parent
MODULES = sorted((TESTS / "e2e").glob("test_*.py")) + [TESTS / "test_ui_bookmark_colours.py"]


def test_known_unsafe_ports_are_listed():
    for port in (6665, 6666, 6667, 6668, 6669, 6697, 6000, 5060, 10080, 2049, 1720):
        assert port in ports.CHROMIUM_UNSAFE_PORTS


def test_free_port_skips_unsafe_ports():
    offered = iter([6665, 6667, 6000, 51234, 51235])
    assert ports.free_port(_next_candidate=lambda: next(offered)) == 51234


def test_free_port_returns_a_usable_port_by_default():
    port = ports.free_port()
    assert 1024 <= port <= 65535 and port not in ports.CHROMIUM_UNSAFE_PORTS


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_every_e2e_module_takes_its_port_from_the_helper(path):
    text = path.read_text(encoding="utf-8")
    assert "s.bind((" not in text, f"{path.name} picks its own port"
    if "--server.port" in text:
        assert "from tests.e2e.ports import free_port" in text, path.name
        assert not re.search(r"^def _?free_port", text, re.M), path.name
