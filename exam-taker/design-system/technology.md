# Technology

## Current stack

- Streamlit 1.51 (Python), multipage `pages/` folder.
- `streamlit-quill` (notes), `streamlit-mermaid` (diagrams), Plotly / Altair charts.
- Custom CSS + JS injected from `utils/ui_helpers.py`.
- Option / explanation text drawn in `components.html` iframes for KaTeX.

## Verdict

- **Yes — Streamlit can carry about 80–85% of this design.** Start here.
- *Logic, files and SRS stay untouched; only `app.py` / `pages/*.py` render code and `ui_helpers.py` change.*

## What Streamlit 1.51 already gives

| Need | Streamlit feature |
| --- | --- |
| Dark palette | `.streamlit/config.toml` `[theme]` + `[theme.sidebar]` |
| Status colours | `greenColor`, `orangeColor`, `redColor`, `blueColor` (+ `…BackgroundColor`, `…TextColor`) |
| Rounded corners | `baseRadius`, `buttonRadius` |
| Custom fonts | `font`, `headingFont`, `codeFont`, `[[theme.fontFaces]]` |
| Grouped nav + icons | `st.navigation({...})` + `st.Page(icon=":material/…:")` |
| Quiet buttons | `st.button(type="primary" / "secondary" / "tertiary", icon=…)` |
| Clean CSS hooks | `st.container(key="x")` → `.st-key-x` class |
| Bookmark chips | `st.pills`, `st.segmented_control` |
| Cards | `st.container(border=True)` |
| LaTeX without iframes | `st.markdown` and widget labels support `$…$` |

## What needs extra work

- **Whole-row clickable options** — `st.radio` with full option text as labels + CSS to make each label a bordered row.
- **Correct / missed / wrong row colours after submit** — render options as HTML rows (`st.markdown`) once submitted.
- **Keyboard shortcuts** — small add-on package (for example `streamlit-shortcuts`) or one `components.html` script.
  - *Check the package's last release before adding it.*
- **Quill dark mode** — keep the current iframe style injection; update colours to tokens.

## Steps (low risk order)

1. Add `config.toml` theme + fonts. *(No code change; instant big win.)*
2. Replace `_GLOBAL_CSS` in `ui_helpers.py` with token-based CSS.
3. Switch to `st.navigation` groups; remove emoji, add Material icons.
4. Exam page: native Markdown for stem/explanation; OptionCard radio; keyed action bar.
5. Review pages: shared list layout + chip filters.
6. Dashboards: one Plotly template for all charts.

```python
# utils/ui_helpers.py — one Plotly template for every chart
import plotly.io as pio
pio.templates["etp"] = pio.templates["plotly_dark"]
pio.templates["etp"].layout.update(
    paper_bgcolor="#1c1f23", plot_bgcolor="#1c1f23",
    font=dict(family="Atkinson Hyperlegible", color="#d5cfc4"),
    colorway=["#8cc29f", "#dcae6e", "#e0968a", "#93aecf"])
pio.templates.default = "etp"
```

## If you want more than Streamlit can give

### Option A — NiceGUI (recommended next step)

- Python, so `utils/` imports work as-is.
- No full-page rerun → no flicker; real keyboard events; full CSS / Tailwind control.
- Desktop window via `ui.run(native=True)`.
- Effort: rewrite page files only (~1–2 weeks for 13 pages).

### Option B — FastAPI + React (Vite, Tailwind) + Tauri or pywebview

- Best possible UI and speed; true desktop app.
- `utils/` becomes a small REST API.
- Effort: highest (~3–5 weeks). Two languages to maintain.

### Option C — Flet (Flutter in Python)

- Matches the existing Flutter mobile app look.
- Less mature for rich text, LaTeX and Mermaid.

### Pick

```text
Want quick, safe win           -> stay on Streamlit (steps 1–6)
Want no flicker + keyboard     -> NiceGUI, reuse utils/
Want product-grade desktop app -> FastAPI + React + Tauri
```

## Drawbacks and real-world notes

- Streamlit: every click reruns the script; large question files feel slower on each answer.
- Streamlit: internal `data-testid` names change between versions — pin the version in `requirements.txt`.
- Streamlit: iframes (`components.html`) cannot read the main page CSS, so each needs its own style.
- NiceGUI: smaller community; some widgets (rich text editor) need a third-party JS library.
- React stack: more moving parts (Node build, API server, packaging).
