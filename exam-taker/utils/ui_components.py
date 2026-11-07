"""Shared UI components for Exam Taker Pro (design system, Batch 2).

Pure functions that return HTML strings. All user text goes through
html.escape, but LaTeX ($...$ / $$...$$) is left readable. No emoji.
Styles live in utils/ui_helpers._GLOBAL_CSS (classes prefixed `etp-`).
The thin render_*() wrappers are the only functions that touch Streamlit.
"""
import html
import re
from typing import Iterable, Optional, Sequence

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
# "A) ", "B. ", "(C) ", "d) " at the very start. Anchored, so "$a) b$" is safe.
_OPTION_PREFIX = re.compile(r"^\s*(?:\([A-Za-z]\)\s*|[A-Za-z][.)]\s+)")


def option_label(text: Optional[str]) -> str:
    """Strip a leading option letter ("A) ", "B. ", "(C) ", "d) ") from option text."""
    if not text:
        return ""
    return _OPTION_PREFIX.sub("", text, count=1).strip()


def _esc(value) -> str:
    """Escape for HTML. `$...$` survives because html.escape never touches `$` or `\\`."""
    return html.escape("" if value is None else str(value), quote=False)


# Regions md_safe must leave alone: fenced code, inline code, $$display$$, $inline$ math.
_PROTECTED = re.compile(r"```.*?```|`[^`\n]+`|\$\$.*?\$\$|\$[^$\n]+\$", re.S)
_NBSP = "\u00a0"


def _escape_line(line: str, at_line_start: bool) -> str:
    # `\` before ASCII punctuation would swallow the escape we add next
    line = re.sub(r"\\(?=[!-/:-@\[-`{-~])", r"\\\\", line)
    line = re.sub(r"([*_\[\]<>|`])", r"\\\1", line)
    if not at_line_start:
        return line
    indent = re.match(r"[ \t]+", line)
    if indent:  # keep indentation visible, never let it become a code block
        width = len(indent.group(0).replace("\t", "    "))
        return _NBSP * width + line[indent.end():]
    line = re.sub(r"^#", r"\\#", line)
    line = re.sub(r"^([-+])(?=\s)", r"\\\1", line)
    line = re.sub(r"^(\d+)([.)])(?=\s)", r"\1\\\2", line)
    line = re.sub(r"^(-{3,}|={3,})\s*$", r"\\\1", line)
    return line


def md_safe(text: Optional[str]) -> str:
    """Make arbitrary question text safe for st.markdown.

    Escapes markdown control characters outside `code`, ```fences```, $math$
    and $$math$$; turns newlines into hard breaks; keeps leading indentation
    readable (non-breaking spaces). `__init__` renders as `__init__`.
    """
    if not text:
        return ""
    out = []
    pos = 0

    def plain(seg: str):
        at_start = not out or out[-1].endswith("\n")
        lines = seg.split("\n")
        done = [_escape_line(ln, at_start if i == 0 else True) for i, ln in enumerate(lines)]
        out.append("  \n".join(done))

    for m in _PROTECTED.finditer(text):
        if m.start() > pos:
            plain(text[pos:m.start()])
        out.append(m.group(0))
        pos = m.end()
    if pos < len(text):
        plain(text[pos:])
    return "".join(out)


# --- display-only LaTeX repair ------------------------------------------------
# JSON "\frac" (single backslash) decodes to FORM FEED + "rac"; same for \beta (\b),
# \times (\t), \right (\r), \nabla (\n). Question files are NOT modified: we map the
# control characters back, but only INSIDE $...$ / $$...$$ spans.
_MATH_SPAN = re.compile(r"\$\$.*?\$\$|\$(?:[^$\n]|\n(?!\n))+?\$", re.S)
# "\nabla" decodes to NEWLINE + "abla" (the escape swallows the "n"), so match the suffix.
_NEWLINE_COMMAND = re.compile(
    r"\n(?=(?:abla|eq|ewline|u|e|otin|i|ot|leq|geq|mid|rightarrow|atural)(?![a-zA-Z]))")
_CONTROL_TO_ESCAPE = {"\x0c": "\\f", "\x08": "\\b", "\t": "\\t", "\r": "\\r"}


