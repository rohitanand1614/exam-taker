"""UI helpers for Exam Taker Pro.

Design system: "Exam Taker Pro" (Slate Night theme).
Only presentation lives here. Function names and signatures are unchanged,
so app.py and pages/*.py keep working without edits.
"""
import json
import re
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Design tokens (Slate Night). Keep in sync with .streamlit/config.toml
# ---------------------------------------------------------------------------
TOKENS = {
    "bg": "#15171a",
    "surface": "#1c1f23",
    "surface_raised": "#23272c",
    "surface_sunken": "#111316",
    "border": "#2c3136",
    "border_strong": "#646c75",
    "ink": "#e6e1d8",
    "ink_reading": "#d5cfc4",
    "ink_muted": "#a29d93",
    "ink_faint": "#8a857c",
    "accent": "#8cc29f",
    "accent_fill": "#35553f",
    "on_accent_fill": "#eef4ef",
    "selected_bg": "#1f2a24",
    "success": "#8cc29f",
    "success_bg": "#1b2a21",
    "success_border": "#3f6b4f",
    "danger": "#e0968a",
    "danger_bg": "#2d1f1d",
    "danger_border": "#7a4a42",
    "warning": "#dcae6e",
    "warning_bg": "#2b2418",
    "warning_border": "#6e5730",
    "info": "#93aecf",
    "info_bg": "#1b2330",
}

FONT_READING = "Literata, Georgia, 'Times New Roman', serif"
FONT_UI = "'Atkinson Hyperlegible', 'Segoe UI', system-ui, sans-serif"
FONT_MONO = "'JetBrains Mono', Consolas, monospace"

_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Atkinson+Hyperlegible:wght@400;700"
    "&family=JetBrains+Mono:wght@400"
    "&family=Literata:opsz,wght@7..72,400;7..72,500;7..72,600"
    "&display=swap"
)

# Difficulty colours (use instead of "green"/"orange"/"red" strings)
DIFFICULTY_COLORS = {
    "EASY": TOKENS["success"],
    "MEDIUM": TOKENS["warning"],
    "HARD": TOKENS["danger"],
}

# ---------------------------------------------------------------------------
# Math / LaTeX rendering helpers
# ---------------------------------------------------------------------------

_KATEX_HEAD = (
    f'<link rel="stylesheet" href="{_FONTS_URL}">'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">'
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>'
    '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"'
    ' onload="renderMathInElement(document.body,{'
    'delimiters:[{left:\'$$\',right:\'$$\',display:true},{left:\'$\',right:\'$\',display:false}],'
    'throwOnError:false});"></script>'
)


def prepare_math_text(text: str) -> str:
    """Convert \\[...\\] and \\(...\\) delimiters to $$...$$ and $...$
    so Streamlit's KaTeX renderer and render_math_text() can handle them."""
    if not text:
        return text
    text = re.sub(r'\\\[', '$$', text)
    text = re.sub(r'\\\]', '$$', text)
    text = re.sub(r'\\\(', '$', text)
    text = re.sub(r'\\\)', '$', text)
    return text


