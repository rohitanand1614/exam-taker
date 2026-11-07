# Exam Taker Pro - Technical Documentation

## 1. Executive Summary
Exam Taker Pro is a local-first, Python/Streamlit based educational application that provides a sophisticated environment for exam preparation. It features intelligent scoring, spaced repetition (SRS), dark-mode UI, AI-powered topic analysis, and contextual notes review.

## 2. Architecture Overview
The application is structured as a Streamlit multi-page app with a backend primarily defined through utility functions (`utils/`) operating on local JSON databases. 
- **Frontend**: Streamlit for UI components, custom CSS for a premium dark mode, and Plotly for analytics dashboards.
- **Backend**: Python utility modules handling file I/O, scoring logic, spaced repetition algorithms (SM-2), and interactions with LLMs (Ollama or OpenAI API).
- **Storage**: Flat-file JSON system providing portability and ease of manual edits.

## 3. Folder Structure Breakdown
```text
exam-taker/
├── app.py                     # Main application entry point (Streamlit)
├── pages/                     # Streamlit frontend pages
│   ├── Archived_Questions.py
│   ├── Bookmarks.py
│   ├── Notes_Review.py        # Semantic sorting of user notes + PDF export
│   ├── Practice_Bookmarks.py
│   ├── Practice_Incorrect.py
│   ├── Progress_Dashboard.py  # Overall metrics and question categorizations
│   ├── Regressive_Practice.py
│   ├── Search_Questions.py    # Search and filtering interface
│   ├── Similar_Questions_Management.py
│   ├── Targeted_Drill.py      # Dynamic queue based on weak topics
│   ├── Topic_Analysis.py      # Visualizes LLM-clustered topic metrics
│   └── Wrong_Answers.py
├── utils/                     # Backend Logic modules
│   ├── archive_manager.py     # Move questions to archive
│   ├── bookmark_manager.py    # Handles user bookmarks
│   ├── file_manager.py        # Loads/Saves JSON questions and attempt logs
│   ├── llm_client.py          # Wrapper for AI operations
│   ├── remove_duplicates.py   # Cleanup utility
│   ├── scoring.py             # F1 scoring logic
│   ├── similarity.py          # Cross-encoder similarity matching
│   ├── srs.py                 # SM-2 Spaced Repetition Algorithm
│   ├── topic_analyzer.py      # LLM-based semantic tag clustering
│   └── ui_helpers.py          # Frontend UI injectors (CSS/JS)
├── questions/                 # Primary Database: JSON question files
│   └── [Exam Folders] / ...
├── user_data/                 # Cache files (LLM embeddings, topic cache)
└── logs/
    └── attempts/              # User progress logs per question ID
```

## 4. Data Models and Storage
The application utilizes a purely local file-based storage architecture.

### 4.1 Question Schema (JSON)
Questions are stored as lists of objects inside `.json` files under `questions/`.
```json
{
  "id": "Transformer_001",
  "question": "What is self-attention?",
  "type": "multiple_choice",
  "options": ["A", "B", "C", "D"],
  "correct_indices": [1],
  "tags": ["transformer", "attention"],
  "difficulty": "medium",
  "category": "conceptual",
  "explanation": "Detailed rationale."
}
```

### 4.2 Attempt Logs (`logs/attempts/{question_id}.log.json`)
Every user attempt is logged with a timestamp, score, and applied SRS parameters.
```json
{
  "question_id": "Transformer_001",
  "summary": {
    "total_attempts": 3,
    "correct_count": 2,
    "current_srs": {
      "repetitions": 2,
      "interval_days": 6,
      "ef": 2.6,
      "next_due": "2026-03-01"
    }
  },
  "attempts": [
    {"timestamp": "...", "score": 1.0, "selected_indices": [1]}
  ],
  "user_notes": "...",
  "user_diagram": "..."
}
```

### 4.3 Cache System (`user_data/`)
To reduce API costs and latency, the system caches LLM outputs:
- `notes_embedding_cache.json`: Caches generated semantic embeddings for Notes Review.
- `topic_analysis_cache_{suite}.json`: Caches the LLM tag-to-topic mapping per exam suite.

## 5. Backend Implementation Details

### 5.1 Scoring Logic (`utils/scoring.py`)
Multi-select questions require partial grading. The system computes an **F1 Score** using True Positives (TP = selected ∩ correct), Precision, and Recall. This creates a score between 0.0 and 1.0. The score is then converted to an integer quality rating (0-5) suitable for SRS using the `score_to_quality` function.

### 5.2 Spaced Repetition (`utils/srs.py`)
Uses the standard SM-2 algorithm. Parameters track:
- `repetitions`: Streak of successful recalls.
- `ef` (Easiness Factor): Multiplier for the inter-repetition interval.
- `interval_days`: Days until the question should be reviewed next.

### 5.3 Topic analyzer (`utils/topic_analyzer.py`)
Utilizes a local LLM or OpenAI to map raw granular tags into broader "Topics". It attempts to cluster new tags into existing known topics first to prevent fragmentation. Results are cached and shown heavily in the Topic Analysis page.

## 6. Frontend Pages and User Flow

### Main Study Flow (`app.py`)
1. **Selection Mode**: User selects an exam folder or specific file via the sidebar.
2. **Study Mode**: Standard (Sequential) or Shuffled.
3. **Daily Filter Logic**: Questions answered correctly in the last 48 hours and not bookmarked are skipped, focusing the user on what matters today.
4. **Interaction**: User answers -> F1 Score calculated -> SRS updated -> Log saved -> Explanation & custom Markdown/Mermaid notes revealed.

### Dashboard & Analytics Flow
- **Progress Dashboard**: Aggregates logs, sorting questions into `Mastered` (All correct), `Mixed`, `Struggling` (All incorrect), and `Unattempted`.
- **Topic Analysis**: Displays LLM-driven topic mappings. Visualizes data via Plotly graphs (treemaps, bar charts for lowest accuracy). Triggers `Targeted Drill`.
- **Targeted Drill**: Automatically queues questions from the weakest topics. Contains a "Double-Loop" logic that inserts incorrect questions twice in the drill session for reinforced learning.

### Review Flow
- **Notes Review**: Aggregates all user notes. Features an LLM-powered "Reorganize Contextually" button that clusters notes semantically. Exports to PDF using FPDF and BeautifulSoup for clean text extraction.
- **Similar Questions**: Identifies and clusters duplicates across the database.

## 7. Extending the Project (Future Developer Guide)
- **Adding new pages**: Create a `.py` file in `pages/` following Streamlit conventions. Ensure it imports `utils/file_manager.py` for standard data access.
- **Updating the Data Schema**: Modify formatting in `questions/`, update `file_manager.load_questions` validations if necessary, and ensure `app.py` UI rendering supports the new fields (e.g., adding a "hint" property).
- **Updating SRS**: If migrating from SM-2 to FSRS, changes are strictly isolated to `utils/srs.py` and `utils/scoring.py` output mappings. Backwards compatibility for the `current_srs` dict in logs is mandatory.
