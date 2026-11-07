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
orangeColor = "#dcae6e"
redColor = "#e0968a"
blueColor = "#93aecf"

[theme.sidebar]
backgroundColor = "#111316"
```

```css
/* primary button = accent-fill, not the bright accent */
button[kind="primary"] { background:#35553f; border-color:#35553f; color:#eef4ef; }
```
