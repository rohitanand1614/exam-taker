"""A free local port for an e2e Streamlit server that Chromium will actually connect to.

Asking the OS for port 0 can return a port that Chromium blocks with net::ERR_UNSAFE_PORT (IRC 6665-6669, ...).
That made every test of a module fail at once, with no relation to the app. This is Chromium's restricted-port list
(net/base/port_util.cc) plus the well-known ports below 1024 are never returned anyway.
"""
import socket
from typing import Callable, Optional

CHROMIUM_UNSAFE_PORTS = frozenset({
    1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 69, 77, 79, 87, 95, 101, 102, 103, 104, 109,
    110, 111, 113, 115, 117, 119, 123, 135, 137, 139, 143, 161, 179, 389, 427, 465, 512, 513, 514, 515, 526, 530,
    531, 532, 540, 548, 554, 556, 563, 587, 601, 636, 989, 990, 993, 995, 1719, 1720, 1723, 2049, 3659, 4045, 4190,
    5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6679, 6697, 10080,
})


def _os_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def free_port(_next_candidate: Optional[Callable[[], int]] = None) -> int:
    """A free port that is not on Chromium's blocked list (the candidate source is injectable for the unit test)."""
    pick = _next_candidate or _os_port
    for _ in range(200):
        port = pick()
        if port not in CHROMIUM_UNSAFE_PORTS and port >= 1024:
            return port
    raise RuntimeError("could not find a free port that Chromium accepts")
