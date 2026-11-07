# Implementation plan — UI redesign (test-driven, batch by batch)

## Status (final)

**Batches 0-8 are DONE.** Final suite: **756 passed, 4 skipped** (`python -m pytest -q`); every test file also
passes when run on its own. Entry point: `streamlit run main.py` (grouped `st.navigation`).

| Batch | What | Status |
| --- | --- | --- |
| 0 | Safety net: fixtures, characterization + smoke + flow tests | done |
| 1 | Global theme, tokens, Plotly theme, Quill dark mode, alert styling | done |
| 2 | Shared UI components (`utils/ui_components.py`) | done |
| 3 | Exam page redesign, `md_safe`, keyed containers | done |
| 4 | Shared `exam_view`, practice pages, Targeted drill, Regressive practice | done |
| 5 | Review / list pages, LaTeX repair, `tools/repair_latex_data.py` | done |
| 6 | Insights: Progress dashboard, Topic analysis, chart theme | done |
| 7 | Similar questions management | done |
| 8 | Test isolation, grouped navigation (`main.py`), chrome + label consistency, release checks | done |
| 9 | Keyboard shortcuts | optional, not started |

### Known follow-ups
- **Topic analysis, "Generate Analysis" button:** it only appears to work when loading the cached analysis *raises*.
  A load that returns an empty result stores a falsy value under the page's session key, so the next run skips the
  generate block. Frozen in `tests/test_insights_flow.py`; behaviour deliberately not changed.
- **`questions/genai-llm-books/Hands-On Large Language Models/Chapter4.json` is empty (0 bytes)** and is skipped by
  every loader and by `tools/repair_latex_data.py`. Restore its content from the source.
- **Keyboard shortcuts** (Batch 9) are not implemented.
- **Sidebar height:** the 13-item navigation plus a page's own sidebar controls is taller than a 1000 px screen; the
  controls (for example "Start new session") need a scroll. Options: move page controls into the main area, or use
  `st.navigation(position="top")`.
- **Label wording:** see the "Other inconsistent labels" list in the Batch 8 report: Title Case sidebar/filter labels,
  three names for "show the answer", "dashboard" in two buttons that go to Topic analysis, nav title vs page-head wording.
- **Bare `pytest`** cannot import the isolation plugin; use `python -m pytest`.
- **Unfixed data:** `tools/repair_latex_data.py` was applied once (5 strings, 1 file; `.bak` kept). Run its dry-run
  after adding new question files.

## Principles
- Logic is frozen. Only render code changes.
- Tests first. Every batch: red → green → full suite → manual check → commit.
- Small batches, each one revertible with `git revert`.
- Tests never touch real data (temp copy of fixtures).

---

## Batch 0 — Safety net (no UI change)

### 0.1 Baseline
- Commit current code (see commit commands in chat).
- `git tag ui-baseline`
- Backup: copy `logs/`, `bookmarks/`, `archives/`, `user_data/` to `F:\exam-backup\<date>\`.
- Pin `streamlit==1.51.0` and add `pytest`, `playwright` in `requirements-dev.txt`.

### 0.2 Test harness
```
tests/
  conftest.py              # adds exam-taker/ to sys.path; `workspace` fixture
  fixtures/workspace/
    questions/sample/sample.json   # 3 questions: single, multi-select, LaTeX
    logs/attempts/                 # 1 existing log (for "reattempt" / due)
    bookmarks/registry.json
    archives/registry.json
  test_logic_scoring.py    # characterization
  test_logic_srs.py
  test_logic_files.py      # load_questions, save_attempt_log, delete_last_attempt, reset
  test_logic_daily.py      # process_daily_session 48h / 24h rules
  test_pages_smoke.py      # every page loads, no exception
  test_exam_flow.py        # behaviour contract of the exam page
  test_ui_*.py             # new UI expectations (added per batch)
  visual/shoot.py          # Playwright screenshots
