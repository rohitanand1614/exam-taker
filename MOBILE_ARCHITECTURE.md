# Exam-Taker App: Complete Architecture for Mobile Rebuild

> **Purpose:** One-stop reference for rebuilding this app as an Android (or any mobile) application. Covers every data structure, algorithm, business rule, and feature — excluding the Ollama/LLM AI features which are optional and clearly marked.

---

## 1. HIGH-LEVEL SYSTEM OVERVIEW

```
┌─────────────────── EXAM-TAKER SYSTEM ───────────────────────┐
│                                                              │
│   QUESTION BANK          PRACTICE ENGINE        USER STATE   │
│   (Read-Only JSON)  ──▶  (Quiz Loops)    ──▶  (JSON Files)  │
│   questions/             app, drill,           logs/         │
│   *.json                 bookmarks,            bookmarks/    │
│                          regressive            archives/     │
│                                                              │
│   REVIEW TOOLS           ANALYSIS TOOLS        EXPORT       │
│   Search, Bookmarks,     Progress, Topics,     PDF/Markdown  │
│   Archives, Notes        Wrong Answers         (notes)       │
└──────────────────────────────────────────────────────────────┘
```

**Core loop (one sentence):** Load questions from JSON → filter by SRS schedule → user answers → score with F1 → update SM-2 spaced-repetition state → persist to log file.

---

## 2. FOLDER & FILE STRUCTURE

```
exam-taker/
│
├── app.py                          ← Main daily practice page
│
├── pages/                          ← Feature pages (12 total)
│   ├── Regressive_Practice.py      ← Mastery drill (2-streak)
│   ├── Targeted_Drill.py           ← Adaptive drill (re-queue wrong)
│   ├── Practice_Bookmarks.py       ← Quiz bookmarked questions
│   ├── Practice_Incorrect.py       ← Quiz failing questions
│   ├── Progress_Dashboard.py       ← Green/Yellow/Red/Grey overview
│   ├── Wrong_Answers.py            ← Review mode (no quiz)
│   ├── Bookmarks.py                ← Bookmark CRUD
│   ├── Archived_Questions.py       ← Archive CRUD
│   ├── Search_Questions.py         ← Full-text search
│   ├── Notes_Review.py             ← View user notes + export
│   ├── Topic_Analysis.py           ← [USES AI] Tag-based analytics
│   └── Similar_Questions_Management.py  ← [USES AI] Duplicate detection
│
├── utils/
│   ├── file_manager.py             ← ALL disk I/O
│   ├── scoring.py                  ← F1 score + quality mapping
│   ├── srs.py                      ← SM-2 spaced repetition algorithm
│   ├── bookmark_manager.py         ← Bookmark registry CRUD
│   ├── archive_manager.py          ← Archive registry CRUD
│   ├── similarity.py               ← [USES AI] Duplicate detection
│   ├── topic_analyzer.py           ← [USES AI] Tag clustering
│   └── llm_client.py               ← [AI] Ollama/OpenAI adapter
│
├── questions/                      ← QUESTION BANK (read-only at runtime)
│   ├── nvidia-exam/
│   │   ├── Exam1/ *.json
│   │   └── Exam2/ ...
│   ├── 2026 LLM Job/
│   │   ├── Week1/ *.json
│   │   └── Week2/ ...
│   ├── CampusXDeepLearning-Basics/
│   └── ... (one folder per subject/course)
│
├── logs/
│   └── attempts/                   ← ONE FILE PER QUESTION
│       ├── question-id-001.log.json
│       └── ...
│
├── bookmarks/
│   └── registry.json               ← Single flat registry, all bookmarks
│
└── archives/
    └── registry.json               ← Single flat registry, all archived questions
```

---

## 3. DATA SCHEMAS

### 3a. Question JSON  (questions/**/*.json)

