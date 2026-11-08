"""Batch 10b.1: the keyboard script must wait for Streamlit by CONDITION, not by a fixed wall-clock deadline.

Found with CPU stress: after Submit the page was fully drawn and the Next button present, but ArrowRight was
lost, because the key had waited more than MAX_WAIT_MS (1.5 s) for a slow rerun to finish and was then dropped.
These tests use a tiny synthetic page (no Streamlit server) and control the 'running' marker by hand, so they
fail deterministically with the old script and do not depend on machine speed.
"""
import pytest

pw_sync = pytest.importorskip("playwright.sync_api")

from utils import shortcuts

pytestmark = [pytest.mark.e2e]

PAGE = """<!doctype html><html><body>
<div class="st-key-nav_next"><button onclick="window.next=(window.next||0)+1">Next</button></div>
<div id="slot"></div>
<script>%s</script></body></html>"""

BUSY = '<div data-testid="stStatusWidget" id="busy">Running...</div>'


@pytest.fixture(scope="module")
def browser():
    with pw_sync.sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:
            pytest.skip(f"Chromium not available: {e}")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    pg = browser.new_context().new_page()
    pg.set_content(PAGE % shortcuts.script())
    pg.wait_for_function("() => typeof window.__etpShortcuts === 'function'")
    yield pg
    pg.context.close()


def set_busy(page, on):
    page.evaluate("on => { const s = document.getElementById('slot'); s.innerHTML = on ? %r : ''; }" % BUSY, on)


def clicks(page, name="next"):
    return page.evaluate(f"() => window.{name} || 0")


def test_key_waits_as_long_as_the_rerun_takes(page):
    set_busy(page, True)
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(3500)                    # a slow rerun: longer than the old 1.5 s deadline
    assert clicks(page) == 0                       # never clicks while Streamlit is running
    set_busy(page, False)
    page.wait_for_function("() => window.next === 1", timeout=5000)


def test_key_with_no_target_is_dropped_once_the_page_is_idle(page):
    """Pressing P where there is no Previous button must not fire later, when one appears."""
    page.keyboard.press("p")
    page.wait_for_timeout(1500)
    page.evaluate("""() => { const d = document.createElement('div'); d.className = 'st-key-nav_prev';
        d.innerHTML = '<button onclick="window.prev=(window.prev||0)+1">Previous</button>';
        document.body.appendChild(d); }""")
    page.wait_for_timeout(1000)
    assert clicks(page, "prev") == 0


def test_a_key_pressed_while_idle_clicks_immediately(page):
    page.keyboard.press("n")
    page.wait_for_function("() => window.next === 1", timeout=2000)


def test_keys_queue_in_order_and_each_clicks_once(page):
    set_busy(page, True)
    page.keyboard.press("n")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(300)
    set_busy(page, False)
    page.wait_for_function("() => window.next === 2", timeout=5000)
    page.wait_for_timeout(500)
    assert clicks(page) == 2
