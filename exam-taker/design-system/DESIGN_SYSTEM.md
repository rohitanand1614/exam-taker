A calm, dark, book-like interface for long exam practice sessions. Text first, colour only for meaning.

## Principles

- **Reading comes first**
  - Question, options and explanation use a reading serif (`reading` family, Literata).
  - Controls use a clear sans (`ui` family, Atkinson Hyperlegible).
  - *Literata was designed for e-book reading; Atkinson Hyperlegible was designed for low-vision legibility.*
- **Dark, but not black**
  - Page `bg`, cards `surface`. Never `#000`.
  - Text is warm off-white (`ink`, `ink-reading`), never pure white.
  - *Pure white on pure black causes glare and "halo" on long reads.*
- **Colour = meaning only**
  - Green `success` = correct. Orange `warning` = partial / missed / retry. Terracotta `danger` = wrong / hard reset.
  - Blue `info` = explanation and due dates.
  - Everything else is neutral.
- **One primary action per screen**
  - Only *Submit answer* or *Next* is filled (`accent-fill`).
- **Same place, every time**
  - Actions sit in the same spot on every question, so the eye does not search.

## Content rules

- Plain, short English. Sentence case: "Submit answer", not "SUBMIT ANSWER".
- Calm feedback: "Correct", "Partly correct", "Not correct". Not "Wrong!".
- No emoji in titles, buttons or labels. Use icons (see Iconography).
- Numbers as digits: "Question 12 of 40".
- Uppercase only for `label` style overlines.
- **One label rule set** (all 13 pages, checked by `tests/test_label_rules.py`):
  - Sentence case everywhere ("Select exam", not "Select Exam"). No trailing colons.
  - One verb for revealing an answer: **Show answer** (never "View answer" / "Review answer").
  - Archive pages use **Restore**, and the toast says "Restored." (same word).
  - The page head title equals the navigation title; descriptive text goes in the subtitle.
  - Buttons that return to Topic analysis say **Back to topic analysis** (never "dashboard").
  - Option values the page logic compares (for example "Ever Incorrect") are values, not labels, and keep their case.

## Colour

### Themes

- **Slate Night** (`slate`) — default, cool neutral grey.
- **Sepia Night** (`sepia`) — warmer, for late-night sessions.
- *Both are dark. Only the tint changes; every rule below is the same.*

### Surfaces (dark → light)

- `surface-sunken` — sidebar, code.
- `bg` — page.
- `surface` — cards, lists, tiles.
- `surface-raised` — hover, inputs, open menus.

### Text

- `ink` — titles, question stem, button labels.
- `ink-reading` — options, explanations, notes.
- `ink-muted` — tags, captions, meta.
- `ink-faint` — hints, shortcut keys only. Not on `surface-raised`.

### Status

- Each status has three tokens: text (`success`), ground (`success-bg`), edge (`success-border`).
- Always pair a status colour with an icon AND a word.
  - *Green and terracotta differ mainly in hue. The icon + word keeps it readable for colour-blind users.*

### Bookmark colours (exact hex)

| Bookmark | Short name | Hex |
| --- | --- | --- |
| Important (Red) | Important | `#d48a80` |
| Review Later (Orange) | Review later | `#d6a464` |
| Interesting (Blue) | Interesting | `#8ea9cc` |
| Hard (Purple) | Hard | `#b4a0cc` |
| Solved (Green) | Solved | `#8cc29f` |

- **BookmarkChip** = filled dot in the bookmark colour + short name. No emoji, no colour-only meaning.
- In the question card the popover holds five chips (single choice, `st.pills`); the header chip shows the dot and
  name once saved ("Bookmark" before). The same chips filter the Bookmarks page.
- The dot colours come from `.streamlit/config.toml`. Streamlit lightens `<name>Color` for text on a dark theme, so
  the exact hex is set twice: `<name>Color` and `<name>TextColor` (red, orange, blue, violet, green).
  The stored value is still the `BOOKMARK_COLORS` key ("Important (Red)").

### Contrast (checked in both themes)

- `ink` on any surface: 11.5:1 or more.
- `ink-reading`: 9.6:1 or more. `ink-muted`: 5.5:1 or more.
- Status text on its own `-bg`: 6.7:1 or more.
- `border-strong` (control edges) on `surface`: 3.1:1 or more.

## Type

| Style | Use |
| --- | --- |
| `question` | Question stem — Literata 20/32, 500 |
| `option` | Answer options — Literata 17/27 |
| `reading` | Explanation, notes — Literata 17/29 |
| `page-title` | One per page |
| `section` | Section heading |
| `ui` / `ui-strong` | Buttons, inputs, nav |
| `meta` | Tags, dates, captions |
| `label` | Uppercase overline |
| `stat` | Dashboard numbers |
| `code` | Code, keyboard keys |

- **Fonts work offline.** Literata, Atkinson Hyperlegible and JetBrains Mono (woff2) and KaTeX 0.16.11 are bundled
  in `static/` and served by the app at `/app/static/...`. Nothing is requested from Google Fonts or a CDN at run
  time. Rebuild the files with `python tools/fetch_assets.py` (licences are saved next to the fonts).
- Max line length `measure` (68ch) for all reading text.
  - *45–75 characters per line is the comfortable reading range.*
- Never centre long text. Left-align.

## Spacing, radius, size