```json
[
  {
    "id": "Transformer_3B1B_Attention_001",
    "question": "What is the core problem that the attention mechanism solves in transformers?",
    "type": "multiple_choice",
    "options": [
      "A) Embeddings are too large and need compression",
      "B) Initial token embeddings are context-free lookup vectors...",
      "C) Token embeddings cannot represent rare words accurately",
      "D) Initial embeddings encode too much positional information"
    ],
    "correct_indices": [1],
    "tags": ["attention", "embedding", "transformer", "context"],
    "difficulty": "medium",
    "category": "conceptual",
    "explanation": "The core problem is that initial token embeddings are context-free..."
  }
]
```

**Field rules:**
- `correct_indices`: 0-based int array. `[1]` = single-select. `[0,2]` = multi-select.
- `type`: always `"multiple_choice"` (multi-select is inferred by `len(correct_indices) > 1`)
- `options`: text includes letter prefix (`"A) ..."`) — strip for clean display
- `difficulty`: `"easy"` | `"medium"` | `"hard"`
- `tags`: free-form array — used for topic filtering
- `explanation`: may contain LaTeX math (`$...$`, `\[...\]`, `\(...\)`)
- `question`: may contain LaTeX math

### 3b. Question Attempt Log  (logs/attempts/{sanitized_id}.log.json)

```json
{
  "summary": {
    "total_attempts": 3,
    "correct_count": 2,
    "wrong_count": 1,
    "avg_score": 0.833,
    "last_attempted_at": "2025-12-04T19:21:17.216106",
    "srs": {
      "repetitions": 2,
      "interval_days": 6,
      "ef": 2.6,
      "next_due": "2025-12-10"
    }
  },
  "attempts": [
    {
      "attempt_id": "20251204192117",
      "timestamp": "2025-12-04T19:21:17.216106",
      "selected_indices": [1],
      "score": 1.0,
      "quality": 5
    }
  ],
  "user_notes": "<p>HTML notes written by user</p>",
  "user_diagram": "graph TD; A-->B; B-->C;"
}
```

