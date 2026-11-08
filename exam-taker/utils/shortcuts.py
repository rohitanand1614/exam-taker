"""Keyboard shortcuts for the exam pages (Exam, Practice incorrect, Practice bookmarks, Targeted drill,
Regressive practice).

    1-9 / A-H        select that answer (toggles it on multi-select questions)
    Enter            Submit answer
    ArrowRight / N   Next          ArrowLeft / P   Previous
    Shift+B          open the bookmark popover  (plain B is the answer letter B)

No logic changes and no new dependency: one `components.html` script appends a <script> to the PARENT
document (so it survives the iframe being replaced), which listens for keydown and CLICKS the buttons and
answer labels that are already on the page, found by their `st-key-*` class. Keys are ignored while typing in
an input / textarea / select / contenteditable (Quill) and when Ctrl, Alt or Meta is held.

`KEY_MAP` and `SELECTORS` are plain data: the unit tests check them and the script is generated from them,
so the browser and the tests cannot drift apart.
"""
import json
from typing import Optional, Tuple

import streamlit.components.v1 as components

# ---------------------------------------------------------------------------- the key map (pure data)
OPTION_KEYS = "123456789"
OPTION_LETTERS = "abcdefgh"          # n, p and b are not answer letters here (b = answer B, bookmark = Shift+B)

KEY_MAP = {
    **{k: ("option", i) for i, k in enumerate(OPTION_KEYS)},
    **{k: ("option", i) for i, k in enumerate(OPTION_LETTERS)},
    "Enter": ("submit", None),
    "ArrowRight": ("next", None),
    "n": ("next", None),
    "ArrowLeft": ("prev", None),
    "p": ("prev", None),
}
BOOKMARK_KEY = "B"                    # Shift+B

# every exam page has these keyed containers/buttons (CSS hooks from the redesign)
SELECTORS = {
    "radio": '.st-key-answers [role="radiogroup"] label',
    "checkbox": '.st-key-answers [data-testid="stCheckbox"] label',
    "submit": ['[class*="st-key-nav_submit"] button', '[class*="st-key-drill_submit_"] button'],
    "next": ['[class*="st-key-nav_next"] button', '[class*="st-key-drill_next_"] button',
             '[class*="st-key-reg_next"] button'],
    "prev": ['[class*="st-key-nav_prev"] button'],
    "bookmark": '.st-key-qcard [data-testid="stPopover"] button',
}

HINTS = {"submit": "Enter", "next": "N", "prev": "P"}      # shown on the buttons (CSS, ui_helpers)


def action_for(key: str, shift: bool = False) -> Optional[Tuple[str, Optional[int]]]:
    """('option', index) / ('submit'|'next'|'prev'|'bookmark', None) for a KeyboardEvent.key, else None.

    Letters are case-insensitive, except that Shift+letter never selects an answer, and Shift+B is the bookmark.
    """
    if key == BOOKMARK_KEY and shift:
        return ("bookmark", None)
    if len(key) == 1 and key.isalpha():
        if shift:
            return None
        key = key.lower()
    if shift and key in OPTION_KEYS:          # Shift+1 is '!' on most layouts; be strict anyway
        return None
    return KEY_MAP.get(key)


