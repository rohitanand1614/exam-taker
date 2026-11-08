"""Failure evidence for the real-browser tests: on a failing e2e test save the traceback, a screenshot, the page
HTML, the browser console and the server log to tests/.artifacts/flaky/<time>_<test>/ (Batch 10b.1)."""
import re
import time
from pathlib import Path

import pytest

ARTIFACTS = Path(__file__).resolve().parents[1] / ".artifacts" / "flaky"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call" or not rep.failed:
        return
    try:
        _save_evidence(item, rep)
    except Exception:                                            # never turn a test failure into an INTERNALERROR
        pass


def _save_evidence(item, rep):
    out = ARTIFACTS / (time.strftime("%Y%m%d_%H%M%S_") + re.sub(r"\W+", "_", item.name))
    out.mkdir(parents=True, exist_ok=True)
    (out / "traceback.txt").write_text(rep.longreprtext, encoding="utf-8")
    page = item.funcargs.get("page") or item.funcargs.get("offline")
    if page is not None:
        try:
            page.screenshot(path=str(out / "screenshot.png"), full_page=True)
            (out / "page.html").write_text(page.content(), encoding="utf-8")
            (out / "console.log").write_text("\n".join(getattr(page, "console_log", [])), encoding="utf-8")
            (out / "shortcuts.log").write_text("\n".join(page.evaluate("() => window.__etpLog || []")), encoding="utf-8")
        except Exception as e:                                   # the page may already be closed
            (out / "capture_error.txt").write_text(repr(e), encoding="utf-8")
    server = item.funcargs.get("server")
    work = None
    if isinstance(server, tuple) and len(server) == 2:           # test_keyboard_flow: (url, workspace)
        work = server[1]
    elif isinstance(server, str):                               # other e2e modules: just the url (no workspace)
        work = None
    try:
        if work is not None:
            log = Path(work) / "server.log"
            if log.exists():
                (out / "server.log").write_text(log.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            attempts = Path(work) / "logs" / "attempts"
            if attempts.exists():
                text = []
                for f in sorted(attempts.glob("*.json")):
                    text.append(f.name + chr(10) + f.read_text(encoding="utf-8"))
                (out / "attempts.txt").write_text((chr(10) * 2).join(text), encoding="utf-8")
    except Exception as e:                                       # evidence gathering must never break the run
        (out / "capture_error_server.txt").write_text(repr(e), encoding="utf-8")