def render_math_text(
    text: str,
    font_size: str = "1rem",
    font_weight: str = "normal",
    extra_style: str = "",
    height: int = 70,
) -> None:
    """Render *text* (which may contain $...$ / $$...$$ LaTeX) in a KaTeX-
    enabled HTML component, using the reading font."""
    t = TOKENS
    html = (
        "<!DOCTYPE html><html><head>"
        + _KATEX_HEAD
        + "<style>*{box-sizing:border-box;margin:0;padding:0}"
        f"html,body{{background:transparent;font-family:{FONT_READING};"
        f"color:{t['ink_reading']};font-size:{font_size};font-weight:{font_weight};"
        "line-height:1.45;-webkit-font-smoothing:antialiased;"
        f"padding:4px 6px;{extra_style}}}"
        f"code{{font-family:{FONT_MONO};font-size:.85em;background:{t['surface_sunken']};"
        f"color:{t['ink']};padding:1px 5px;border-radius:6px}}"
        f"b,strong{{color:{t['ink']}}}"
        ".katex{font-size:1.05em}"
        "</style></head>"
        f"<body>{text}</body></html>"
    )
    components.html(html, height=height, scrolling=False)


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
_t = TOKENS
_GLOBAL_CSS = f"""
<style>
@import url('{_FONTS_URL}');

:root {{
  --etp-bg:{_t['bg']}; --etp-surface:{_t['surface']}; --etp-raised:{_t['surface_raised']};
  --etp-sunken:{_t['surface_sunken']}; --etp-border:{_t['border']}; --etp-border-strong:{_t['border_strong']};
  --etp-ink:{_t['ink']}; --etp-read:{_t['ink_reading']}; --etp-muted:{_t['ink_muted']}; --etp-faint:{_t['ink_faint']};
  --etp-accent:{_t['accent']}; --etp-fill:{_t['accent_fill']}; --etp-on-fill:{_t['on_accent_fill']};
  --etp-success:{_t['success']}; --etp-success-bg:{_t['success_bg']}; --etp-success-border:{_t['success_border']};
  --etp-danger:{_t['danger']}; --etp-danger-bg:{_t['danger_bg']}; --etp-danger-border:{_t['danger_border']};
  --etp-warn:{_t['warning']}; --etp-warn-bg:{_t['warning_bg']}; --etp-warn-border:{_t['warning_border']};
  --etp-info:{_t['info']}; --etp-info-bg:{_t['info_bg']};
  --etp-selected-bg:{_t['selected_bg']};
  --etp-s1:4px; --etp-s2:8px; --etp-s3:12px; --etp-s4:16px; --etp-s5:24px; --etp-s6:32px; --etp-s7:48px;
  --etp-r-sm:6px; --etp-r-md:10px; --etp-r-lg:14px; --etp-r-pill:999px;
  --etp-measure:68ch; --etp-target:44px;
}}

/* ---------- Base ---------- */
html, body, .stApp, [class*="css"], button, input, textarea, select {{
  font-family: {FONT_UI};
}}
.stApp {{ background-color: var(--etp-bg); color: var(--etp-ink); }}
.stApp p, .stApp li {{ color: var(--etp-read); line-height: 1.6; }}
.block-container {{ max-width: 980px; padding-top: 2.5rem; }}
h1, h2, h3, h4 {{ font-family: {FONT_UI} !important; color: var(--etp-ink) !important; letter-spacing: -0.01em; }}
h1 {{ font-size: 1.65rem !important; font-weight: 700 !important; }}
h3 {{ font-size: 1.15rem !important; font-weight: 700 !important; }}
a {{ color: var(--etp-accent) !important; }}
code {{ font-family: {FONT_MONO} !important; }}
hr {{ border-color: var(--etp-border) !important; }}
[data-testid="stCaptionContainer"], .stCaption, small {{ color: var(--etp-muted) !important; }}
::selection {{ background: rgba(140,194,159,.28); }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: var(--etp-bg); }}
::-webkit-scrollbar-thumb {{ background: var(--etp-raised); border-radius: 999px; border: 2px solid var(--etp-bg); }}
::-webkit-scrollbar-thumb:hover {{ background: var(--etp-border-strong); }}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {{
  background-color: var(--etp-sunken);
  border-right: 1px solid var(--etp-border);
}}
section[data-testid="stSidebar"] h1 {{ font-size: 1.15rem !important; }}
section[data-testid="stSidebar"] h3 {{
  font-size: .75rem !important; text-transform: uppercase; letter-spacing: .06em !important;
  color: var(--etp-muted) !important;
}}
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNavLink"] {{ border-radius: 10px; }}
[data-testid="stSidebarNav"] a span, [data-testid="stSidebarNavLink"] span {{ color: var(--etp-muted); }}
[data-testid="stSidebarNav"] a:hover span, [data-testid="stSidebarNavLink"]:hover span {{ color: var(--etp-ink); }}
[data-testid="stSidebarNav"] a[aria-current="page"], [data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: var(--etp-surface);
}}
[data-testid="stSidebarNav"] a[aria-current="page"] span,
[data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: var(--etp-ink); font-weight: 700; }}

/* ---------- Cards & reading blocks ---------- */
.question-card {{
  background-color: var(--etp-surface);
  padding: 1.5rem;
  border-radius: 14px;
  border: 1px solid var(--etp-border);
  box-shadow: 0 1px 2px rgba(0,0,0,.35);
  margin-bottom: 1.5rem;
}}
.question-card:empty {{ display: none; }}
.question-text {{
  font-family: {FONT_READING};
  font-size: 1.25rem; font-weight: 500; line-height: 1.6;
  color: var(--etp-ink); max-width: 68ch; margin-bottom: 1.5rem;
}}
.success-box, .error-box, .warning-box {{
  padding: .9rem 1rem; border-radius: 10px; margin-top: 1rem; border: 1px solid;
  font-family: {FONT_UI};
}}
.success-box {{ background: var(--etp-success-bg); border-color: var(--etp-success-border); color: var(--etp-success); }}
.error-box   {{ background: var(--etp-danger-bg);  border-color: var(--etp-danger-border);  color: var(--etp-danger); }}
.warning-box {{ background: var(--etp-warn-bg);    border-color: var(--etp-warn-border);    color: var(--etp-warn); }}
.explanation-box {{
  background: var(--etp-info-bg); border: 1px solid var(--etp-border);
  padding: 1.25rem; margin-top: 1rem; border-radius: 14px;
  font-family: {FONT_READING}; font-size: 1.05rem; line-height: 1.7; color: var(--etp-read);
}}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--etp-border) !important; border-radius: 14px !important; }}

/* ---------- Buttons ---------- */
.stButton button, .stDownloadButton button, .stFormSubmitButton button,
button[data-testid^="stBaseButton"] {{
  min-height: 44px;
  background-color: transparent;
  color: var(--etp-ink);
  border: 1px solid var(--etp-border-strong);
  border-radius: 10px;
  padding: .45rem 1.1rem;
  font-weight: 700;
  font-family: {FONT_UI};
  transition: background-color .15s ease, border-color .15s ease, color .15s ease;
}}
.stButton button:hover, .stDownloadButton button:hover, button[data-testid^="stBaseButton"]:hover {{
  background-color: var(--etp-raised);
  border-color: var(--etp-border-strong);
  color: var(--etp-ink);
}}
.stButton button:focus-visible, button[data-testid^="stBaseButton"]:focus-visible {{
  outline: 2px solid var(--etp-accent) !important; outline-offset: 2px; box-shadow: none !important;
}}
.stButton button[kind="primary"], button[data-testid="stBaseButton-primary"] {{
  background-color: var(--etp-fill); border-color: var(--etp-fill); color: var(--etp-on-fill);
}}
.stButton button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {{
  background-color: var(--etp-fill); border-color: var(--etp-accent); color: var(--etp-on-fill);
  filter: brightness(1.12);
}}
.stButton button[kind="tertiary"], button[data-testid="stBaseButton-tertiary"] {{
  border-color: transparent; color: var(--etp-muted); min-height: 36px;
}}
.stButton button:disabled {{ opacity: .45; }}
.stButton button p {{ color: inherit !important; font-weight: 700; }}

/* ---------- Radio (answer options) ---------- */
div[data-testid="stRadio"] > label p, div[data-testid="stCheckbox"] label p {{
  color: var(--etp-read) !important;
}}
section[data-testid="stMain"] div[data-testid="stRadio"] [role="radiogroup"] {{ gap: .5rem; }}
section[data-testid="stMain"] div[data-testid="stRadio"] [role="radiogroup"] > label {{
  border: 1px solid var(--etp-border-strong); border-radius: 10px;
  padding: .55rem .9rem; min-height: 44px; margin: 0;
  transition: background-color .15s ease, border-color .15s ease;
}}
section[data-testid="stMain"] div[data-testid="stRadio"] [role="radiogroup"] > label:hover {{ background: var(--etp-raised); }}
section[data-testid="stMain"] div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {{
  background: {_t['selected_bg']}; border-color: var(--etp-accent);
}}
section[data-testid="stMain"] div[data-testid="stRadio"] [role="radiogroup"] label p {{
  color: var(--etp-read) !important; font-size: 1rem !important; font-weight: 500 !important;
  font-family: {FONT_READING};
}}
section[data-testid="stMain"] div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p {{ color: var(--etp-ink) !important; }}

/* ---------- Inputs ---------- */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, .stTextInput input,
.stTextArea textarea, [data-baseweb="textarea"] {{
  background-color: var(--etp-surface) !important;
  border-color: var(--etp-border-strong) !important;
  color: var(--etp-ink) !important;
  border-radius: 10px !important;
}}
[data-baseweb="popover"] ul, [data-baseweb="menu"] {{ background: var(--etp-raised) !important; }}
[data-baseweb="tag"] {{ background: var(--etp-raised) !important; color: var(--etp-ink) !important; border-radius: 6px !important; }}
.stTextArea textarea {{ font-family: {FONT_MONO} !important; font-size: .9rem !important; }}
[data-testid="stWidgetLabel"] p {{ color: var(--etp-muted) !important; font-size: .85rem !important; }}

/* ---------- Expander ---------- */
[data-testid="stExpander"] details {{
  background: var(--etp-surface); border: 1px solid var(--etp-border) !important; border-radius: 14px !important;
}}
[data-testid="stExpander"] summary {{ border-radius: 14px; }}
[data-testid="stExpander"] summary:hover {{ background: var(--etp-raised); }}
[data-testid="stExpander"] summary p {{ color: var(--etp-ink) !important; font-weight: 600; }}

/* ---------- Metrics ---------- */
[data-testid="stMetric"] {{
  background: var(--etp-surface); border: 1px solid var(--etp-border);
  border-radius: 14px; padding: 1rem 1.1rem;
}}
[data-testid="stMetricLabel"] p {{
  color: var(--etp-muted) !important; font-size: .75rem !important; font-weight: 700 !important;
  text-transform: uppercase; letter-spacing: .06em;
}}
[data-testid="stMetricValue"] {{ color: var(--etp-ink) !important; font-weight: 700; font-variant-numeric: tabular-nums; }}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: .25rem; border-bottom: 1px solid var(--etp-border); }}
.stTabs [data-baseweb="tab"] p {{ color: var(--etp-muted); font-weight: 600; }}
.stTabs [aria-selected="true"] p {{ color: var(--etp-ink); }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: var(--etp-accent) !important; }}

/* ---------- Alerts, progress, toasts ---------- */
[data-testid="stAlert"] {{ border-radius: 10px; }}
[data-testid="stProgress"] > div > div {{ background-color: var(--etp-raised) !important; }}
[data-testid="stProgress"] > div > div > div > div {{ background-color: var(--etp-accent) !important; }}
[data-testid="stToast"] {{ background: var(--etp-raised) !important; border: 1px solid var(--etp-border); color: var(--etp-ink); }}

/* ---------- Dataframes ---------- */
[data-testid="stDataFrame"] {{ border: 1px solid var(--etp-border); border-radius: 10px; }}

/* ---------- Exam navigation row (after submit) ---------- */
/* Simple Retry — muted amber outline */
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="column"]:nth-of-type(2) button,
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-of-type(2) button,
[data-testid="stElementContainer"]:has(#nav-buttons-marker) + [data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-of-type(2) button {{
  background-color: transparent !important;
  border-color: var(--etp-warn-border) !important;
  color: var(--etp-warn) !important;
  filter: none !important;
}}
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="column"]:nth-of-type(2) button:hover,
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-of-type(2) button:hover,
[data-testid="stElementContainer"]:has(#nav-buttons-marker) + [data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-of-type(2) button:hover {{
  background-color: var(--etp-warn-bg) !important;
}}
/* Hard Retry — muted terracotta outline (never filled red) */
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="column"]:nth-of-type(3) button,
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-of-type(3) button,
[data-testid="stElementContainer"]:has(#nav-buttons-marker) + [data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-of-type(3) button {{
  background-color: transparent !important;
  border-color: var(--etp-danger-border) !important;
  color: var(--etp-danger) !important;
  filter: none !important;
}}
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="column"]:nth-of-type(3) button:hover,
div:has(#nav-buttons-marker) ~ div[data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-of-type(3) button:hover,
[data-testid="stElementContainer"]:has(#nav-buttons-marker) + [data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-of-type(3) button:hover {{
  background-color: var(--etp-danger-bg) !important;
}}
</style>
"""