# ---------------------------------------------------------------------------- the browser side
_HANDLER = r"""
(function () {
  var KEY_MAP = %(key_map)s, SEL = %(selectors)s, BOOKMARK_KEY = %(bookmark_key)s;
  var GAP_MS = 150, POLL_MS = 60, MAX_WAIT_MS = 1500;
  if (window.__etpShortcuts) { document.removeEventListener('keydown', window.__etpShortcuts, true); }

  function typing(el) {
    if (!el) return false;
    if (el.isContentEditable || (el.closest && el.closest('.ql-editor, [contenteditable="true"]'))) return true;
    var tag = (el.tagName || '').toLowerCase();
    if (tag === 'textarea' || tag === 'select') return true;
    if (tag === 'input') return ['radio', 'checkbox', 'button', 'submit'].indexOf((el.type || '').toLowerCase()) < 0;
    return false;
  }
  function visible(el) {
    return !!(el && el.offsetParent !== null && !el.disabled && !(el.closest && el.closest('[data-stale="true"]')));
  }
  function first(selectors) {
    for (var i = 0; i < selectors.length; i++) {
      var found = Array.prototype.filter.call(document.querySelectorAll(selectors[i]), visible);
      if (found.length) return found[0];
    }
    return null;
  }
  function options() {
    var radios = Array.prototype.filter.call(document.querySelectorAll(SEL.radio), visible);
    return radios.length ? radios : Array.prototype.filter.call(document.querySelectorAll(SEL.checkbox), visible);
  }
  function actionFor(e) {
    if (e.key === BOOKMARK_KEY && e.shiftKey) return ['bookmark', null];
    var k = e.key;
    if (k.length === 1 && /[a-z]/i.test(k)) { if (e.shiftKey) return null; k = k.toLowerCase(); }
    if (e.shiftKey && /[0-9]/.test(k)) return null;
    return KEY_MAP[k] || null;
  }
  function find(a) {
    if (a[0] === 'option') return options()[a[1]];
    if (a[0] === 'submit') return first(SEL.submit);
    if (a[0] === 'next') return first(SEL.next);
    if (a[0] === 'prev') return first(SEL.prev);
    return first([SEL.bookmark]);
  }
  // A click starts a rerun; the next key must not hit a stale element of the old run (the stem is redrawn
  // before the answers), so actions run one at a time, only while Streamlit is idle.
  function running() {
    return !!(document.querySelector('[data-testid="stStatusWidget"]') || document.querySelector('[data-stale="true"]'));
  }
  var queue = [], lastClick = 0, timer = null;
  function drain() {
    timer = null;
    while (queue.length && Date.now() > queue[0].deadline) queue.shift();       // never wait forever
    if (!queue.length) return;
    if (Date.now() - lastClick < GAP_MS || running()) { timer = setTimeout(drain, POLL_MS); return; }
    var target = find(queue[0].a);
    if (!target) { timer = setTimeout(drain, POLL_MS); return; }          // not drawn yet: keep waiting
    queue.shift();
    target.click(); lastClick = Date.now();
    if (queue.length) timer = setTimeout(drain, POLL_MS);
  }
  function onKey(e) {
    if (e.ctrlKey || e.altKey || e.metaKey || e.isComposing) return;
    if (typing(e.target)) return;
    var a = actionFor(e);
    if (!a) return;
    var tag = e.target && e.target.tagName;
    if (a[0] === 'submit' && (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY')) return;   // native Enter on a focused control
    // The target may not exist YET (the key can arrive between a click and the redraw it causes), so the
    // action is queued and resolved when it runs; if it never appears it is dropped after MAX_WAIT_MS.
    e.preventDefault(); e.stopPropagation();   // also stops arrow keys moving a focused radio
    queue.push({a: a, deadline: Date.now() + MAX_WAIT_MS});
    if (!timer) timer = setTimeout(drain, 0);
  }
  window.__etpShortcuts = onKey;
  document.addEventListener('keydown', onKey, true);
})();
"""


def script() -> str:
    """The JavaScript that is injected into the parent document (generated from KEY_MAP / SELECTORS)."""
    return _HANDLER % {
        "key_map": json.dumps({k: list(v) for k, v in KEY_MAP.items()}),
        "selectors": json.dumps(SELECTORS),
        "bookmark_key": json.dumps(BOOKMARK_KEY),
    }


def render():
    """Install the shortcuts (idempotent). Call once per exam page, after the question card is drawn."""
    loader = (
        "<script>(function(){var p=window.parent,d=p.document;"
        "var old=d.getElementById('etp-shortcuts-script');if(old)old.remove();"
        "var s=d.createElement('script');s.id='etp-shortcuts-script';s.textContent="
        + json.dumps(script())
        + ";d.head.appendChild(s);})();</script>"
    )
    components.html(loader, height=0)
