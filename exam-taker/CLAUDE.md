# Exam Taker Pro — rules for Claude Code

## Goal
UI-only redesign of the Streamlit desktop app. Follow:
- design-system/DESIGN_SYSTEM.md  (tokens, type, icons, rules)
- design-system/pages.md          (page-by-page UI)
- design-system/IMPLEMENTATION_PLAN.md (batches, tests, gates)

## Hard rules
- Do NOT change logic in utils/*.py (except utils/ui_helpers.py and new utils/ui_components.py).
- Do NOT change: file_manager / srs / scoring / bookmark_manager / archive_manager calls,
  process_daily_session, handle_submission, JSON formats, file paths.
- Keep every widget `key=` exactly as it is (session state depends on them).
- Keep st.radio return values as letters ("A","B",...). Show option text with `format_func`.
- Colours only from `ui_helpers.TOKENS`. No emoji in labels; use `icon=":material/<name>:"`.
- Never touch: questions/, logs/, bookmarks/, archives/, user_data/, exam-taker-mobile/, env/.

## Way of working (TDD)
1. Write / update the test first (tests/). Run it: it must FAIL for new UI behaviour.
2. Change the UI code. Run the FULL suite: `python -m pytest -q`.
3. Characterization tests (tests/test_logic_*.py) must never be edited to make them pass.
4. One batch = one commit. Show the diff before committing.
5. Tests run in a temp copy of tests/fixtures/workspace (never real data).

## Commands
```powershell
env\Scripts\activate
python -m pytest -q                 # all tests
python -m pytest -q -m smoke        # page load only
streamlit run app.py                # manual check
```