# ---------------------------------------------------------------------------
# Component CSS (Batch 2). Values from design-system/reference-components.css,
# expressed with the --etp-* variables above. Used by utils/ui_components.py.
# ---------------------------------------------------------------------------
_COMPONENT_CSS = """
/* ---------- Components (utils/ui_components.py) ---------- */
.etp-meta { display: flex; align-items: center; gap: var(--etp-s2); flex-wrap: wrap; }
.etp-badge { display: inline-flex; align-items: center; gap: var(--etp-s1); padding: 2px var(--etp-s2);
  border-radius: var(--etp-r-sm); font: 700 12px/16px __UI__; letter-spacing: .04em; text-transform: uppercase;
  border: 1px solid var(--etp-border); color: var(--etp-muted); background: var(--etp-surface); }
.etp-badge--easy { color: var(--etp-success); border-color: var(--etp-success-border); }
.etp-badge--medium { color: var(--etp-warn); border-color: var(--etp-warn-border); }
.etp-badge--hard { color: var(--etp-danger); border-color: var(--etp-danger-border); }
.etp-badge--info { color: var(--etp-info); }
.etp-badge--reattempt { color: var(--etp-warn); border-color: var(--etp-warn-border); background: var(--etp-warn-bg); }
.etp-badge--neutral { color: var(--etp-muted); }
.etp-tag { font: 400 13px/18px __UI__; color: var(--etp-muted); }

.etp-option { display: flex; gap: var(--etp-s4); align-items: flex-start; width: 100%; box-sizing: border-box;
  max-width: calc(var(--etp-measure) + 80px); min-height: var(--etp-target); padding: var(--etp-s3) var(--etp-s4);
  margin-bottom: var(--etp-s2); border: 1px solid var(--etp-border-strong); border-radius: var(--etp-r-md);
  background: transparent; color: var(--etp-read); font: 400 17px/27px __READ__; text-align: left; }
.etp-option__key { flex: none; width: 28px; height: 28px; margin-top: -1px; display: grid; place-items: center;
  border-radius: var(--etp-r-sm); border: 1px solid var(--etp-border-strong); font: 700 13px/1 __UI__; color: var(--etp-muted); }
.etp-option__text { flex: 1; }
.etp-option__status { flex: none; display: inline-flex; align-items: center; gap: var(--etp-s1); font: 700 13px/27px __UI__; }
.etp-option.is-neutral { opacity: .85; }
.etp-option.is-selected { background: var(--etp-selected-bg); border-color: var(--etp-accent); color: var(--etp-ink); }
.etp-option.is-selected .etp-option__key { background: var(--etp-accent); border-color: var(--etp-accent); color: var(--etp-bg); }
.etp-option.is-correct { background: var(--etp-success-bg); border-color: var(--etp-success-border); color: var(--etp-ink); }
.etp-option.is-correct .etp-option__key, .etp-option.is-correct .etp-option__status { color: var(--etp-success); border-color: var(--etp-success-border); }
.etp-option.is-missed { background: var(--etp-warn-bg); border-color: var(--etp-warn-border); border-style: dashed; }
.etp-option.is-missed .etp-option__key, .etp-option.is-missed .etp-option__status { color: var(--etp-warn); border-color: var(--etp-warn-border); }
.etp-option.is-wrong { background: var(--etp-danger-bg); border-color: var(--etp-danger-border); }
.etp-option.is-wrong .etp-option__key, .etp-option.is-wrong .etp-option__status { color: var(--etp-danger); border-color: var(--etp-danger-border); }

.etp-banner { display: flex; gap: var(--etp-s3); align-items: flex-start; padding: var(--etp-s4);
  border-radius: var(--etp-r-md); border: 1px solid; margin: var(--etp-s3) 0; }
.etp-banner__title { font: 700 15px/22px __UI__; }
.etp-banner__body { font: 400 13px/18px __UI__; color: var(--etp-muted); margin-top: 2px; }
.etp-banner--success { background: var(--etp-success-bg); border-color: var(--etp-success-border); color: var(--etp-success); }
.etp-banner--partial { background: var(--etp-warn-bg); border-color: var(--etp-warn-border); color: var(--etp-warn); }
.etp-banner--danger { background: var(--etp-danger-bg); border-color: var(--etp-danger-border); color: var(--etp-danger); }

.etp-explain { background: var(--etp-info-bg); border: 1px solid var(--etp-border); border-radius: var(--etp-r-lg);
  padding: var(--etp-s5); margin-top: var(--etp-s3); }
.etp-explain__head { display: flex; align-items: center; gap: var(--etp-s2); color: var(--etp-info);
  font: 700 12px/16px __UI__; letter-spacing: .06em; text-transform: uppercase; margin-bottom: var(--etp-s3); }
.etp-explain__body { font: 400 17px/29px __READ__; color: var(--etp-read); max-width: var(--etp-measure); }
.etp-explain__body p { margin: 0 0 var(--etp-s3); }
.etp-explain__body code { font: 400 14px/22px __MONO__; background: var(--etp-sunken); padding: 1px 5px;
  border-radius: var(--etp-r-sm); color: var(--etp-ink); }

.etp-pagehead { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--etp-s4); margin-bottom: var(--etp-s4); }
.etp-pagehead h1 { margin: 0; font: 700 26px/34px __UI__ !important; letter-spacing: -0.01em; color: var(--etp-ink); }
.etp-pagehead p { margin: var(--etp-s1) 0 0; font: 400 13px/18px __UI__; color: var(--etp-muted); }

.etp-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--etp-s3); }
.etp-stat { background: var(--etp-surface); border: 1px solid var(--etp-border); border-radius: var(--etp-r-lg); padding: var(--etp-s4); }
.etp-stat__label { font: 700 12px/16px __UI__; letter-spacing: .06em; text-transform: uppercase; color: var(--etp-muted); }
.etp-stat__value { font: 700 30px/36px __UI__; color: var(--etp-ink); margin-top: var(--etp-s2); font-variant-numeric: tabular-nums; }
.etp-stat__delta { font: 400 13px/18px __UI__; color: var(--etp-muted); }
.etp-stat__delta.up { color: var(--etp-success); }
.etp-stat__delta.down { color: var(--etp-danger); }
""".replace("__UI__", FONT_UI).replace("__READ__", FONT_READING).replace("__MONO__", FONT_MONO)