```
- `workspace` fixture: copy `fixtures/workspace` → `tmp_path`, `monkeypatch.chdir(tmp_path)`.
  - *All utils use relative paths (`Path("questions")`, `Path("logs/attempts")`, `Path("bookmarks")`), so chdir isolates data.*
- Fixture question shape = real files: `id`, `question`, `type`, `options` ("A) ..." prefixed), `correct_indices`, `explanation`, `tags`, `difficulty`.

### 0.3 Characterization tests (lock current behaviour)
- scoring: F1 values for exact / partial / wrong / empty.
- srs: `update_srs` for quality 0..5 from initial state.
- files: attempt log written, summary counts, last-attempt delete, hard reset.
- daily session: correct <48h skipped; bookmarked kept; archived removed; reattempt flag.
- **Rule: these files are never edited after Batch 0.**

### 0.4 Exam flow contract (Streamlit AppTest, headless)
```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=30).run()
at.sidebar.selectbox[0].select("sample").run()
at.radio(key="radio_Q1").set_value("B").run()
at.button(key="btn_Q1").click().run()
# assert logs/attempts/Q1.log.json exists, score == 1.0
# Simple retry  -> key "retry_Q1"      -> last attempt removed
# Hard retry    -> key "hard_retry_Q1" -> history reset
# Bookmark      -> key "bm_btn_Q1"     -> bookmarks/registry.json has Q1
# Archive       -> key "arch_btn_Q1"   -> archives/registry.json has Q1
# Next / Prev   -> keys nav_next*, nav_prev* -> current_q_index changes
```
- Same contract file for Practice_Incorrect, Practice_Bookmarks, Targeted_Drill, Regressive_Practice.
- **Gate 0:** all green on untouched code. Commit "tests: safety net".

---

## Batch 1 — Global theme (DONE, verify)
- Files: `utils/ui_helpers.py`, `.streamlit/config.toml`.
- Tests: smoke + flow green; `ui_helpers` public functions unchanged
  (`prepare_math_text`, `render_math_text`, `inject_global_css`, `inject_quill_dark_mode`).
- Visual: screenshots of all 13 pages → review.
- **Gate 1:** commit "ui: theme + global css".

## Batch 2 — Shared UI components (new file, no page changes yet)
- New `utils/ui_components.py`: `badge()`, `meta_row()`, `feedback_banner()`, `explanation()`,
  `option_label()` (strips "A) " prefix), `page_head()`, `stat_tiles()`, `status_legend()`.
- Pure functions returning HTML strings / calling st.* → unit-test each (input → expected HTML).
- **Gate 2:** unit tests green; nothing else changed.

## Batch 3 — Exam page (`app.py`), the core
Write failing UI tests first (`test_ui_exam.py`):
- no emoji in any button label;
- radio options show option text (via `format_func`), values still letters;
- difficulty / reattempt / due shown as badges;
- explanation rendered with `st.markdown` (not `components.html`);
- after submit: no separate "Analysis" list; option rows show Correct / Missed / Your pick;
- bookmark + archive still reachable with same keys.

Then change only `render_question()` / `render_results()` drawing code.
- **Gate 3:** UI tests + flow contract + logic tests green → manual 10-question run → commit.

## Batch 4 — Practice clones (4 files)
- Practice_Incorrect, Practice_Bookmarks, Targeted_Drill, Regressive_Practice.
- Option A (safer first): apply same changes file by file.
- Option B (later): extract shared `render_exam_card()` — only after Batch 4 A is green.
- One commit per file. **Gate 4** per file.

## Batch 5 — Review / list pages
- Wrong_Answers, Bookmarks, Archived_Questions, Search_Questions, Notes_Review.
- Tests: counts in page head, filters work (AppTest set multiselect/pills), Unarchive/Remove keys unchanged.

## Batch 6 — Insights
- Progress_Dashboard, Topic_Analysis: `apply_plotly_theme()`, stat tiles.
- Tests: page loads with fixture logs; charts present (`at.get("plotly_chart")`).
- Topic_Analysis LLM call: mock `utils.llm_client` in tests (no network, no cost).

## Batch 7 — Manage
- Similar_Questions_Management: scan button, group cards. Mock `similarity` heavy work in tests.

## Batch 8 — Navigation (structural, last)
- New entry with `st.navigation` groups + Material icons; fix `st.page_link` targets.
- Tests: every page reachable (AppTest `switch_page`), default page = Exam.
- **Gate 8:** full suite + all-page visual review → tag `ui-v1`.

## Batch 9 — Keyboard shortcuts (optional)
- Add small shortcut component; test that it does not break flow tests.

---

## Every batch — checklist
```text
[ ] tests written first, seen failing
[ ] code changed (UI only)
[ ] python -m pytest -q  -> all green
[ ] streamlit run app.py -> manual check (one real exam, 5 questions)
[ ] screenshots reviewed (tests/visual/shoot.py)
[ ] git diff reviewed: no utils logic / key= / path changes
[ ] commit "ui(batch N): ..."
```

---

## Risks and mitigations
| Risk | Mitigation |
| --- | --- |
| Logic accidentally changed | Characterization tests frozen; diff review for utils/ |
| Widget key renamed → state lost | Flow tests use keys; rule in CLAUDE.md |
| Radio values change → scoring breaks | Keep letters as values; `format_func` for text |
| Real data overwritten in tests | `workspace` fixture + chdir to tmp |
| Same code in 4 files drifts | Batch 4 per file, then optional extract |
| LaTeX in radio labels renders differently | Fixture has LaTeX question; visual check |
| HTML inside option text | `option_label()` escapes / falls back |
| Streamlit internal CSS selectors change | Pin version; selectors only in ui_helpers |
| AppTest can't run custom components (quill, mermaid) | Treated as unknown elements; assert only around them |
| LLM / similarity calls slow or paid | Mock in tests |
| `sync_to_github.py` commits mid-batch | Don't run sync during a batch |
| Offline: fonts / KaTeX CDN | Fallback fonts OK; later self-host via `static/` |