**Field rules:**
- Filename: sanitize `id` (replace `/`, `\`, spaces with `_`) + `.log.json`
- `summary.srs.ef`: float, minimum 1.3, default 2.5
- `summary.srs.repetitions`: count of consecutive successful reviews
- `summary.srs.interval_days`: days until next review
- `summary.srs.next_due`: ISO date `YYYY-MM-DD`
- `attempts[].quality`: int 0–5 (SM-2 scale). quality ≥ 3 = passed.
- `attempts[].score`: float 0.0–1.0 (F1 score)
- `user_notes`: HTML string or null
- `user_diagram`: Mermaid DSL string or null

### 3c. Bookmarks Registry  (bookmarks/registry.json)

```json
{
  "question-id-001": {
    "color": "Important (Red)",
    "data": { /* full question object snapshot */ },
    "timestamp": "2025-12-03T01:16:38.660317"
  }
}
```

**Color labels → emoji:**
```
"Important (Red)"       → 🔴
"Review Later (Orange)" → 🟠
"Interesting (Blue)"    → 🔵
"Hard (Purple)"         → 🟣
"Solved (Green)"        → 🟢
```

**Key:** Full question object is snapshotted (not a reference). Bookmarks survive question bank edits.

### 3d. Archives Registry  (archives/registry.json)

```json
{
  "question-id-002": {
    "data": { /* full question object snapshot */ },
    "timestamp": "2025-12-04T19:35:53.012831"
  }
}
```

---

## 4. CORE ALGORITHMS

### 4a. F1 Scoring  (scoring.py → `calculate_f1_score`)

Handles multi-select fairly — penalises both over-selection and under-selection.

```
inputs:  user_selected (list of int), correct (list of int)
output:  float 0.0–1.0

TP        = len(intersection(user_selected, correct))
Precision = TP / len(user_selected)  → 0 if nothing selected
Recall    = TP / len(correct)         → 0 if nothing correct
F1        = 2 * P * R / (P + R)       → 0 if P+R == 0
```

**Examples:**
| Correct | Selected | F1 |
|---------|----------|----|
| [1]     | [1]      | 1.0 ✅ |
| [1,2]   | [1]      | 0.667 (partial) |
| [1]     | [0]      | 0.0 ❌ |
| [1,2]   | [1,2,3]  | 0.8 (penalised extra) |

### 4b. Quality Mapping  (scoring.py → `score_to_quality`)

```
score == 1.0          → quality 5  (perfect)
0.8  ≤ score < 1.0    → quality 4  (good)
0.6  ≤ score < 0.8    → quality 3  (passing threshold)
0.4  ≤ score < 0.6    → quality 2
0.2  ≤ score < 0.4    → quality 1
score < 0.2           → quality 0  (blackout)
```

quality ≥ 3 = SRS advances. quality < 3 = SRS resets.

### 4c. SM-2 Spaced Repetition  (srs.py → `update_srs`)

**Initial state for every new question:**
```json
{ "repetitions": 0, "interval_days": 0, "ef": 2.5, "next_due": "today" }
```

**Update algorithm (run after each attempt):**
```
if quality >= 3:         # passed
    if repetitions == 0:
        interval_days = 1
    elif repetitions == 1:
        interval_days = 6
    else:
        interval_days = round(interval_days * ef)
    repetitions += 1
else:                    # failed — reset streak
    repetitions = 0
    interval_days = 1

ef = ef + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
ef = max(1.3, ef)        # floor

next_due = today + interval_days
```

**EF delta by quality:**
| quality | EF change |
|---------|-----------|
| 5 | +0.10 |
| 4 | +0.00 |
| 3 | -0.14 |
| 2 | -0.32 |
| 1 | -0.54 |
| 0 | -0.80 |

---

## 5. DAILY SESSION BUSINESS RULES

Applied only in the **main daily practice** screen. Drill / Bookmarks / Incorrect modes skip these.

### Rule 1 — Archive Skip
```
IF question.id in archives → SKIP (never show)
```

### Rule 2 — 48-Hour Cooldown (non-bookmarked only)
```
IF question is NOT bookmarked
AND last_correct_attempt_time < 48 hours ago
→ SKIP
```

### Rule 3 — Anti-Cram 24-Hour Lock
```
IF count(correct attempts in last 1 hour) >= 4
AND last_correct_attempt_time < 24 hours ago
→ SKIP (regardless of bookmark)
```

### Rule 4 — Reattempt Badge
```
IF attempted today AND NOT correct today
→ show "reattempt" badge on question (no filtering — still shown)
```

---

## 6. FEATURE MODULES

### 6a. Main Daily Practice

```
Screen flow:
  SELECT DECK
    ↓
  FILTER (apply rules 1-4) → build session queue
    ↓
  FOR each question in queue:
    SHOW question + options
    USER submits answer
      → score (F1) → quality → SRS update → save log
    SHOW result + explanation + navigation
      ↓ Simple Retry       → delete last attempt → re-show
      ↓ Hard Retry         → reset entire log → re-show
      ↓ Previous / Next    → navigate queue
  ALL DONE screen (when queue empty)
```

**Bookmark controls (during quiz):**
- Add: pick color → snapshot question → write registry
- Remove: delete by q_id from registry
- Change color: remove + re-add

**Archive control:**
- Archive → snapshot question → write archives registry → question disappears

**Notes/Diagrams (after answer submit):**
- Rich text editor → HTML stored in `user_notes`
- Mermaid code editor → DSL stored in `user_diagram`

---

### 6b. Regressive Practice (2-Streak Mastery)

No disk writes. Purely in-memory.

```
LOAD all questions from a single file → queue[]
LOOP until queue empty:
    PICK random question from queue
    USER answers
    if score == 1.0:
        streak[q_id]++
        if streak[q_id] >= 2: REMOVE from queue
    else:
        streak[q_id] = 0
DONE: show "All mastered!" stats
```

---

### 6c. Targeted Drill (Adaptive Re-queue)

Writes attempts to disk. Re-queues wrong answers.

```
RECEIVE drill_questions[] (from Topic Analysis, or manual selection)
step_key = f"{q_id}_{position_index}"  ← unique per drill slot

FOR each question (position grows as wrong answers re-queue):
    SHOW question
    USER submits
    SAVE attempt log (with drill_mode=true)
    UPDATE SRS
    if score < 1.0:
        APPEND copy of question to END of list
DONE when position reaches end of (growing) list
```

---

### 6d. Practice Bookmarks

```
USER selects source folder + colors filter
FILTER:
    for each question in source:
        if q.id in bookmarks AND bookmark.color in selected_colors:
            include
PRACTICE filtered list (identical quiz loop to Daily Practice)
Writes attempts + SRS updates to disk.
```

---

### 6e. Practice Incorrect

```
FILTER:
    for each question in source:
        load log
        if wrong_count >= correct_count (historically struggling)
        OR last_attempt.score < 1.0 (most recent failure)
        AND NOT archived:
            include
PRACTICE filtered list (identical quiz loop to Daily Practice)
```

---

### 6f. Progress Dashboard

```
For each question in selected source:
    load log
    no attempts      → GREY  (Unattempted)
    wrong_count == 0 → GREEN (Mastered — all correct)
    correct_count > 0 AND wrong_count > 0 → YELLOW (Mixed)
    correct_count == 0 → RED (Struggling — all wrong)

Display 4 tabs with question lists.
Read-only.
```

---

### 6g. Wrong Answers Review

```
Filter mode "Last Attempt Incorrect":
    last_attempt.score < 1.0 → include

Filter mode "Ever Incorrect":
    summary.wrong_count > 0 → include

DISPLAY each question:
    correct options → green
    user's wrong selection → red
    user's correct selection → green ✓
Read-only. No quiz interaction.
```

---

### 6h. Bookmarks Management

```
LIST: read registry, filter by color + source file, paginate 5/page
DELETE: remove entry from registry JSON
ARCHIVE: remove from registry + add to archives registry
```

---

### 6i. Archived Questions

```
LIST: read registry, filter by source file, paginate 10/page
RESTORE: remove entry from archives registry
         (question automatically returns to active pool)
```

---

### 6j. Search

```
INPUTS: folder filter, file filter, keyword
FOR each question in scope:
    if keyword (case-insensitive) in question.text
    OR in any option
    OR in explanation:
        include
Cap at 200 results.
Read-only.
```

---

### 6k. Notes Review

```
FOR each question in source:
    load log
    if user_notes (non-empty HTML) OR user_diagram (non-empty mermaid):
        include

DISPLAY: question, notes (rendered HTML), diagram (Mermaid)

EXPORT:
    Markdown: strip HTML tags → "## Q: {question}\n{clean_notes}\n---"
    PDF: same stripping + encode latin-1 safe
```

---

## 7. FILE I/O OPERATIONS REFERENCE

| Operation | Reads | Writes | Notes |
|-----------|-------|--------|-------|
| List exam folders | `questions/**` dirs | — | Scan for dirs containing .json |
| List exam files | `questions/**/*.json` | — | Recursive glob |
| Load questions | `*.json` file | — | Injects `source_file` field at load |
| Load question log | `logs/attempts/{id}.log.json` | — | Returns empty default if missing |
| Save attempt | `{id}.log.json` | `{id}.log.json` | Appends attempt, recalcs summary, updates SRS |
| Delete last attempt | `{id}.log.json` | `{id}.log.json` | Pops last item, recalcs summary |
| Reset question | — | — | **Deletes** the log file entirely |
| Save notes | `{id}.log.json` | `{id}.log.json` | Updates user_notes + user_diagram fields |
| Get all bookmarks | `bookmarks/registry.json` | — | Returns dict keyed by q_id |
| Add bookmark | `bookmarks/registry.json` | `bookmarks/registry.json` | Overwrites if q_id exists |
| Remove bookmark | `bookmarks/registry.json` | `bookmarks/registry.json` | |
| Check bookmark status | `bookmarks/registry.json` | — | Returns color label or null |
| Get all archives | `archives/registry.json` | — | Returns dict keyed by q_id |
| Archive question | `archives/registry.json` | `archives/registry.json` | Overwrites if already archived |
| Unarchive question | `archives/registry.json` | `archives/registry.json` | |
| Check archived | `archives/registry.json` | — | Returns bool |

**Log filename sanitization:**
```
safe_id = q_id.replace("/","_").replace("\\","_").replace(" ","_")
path    = "logs/attempts/" + safe_id + ".log.json"
```

---

## 8. MOBILE REBUILD GUIDANCE

### Recommended Data Layer (replace JSON files with SQLite/Room)

```sql
CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    source_file TEXT,
    question TEXT,
    type TEXT,
    options_json TEXT,           -- JSON array
    correct_indices_json TEXT,   -- JSON array of ints
    tags_json TEXT,              -- JSON array of strings
    difficulty TEXT,
    category TEXT,
    explanation TEXT
);