_GLOBAL_CSS = _GLOBAL_CSS.replace("</style>", _COMPONENT_CSS + "</style>")


def inject_global_css() -> None:
    """Inject the shared design-system CSS into the current Streamlit page."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def apply_plotly_theme() -> None:
    """Optional: make every Plotly chart match the dark reading theme.
    Call once at the top of a page that draws Plotly charts."""
    try:
        import plotly.io as pio
    except ImportError:
        return
    t = TOKENS
    tpl = pio.templates["plotly_dark"]
    tpl.layout.update(
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font=dict(family="Atkinson Hyperlegible, Segoe UI, sans-serif", color=t["ink_reading"]),
        colorway=[t["success"], t["warning"], t["danger"], t["info"], "#b4a0cc"],
        xaxis=dict(gridcolor=t["border"], zerolinecolor=t["border"]),
        yaxis=dict(gridcolor=t["border"], zerolinecolor=t["border"]),
    )
    pio.templates["etp"] = tpl
    pio.templates.default = "etp"


def inject_quill_dark_mode():
    """
    Injects JavaScript to programmatically style the Quill iframe for dark mode.
    This works by accessing the iframe's contentDocument and appending a <style> tag.
    """
    t = TOKENS
    css = f"""
          @import url('{_FONTS_URL}');
          .ql-editor {{
            background: {t['surface_sunken']} !important;
            color: {t['ink_reading']} !important;
            caret-color: {t['accent']} !important;
            font-family: Literata, Georgia, serif !important;
            font-size: 16px !important;
            line-height: 1.7 !important;
            min-height: 140px;
          }}
          .ql-toolbar {{
            background: {t['surface']} !important;
            border: 1px solid {t['border']} !important;
            border-bottom: none !important;
            border-radius: 10px 10px 0 0 !important;
          }}
          .ql-container {{
            border: 1px solid {t['border']} !important;
            border-radius: 0 0 10px 10px !important;
          }}
          .ql-stroke {{ stroke: {t['ink_muted']} !important; }}
          .ql-fill {{ fill: {t['ink_muted']} !important; }}
          .ql-picker {{ color: {t['ink_muted']} !important; }}
          .ql-toolbar button:hover .ql-stroke, .ql-toolbar .ql-active .ql-stroke {{ stroke: {t['accent']} !important; }}
          .ql-toolbar button:hover .ql-fill, .ql-toolbar .ql-active .ql-fill {{ fill: {t['accent']} !important; }}
          .ql-picker-options {{ background: {t['surface_raised']} !important; border-color: {t['border']} !important; }}
          .ql-editor.ql-blank::before {{
            color: {t['ink_faint']} !important;
            font-style: italic;
          }}
          .ql-editor ::selection {{ background: rgba(140,194,159,.28) !important; }}
          .ql-editor code, .ql-editor pre {{ background: {t['surface']} !important; color: {t['ink']} !important; }}
          body {{ background: transparent !important; }}
    """
    js = r"""
    <script>
    const QUILL_CSS = __CSS__;
    function styleQuillIframe(){
      const iframe = window.parent.document.querySelector('iframe[title="streamlit_quill.st_quill"]')
                  || document.querySelector('iframe[title="streamlit_quill.st_quill"]');
      if(!iframe) return;
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        if(!doc || !doc.head) return;
        if (doc.getElementById('quill-dark-style')) return;
        const style = doc.createElement('style');
        style.id = 'quill-dark-style';
        style.innerHTML = QUILL_CSS;
        doc.head.appendChild(style);
      } catch(e) {
        console.warn('Could not inject styles into quill iframe (cross-origin?).', e);
      }
    }
    setTimeout(styleQuillIframe, 500);
    setTimeout(styleQuillIframe, 1500);
    try {
      new MutationObserver(styleQuillIframe).observe(window.parent.document.body, { childList: true, subtree: true });
    } catch(e) {
      new MutationObserver(styleQuillIframe).observe(document.body, { childList: true, subtree: true });
    }
    </script>
    """.replace("__CSS__", json.dumps(css).replace("</", "<\\/"))
    components.html(js, height=0, width=0)