def _repair_span(match):
    span = match.group(0)
    for ch, esc in _CONTROL_TO_ESCAPE.items():
        span = span.replace(ch, esc)
    return _NEWLINE_COMMAND.sub(lambda m: "\\n", span)


def repair_latex(text: Optional[str]) -> str:
    """Repair control characters that single-backslash LaTeX left inside math spans."""
    if not text:
        return ""
    return _MATH_SPAN.sub(_repair_span, text)


def md_text(text: Optional[str]) -> str:
    """The one pipeline for question / option / explanation text:
    \\( \\) -> $ $, repair_latex, then md_safe."""
    from utils import ui_helpers  # lazy: keeps this module free of Streamlit at import time
    if not text:
        return ""
    return md_safe(repair_latex(ui_helpers.prepare_math_text(text)))


def option_state(idx: int, correct_indices: Iterable[int], selected_indices: Iterable[int]) -> str:
    """'correct' | 'missed' | 'wrong' | 'neutral' for one option after submit."""
    correct = idx in set(correct_indices or [])
    selected = idx in set(selected_indices or [])
    if correct and selected:
        return "correct"
    if correct:
        return "missed"
    if selected:
        return "wrong"
    return "neutral"


# ---------------------------------------------------------------------------
# Badges and meta row
# ---------------------------------------------------------------------------
BADGE_KINDS = ("easy", "medium", "hard", "info", "reattempt", "neutral")


def badge(kind: str, text: str) -> str:
    kind = kind if kind in BADGE_KINDS else "neutral"
    return f'<span class="etp-badge etp-badge--{kind}">{_esc(text)}</span>'


def difficulty_badge(difficulty: Optional[str]) -> str:
    key = (difficulty or "").strip().lower()
    if key in ("easy", "medium", "hard"):
        return badge(key, key.capitalize())
    return badge("neutral", key.capitalize() or "Unknown")


def meta_row(tags: Optional[Sequence[str]], difficulty: Optional[str],
             is_reattempt: bool = False, next_due: Optional[str] = None) -> str:
    parts = [difficulty_badge(difficulty)]
    if is_reattempt:
        parts.append(badge("reattempt", "Reattempt"))
    parts.append(badge("info", f"Due {next_due}" if next_due else "New"))
    if tags:
        parts.append(f'<span class="etp-tag">{" · ".join(_esc(t) for t in tags)}</span>')
    return '<div class="etp-meta">' + "".join(parts) + "</div>"


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
def _join_letters(letters: Sequence[str]) -> str:
    letters = [str(x) for x in letters]
    if len(letters) <= 1:
        return "".join(letters)
    return ", ".join(letters[:-1]) + " and " + letters[-1]


def feedback(score: float, correct_letters: Sequence[str]):
    """Return (kind, title, body) for the result banner."""
    n = len(correct_letters)
    answer = (f"The right answer is {_join_letters(correct_letters)}." if n <= 1
              else f"The right answers are {_join_letters(correct_letters)}.")
    if score >= 1.0:
        return ("success", "Correct", "Well done.")
    if score > 0:
        return ("partial", f"Partly correct · score {score:.2f}", answer)
    return ("danger", "Not correct", answer)


def feedback_banner_html(kind: str, title: str, body: str = "") -> str:
    kind = kind if kind in ("success", "partial", "danger") else "danger"
    body_html = f'<div class="etp-banner__body">{_esc(body)}</div>' if body else ""
    return (f'<div class="etp-banner etp-banner--{kind}"><div>'
            f'<div class="etp-banner__title">{_esc(title)}</div>{body_html}</div></div>')


# ---------------------------------------------------------------------------
# Options and explanation
# ---------------------------------------------------------------------------
_STATUS_WORD = {"correct": "Correct", "missed": "Missed", "wrong": "Your pick"}
_OPTION_STATES = ("correct", "missed", "wrong", "neutral", "selected")


def option_row_html(letter: str, text: str, state: str = "neutral") -> str:
    state = state if state in _OPTION_STATES else "neutral"
    status = (f'<span class="etp-option__status">{_STATUS_WORD[state]}</span>'
              if state in _STATUS_WORD else "")
    return (f'<div class="etp-option is-{state}">'
            f'<span class="etp-option__key">{_esc(letter)}</span>'
            f'<span class="etp-option__text">{_esc(text)}</span>{status}</div>')