CREATE TABLE srs_state (
    question_id TEXT PRIMARY KEY,
    repetitions INTEGER DEFAULT 0,
    interval_days INTEGER DEFAULT 0,
    ef REAL DEFAULT 2.5,
    next_due TEXT                -- ISO date YYYY-MM-DD
);

CREATE TABLE attempts (
    id TEXT PRIMARY KEY,         -- YYYYMMDDHHmmss
    question_id TEXT,
    timestamp TEXT,              -- ISO 8601
    selected_indices_json TEXT,
    score REAL,
    quality INTEGER
);

CREATE TABLE bookmarks (
    question_id TEXT PRIMARY KEY,
    color TEXT,
    snapshot_json TEXT,          -- full question object
    created_at TEXT
);

CREATE TABLE archives (
    question_id TEXT PRIMARY KEY,
    snapshot_json TEXT,
    created_at TEXT
);

CREATE TABLE user_notes (
    question_id TEXT PRIMARY KEY,
    notes_html TEXT,
    diagram_mermaid TEXT,
    updated_at TEXT
);
```

### What to Keep (No AI Required)
```
✅ Daily practice with SM-2 SRS
✅ F1 scoring + quality mapping
✅ All 4 daily session business rules
✅ Regressive practice (2-streak mastery)
✅ Targeted drill (adaptive re-queue)
✅ Practice by bookmarks (filter by color)
✅ Practice by incorrect history
✅ Progress dashboard (4-category)
✅ Wrong answers review
✅ Bookmarks CRUD (5 colors)
✅ Archives CRUD (restore)
✅ Full-text search
✅ Notes + Mermaid diagrams per question
✅ Simple Retry + Hard Retry
✅ Math rendering (use WebView + KaTeX or MathJax)
✅ Exact duplicate detection (hash-based, zero AI)
```

### What Uses AI (Skip for MVP)
```
🤖 Topic Analysis page — LLM tag clustering
🤖 Contextual duplicate detection — Ollama embeddings + cosine similarity
🤖 Notes contextual reordering — Ollama embeddings
```

### Mobile Navigation Map
```
Bottom Nav:
├── 🏠 Daily Practice
├── 📚 Practice Modes
│   ├── By Bookmarks
│   ├── Incorrect / Struggling
│   ├── Regressive Mastery
│   └── Targeted Drill
├── 📊 Progress Dashboard
├── 🔖 Bookmarks
└── ⋯ More
    ├── Search
    ├── Wrong Answers Review
    ├── Archives
    └── Notes Review
```

### Session State → ViewModel Mapping
| Web `session_state` key | Android ViewModel field |
|-------------------------|------------------------|
| `current_exam_folder` | `selectedDeckId: String` |
| `questions` (filtered) | `sessionQueue: List<Question>` |
| `current_q_index` | `currentIndex: Int` |
| `answers[q_id]` | `currentAnswer: List<Int>` |
| `submitted[q_id]` | `isSubmitted: Boolean` |
| `mode` | `shuffleEnabled: Boolean` (Settings) |
| `regressive_queue` | `masteryQueue: MutableList<Question>` |
| `regressive_stats` | `streakMap: Map<String, Int>` |
| `drill_questions` | `drillQueue: MutableList<Question>` |
