# Pages

UI plan for all 13 pages. Only layout, text, icons and styling change. Every `file_manager`, `srs`, `scoring`, `bookmark_manager`, `archive_manager` call stays as it is.

## Whole app (do once)

- **Theme file** — add `.streamlit/config.toml` (see brand book). Removes most custom CSS.
- **Fonts** — Literata (reading), Atkinson Hyperlegible (UI), JetBrains Mono (code).
- **Navigation** — replace the flat page list with `st.navigation` groups: Practice · Review · Insights · Manage (see SidebarNav).
- **Emoji → icons** — remove emoji from all `st.title`, buttons, toasts. Use `icon=":material/…:"`.
- **Page head** — every page: title (`page-title`) + one muted line (what this page is / count).
- **Reading column** — exam-style pages: centred, max ~820px. Dashboards: full width.
- **CSS hooks** — wrap areas in `st.container(key=…)`, style `.st-key-…`. Delete the `nth-of-type` colour rules.
  - *`nth-of-type` breaks the moment a column is added or hidden (for example, when "Previous" is hidden on question 1).*

## 1. Exam (`app.py`) — most important

### Before submit

- Card header: difficulty Badge · Reattempt badge · Due chip · tags — right: icon tools (bookmark, archive).
- "Question 12 of 40" overline.
- Question stem in `question` style, native Markdown + LaTeX (no iframe).
- Options = one OptionCard per option. Whole row clickable. Letter key inside the row.
- Action bar: Previous (left) · **Submit answer** (right, primary).

### After submit

- FeedbackBanner at top: Correct / Partly correct · score / Not correct.
- Results shown on the same option rows (Correct · Missed · Your pick). Remove the separate "Analysis" list.
- ExplanationPanel — grows to fit, no fixed height.
- "My notes & diagram" in one collapsed expander.
- Action bar: Previous · Simple retry · Hard retry … **Next** (right).

### Sidebar

- Load by (segmented: Folder / File) → Exam (select) → Order (segmented: In order / Shuffled) → ProgressMeter.
- "View detailed stats" removed — Progress is in the nav.

### Empty / done states

- "All done for today" → calm card with check icon, count, and button "Choose another exam".
- No exam chosen → card: "Pick an exam in the sidebar to start."

## 2. Practice incorrect · 3. Practice bookmarks · 4. Targeted drill

- Same layout as Exam (reuse the same card + action bar code).
- Page head says what is in the queue: "23 questions you got wrong".
- Targeted drill: sidebar "Drill status" → ProgressMeter + "Exit drill" (ghost button).
- Finish screen: StatTile row (score, correct, time) + "Back to dashboard".

## 5. Regressive practice

- Same Exam card.
- Session stats → StatTile row above the card (Answered · Correct · Streak).
- "Start new session" primary; "End session" danger outline (never filled red).
- "View explanation" → ExplanationPanel, not an expander.

## 6. Wrong answers (Review mistakes)

- ReviewListScreen layout.
- Each row: question (2 lines), "wrong 3 times · last on 5 Nov", button **Practice**.
- Open row → card in review mode: your pick (danger), right answer (success), explanation.

## 7. Bookmarks · 8. Archived questions

- ReviewListScreen layout.
- Filters as chips at the top (bookmark colours / source), not sidebar multiselects.
- Counts in page head: "41 saved · showing 12".
- Row actions: Bookmarks → ghost Archive, Remove (click active chip). Archived → secondary **Restore**.

## 9. Notes review

- List of questions with notes; each opens to an ExplanationPanel-style block in `reading` style.
- "Reorganize contextually" = secondary button with `auto_awesome` icon.
- Export → secondary button in page head, not a buried expander.

## 10. Search questions

- Big search box in page head; filters (exam, difficulty) as one row under it.
- Results = ReviewListScreen rows; match words highlighted with `selected-bg`.
- "View answer" → expands row to show the right option in success style.

## 11. Progress dashboard

- DashboardScreen: tabs as segmented control → StatTile row → charts → question table.
- Charts: dark Plotly, `surface` background, status colours only for mastery bands.

## 12. Topic analysis

- StatTile row (topics, weak, mastered) → "Weak areas" bar chart → "Topic mastery" stacked bar → table.
- "Targeted drill" block: topic select + primary **Start drill**.
- Tag-to-topic mapping stays in an expander.

## 13. Similar questions management

- Sidebar: suite select, similarity slider, mode → "Start scan" primary.
- Each group = one card; questions side by side in columns, each with a checkbox.
- "Archive selected" = ghost button at group end; sticky count "3 selected".

## Keyboard (exam pages)

```text
1–4 / A–D   choose option
Enter       submit
→ / N       next
← / P       previous
B           bookmark
E           open explanation
```

- *Needs a small add-on in Streamlit — see Technology.*

## Drawbacks and caveats

- Streamlit reruns the page on each click — a short flicker stays even after the redesign.
- Radio labels with long LaTeX may wrap less nicely than custom HTML.
- Keyboard shortcuts are not built into Streamlit.
- Styling internal `data-testid` selectors can break on a Streamlit upgrade; keep them few and in one file.