def explanation_html(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    body = "".join(f"<p>{_esc(p)}</p>" for p in paragraphs)
    return ('<div class="etp-explain"><div class="etp-explain__head">Explanation</div>'
            f'<div class="etp-explain__body">{body}</div></div>')


# ---------------------------------------------------------------------------
# List rows (Bookmarks, Archived, Wrong answers, Search, Notes)
# ---------------------------------------------------------------------------
from utils.ui_helpers import TOKENS as _TOKENS  # noqa: E402  (colours only; no cycle)

# bookmark name -> (token colour, short label). Names match bookmark_manager.BOOKMARK_COLORS.
BOOKMARK_STYLE = {
    "Important (Red)": (_TOKENS["bm_red"], "Important"),
    "Review Later (Orange)": (_TOKENS["bm_orange"], "Review later"),
    "Interesting (Blue)": (_TOKENS["bm_blue"], "Interesting"),
    "Hard (Purple)": (_TOKENS["bm_purple"], "Hard"),
    "Solved (Green)": (_TOKENS["bm_green"], "Solved"),
}


def bookmark_style(name: str):
    """(colour, short label) for a bookmark name; unknown names fall back to muted ink."""
    return BOOKMARK_STYLE.get(name, (_TOKENS["ink_muted"], str(name)))


def count_line(total: int, showing: int, noun: str) -> str:
    """'41 saved · showing 12'"""
    return f"{total} {noun} · showing {showing}"


def list_row_html(question_text, meta, dot_colour: Optional[str] = None) -> str:
    """One list row: optional colour dot, question (2-line clamp via CSS), one meta line.
    Text is HTML-escaped; `$...$` math is kept (and repaired) as in the other helpers."""
    if isinstance(meta, (list, tuple)):
        meta = " · ".join(str(m) for m in meta if m)
    dot = (f'<span class="etp-li__dot" style="background:{_esc(dot_colour)}"></span>'
           if dot_colour else "")
    return (f'<div class="etp-li">{dot}<div class="etp-li__body">'
            f'<div class="etp-li__q">{_esc(repair_latex(question_text))}</div>'
            f'<div class="etp-li__meta">{_esc(meta)}</div></div></div>')


# ---------------------------------------------------------------------------
# Page head and stat tiles
# ---------------------------------------------------------------------------
def page_head_html(title: str, subtitle: str = "") -> str:
    sub = f"<p>{_esc(subtitle)}</p>" if subtitle else ""
    return f'<div class="etp-pagehead"><div><h1>{_esc(title)}</h1>{sub}</div></div>'


def stat_tile_html(label: str, value, delta: Optional[str] = None,
                   trend: Optional[str] = None) -> str:
    delta_html = ""
    if delta:
        cls = "etp-stat__delta" + (f" {trend}" if trend in ("up", "down") else "")
        delta_html = f'<div class="{cls}">{_esc(delta)}</div>'
    return ('<div class="etp-stat">'
            f'<div class="etp-stat__label">{_esc(label)}</div>'
            f'<div class="etp-stat__value">{_esc(value)}</div>{delta_html}</div>')


def stat_tiles_html(tiles: Iterable[Sequence]) -> str:
    """tiles: iterable of (label, value[, delta[, trend]])."""
    return '<div class="etp-stats">' + "".join(stat_tile_html(*t) for t in tiles) + "</div>"


# ---------------------------------------------------------------------------
# Thin Streamlit wrappers (the only functions that call st.*)
# ---------------------------------------------------------------------------
def render_html(markup: str) -> None:
    import streamlit as st
    st.markdown(markup, unsafe_allow_html=True)


def render_page_head(title: str, subtitle: str = "") -> None:
    render_html(page_head_html(title, subtitle))


def render_feedback(score: float, correct_letters: Sequence[str]) -> None:
    render_html(feedback_banner_html(*feedback(score, correct_letters)))


def render_stat_tiles(tiles: Iterable[Sequence]) -> None:
    render_html(stat_tiles_html(tiles))