- Steps: `space-1` 4 → `space-7` 48. Card padding `space-5`; options gap `space-3`.
- Radius: `radius-sm` badges · `radius-md` buttons, options · `radius-lg` cards · `radius-pill` chips, bars.
- `target` 44px — minimum height for anything clickable.
- Borders separate things; `shadow-card` only on the question card.

## States

- Hover: `surface-raised` ground.
- Focus: 2px solid `accent` ring, 2px offset (7:1+ on every surface).
- Disabled: 45% opacity, no hover.
- Selected option: `selected-bg` + `accent` edge.

## Iconography

- Line icons, 1.75 stroke, 18px, colour = text colour.
- In Streamlit use **Material Symbols Rounded** via `icon=":material/name:"`.
  - *Previews here use simple stand-in line icons drawn for this system; in the app use the Material names below.*

| Action | Material name |
| --- | --- |
| Previous / Next | `chevron_left` / `chevron_right` |
| Submit | `check` |
| Simple retry | `replay` |
| Hard retry | `restart_alt` |
| Bookmark | `bookmark` / `bookmark_added` |
| Archive / Unarchive | `archive` / `unarchive` |
| Explanation | `lightbulb` |
| Notes / Diagram | `edit_note` / `account_tree` |
| Due date | `schedule` |
| Exam | `menu_book` |
| Targeted drill | `target` |
| Regressive practice | `sync` |
| Wrong answers | `cancel` |
| Search | `search` |
| Progress | `bar_chart` |
| Topic analysis | `psychology` |
| Similar questions | `content_copy` |

## Navigation

- **Top navigation** (`st.navigation(..., position="top")`): four groups, each a dropdown.
  - Practice: Exam · Targeted drill · Regressive practice · Practice incorrect · Practice bookmarks
  - Review: Wrong answers · Bookmarks · Notes review · Search
  - Insights: Progress · Topic analysis
  - Manage: Similar questions · Archived
- All 13 pages fit on one row at 1280 px wide and up. The sidebar holds only page-specific controls.

## Keyboard (exam pages)

| Key | Action |
| --- | --- |
| `1`–`9` or `A`–`H` | choose that option (toggles it on "select all that apply") |
| `Enter` | Submit answer |
| `N` or `→` | Next |
| `P` or `←` | Previous |
| `Shift+B` | open the bookmark popover (plain `B` is the answer letter B) |

- Ignored while typing in a text box, the notes editor or a dropdown, and when Ctrl / Alt / Cmd is held.
- Key chips on the buttons (`↵`, `N`, `P`) are the reminder; they are drawn by CSS, so the button labels do not change.
- Keys wait for Streamlit to finish a rerun (a condition, not a timer), and a key with nothing to click is dropped
  once the page is idle.

## Using this in the Streamlit app

- Put colours and fonts in `.streamlit/config.toml` (theme), then keep a small CSS file for the rest.
- Use `st.container(key="name")` → style `.st-key-name`. Avoid `nth-of-type` selectors.
- Full page-by-page plan: **Pages** section. Technology fit: **Technology** section.

```toml
# .streamlit/config.toml  (Slate Night)
[theme]
base = "dark"
backgroundColor = "#15171a"
secondaryBackgroundColor = "#1c1f23"
textColor = "#e6e1d8"
primaryColor = "#8cc29f"   # accent: radio dot, focus, sliders
linkColor = "#8cc29f"
borderColor = "#2c3136"
baseRadius = "10px"
greenColor = "#8cc29f"
orangeColor = "#d6a464"
redColor = "#d48a80"
blueColor = "#8ea9cc"
violetColor = "#b4a0cc"
# text variants: without these Streamlit lightens the colours above for text on a dark theme
greenTextColor = "#8cc29f"
orangeTextColor = "#d6a464"
redTextColor = "#d48a80"
blueTextColor = "#8ea9cc"
violetTextColor = "#b4a0cc"

[server]
enableStaticServing = true   # serves ./static (fonts, KaTeX) at /app/static/

[theme.sidebar]
backgroundColor = "#111316"
```

```css
/* primary button = accent-fill, not the bright accent */
button[kind="primary"] { background:#35553f; border-color:#35553f; color:#eef4ef; }
```

## CHANGES

- **v1.0** (`ui-v1`, batches 0–8): Slate Night theme and tokens, shared components, redesigned Exam, practice, drill
  and regressive pages, review and insight pages, grouped `st.navigation`, no emoji, `st.container(key=...)` hooks.
- **v1.1** (`ui-v1.1`, batch 9):
  - Top navigation with four dropdown groups.
  - One label rule set (sentence case, no trailing colons, "Show answer", "Restore", "Back to topic analysis"),
    with the page head equal to the nav title.
  - Keyboard shortcuts on the five exam pages, with key chips on Submit / Next / Previous.
  - Topic analysis "Generate analysis" and "Refresh analysis" now run after an empty cache load.
- **v1.2** (`ui-v1.2`, batches 10a / 10a.1): bookmark chips (coloured dot + short name) in the question card and the
  drill, in the exact hex above; toast says "Bookmarked as Important."; AppTest patch moved to
  `tests/plugins/pills_patch.py`.
- **v1.2.x** (batch 10b, `ui-v1.3`):
  - Keyboard script waits by condition: a key is no longer lost when a rerun is slow.
  - Fonts and KaTeX bundled in `static/` (no CDN); `tools/fetch_assets.py` rebuilds them.
  - "All done for today" card on the Exam page; drill finish screen with Answered / Correct / Accuracy tiles.
