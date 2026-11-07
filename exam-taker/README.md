# 📚 Exam Taker Pro

A powerful, local-first exam preparation application built with **Python** and **Streamlit**. It features intelligent scoring, spaced repetition (SRS), and a premium dark-mode interface to help you master any subject.

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have Python installed. Then, install the required library:
```bash
pip install streamlit plotly pandas requests
```

### 2. Run the Application
Navigate to the project directory and launch the app with the grouped sidebar navigation
(Practice, Review, Insights, Manage):
```bash
cd exam-taker
streamlit run main.py
#or to access from any device
streamlit run main.py --server.address 192.168.1.17  --server.port 8501
```
`streamlit run app.py` still works (the Exam page with Streamlit's automatic page list), but `main.py` is the
supported entry point: it registers all 13 pages through `st.navigation`, using `utils/navigation.py`.
```bash

python sync_to_github.py
```

The application will open automatically in your default web browser.

---

## 📖 How It Works

### 1. Folder-Based Organization
The app uses a simple file-system approach. You organize your exams into folders inside the `questions/` directory.
- **Structure**: `questions/{Subject}/{Topic}/*.json`
- **Automatic Discovery**: The app recursively scans the `questions/` folder. Any subfolder containing `.json` files appears in the sidebar dropdown.

### 2. Question Format
You can add questions by creating `.json` files. A single file can contain **one question object** or a **list of question objects**.

**Example JSON:**
```json
[
  {
    "id": "unique-id-001",
    "question": "What is the capital of France?",
    "type": "single_choice",
    "options": ["London", "Berlin", "Paris", "Madrid"],
    "correct_indices": [2],
    "tags": ["geography"],
    "difficulty": "easy",
    "explanation": "Paris is the capital and most populous city of France."
  }
]
```

### 3. The Interface
- **Sidebar**: Select your exam topic here. You can also switch between "Standard" (sequential) and "Shuffled" modes.
- **Main View**: Questions are presented one by one in a focused card view.
- **Feedback**: Immediate visual feedback (Green/Red) with detailed explanations after submission.

---

## 🧠 Core Logic & Features

### 📊 Smart Scoring (F1 Score)
Unlike basic apps that only give 0 or 1, Exam Taker Pro uses an **F1-Score** algorithm for multi-select questions.
- **Precision**: Did you avoid selecting wrong answers?
- **Recall**: Did you find all the correct answers?
- **Result**: You get partial credit for being close, but penalties for guessing wrong.

### 📅 Spaced Repetition System (SM-2)
The app implements the industry-standard **SuperMemo-2 (SM-2)** algorithm to optimize your learning.
1.  **Quality Rating**: Your F1 score (0.0 - 1.0) is converted to a quality scale (0 - 5).
2.  **Scheduling**:
    - **High Quality (4-5)**: The question is scheduled for a later date (interval increases).
    - **Low Quality (0-3)**: The question is flagged to be reviewed sooner (interval resets).
3.  **Tracking**: Every attempt is logged in `logs/attempts/{question_id}.log.json`, tracking your history and next due date.

### 🤖 Topic Analysis Dashboard (LLM-Powered)
Gain deeper insights into your study patterns with the new **Topic Analysis** page.
- **Intelligent Clustering**: Uses an LLM (Ollama or OpenAI) to group your granular tags into high-level themes (e.g., "Neural Networks", "Optimization").
- **Performance Metrics**: Visualizes your mastery of each topic with interactive charts.
- **Weak Area Detection**: Automatically highlights topics where you are struggling.
- **On-Demand**: Analysis is cached and only refreshed when you explicitly click the button, saving API costs/compute.

---

## 💡 Best Practices

1.  **Granular Folders**: Organize questions into specific topics (e.g., `Math/Algebra`, `Math/Calculus`) rather than giant buckets. This allows for focused study sessions.
2.  **Rich Explanations**: Always add the `"explanation"` field to your JSONs. Understanding *why* an answer is wrong is key to learning.
3.  **Regular Practice**: The SRS system works best if you use the app regularly. The app will show you the "Next Due" date for each question.
4.  **Multi-Question Files**: Group related questions into a single JSON file (as a list) to keep your file system clean.

---

## 📂 Project Structure

```text
exam-taker/
├── app.py                  # Main Application Entry Point
├── README.md               # This file
├── utils/                  # Core Logic Modules
│   ├── file_manager.py     # JSON loading & Folder scanning
│   ├── scoring.py          # F1 Math & Quality conversion
│   └── srs.py              # SM-2 Algorithm implementation
├── questions/              # YOUR DATA GOES HERE
│   └── [Subject]/...       # Exam folders
└── logs/                   # AUTOMATED LOGS
    └── attempts/           # History & SRS data for every question
```
Here is the text converted into a clean, structured Markdown format.

## **Topic Analysis Dashboard**

The Topic Analysis Dashboard provides a high-level view of your exam performance, grouped by specific themes or topics identified by the AI. Below is a breakdown of what each section showcases.

---

### **1. Overview Metrics (Top Row)**
This section gives you an immediate summary of your overall standing.

* **Total Questions:** The total count of unique questions included in the current analysis (e.g., 1546).
* **Overall Accuracy:** Your aggregate success rate across all attempted questions (e.g., 69.9%).
* **Topics Identified:** The number of distinct categories or themes the AI has clustered your questions into (e.g., 25 topics).

---

### **2. Weak Areas (Horizontal Bar Chart)**


[Image of horizontal bar chart showing performance metrics]


* **Goal:** Identifying topics that need the most improvement.
* **What it shows:** This chart lists the top 5 topics where you have the **lowest accuracy**.
* **Filter constraint:** It only includes topics with at least **3 questions** (to avoid skewing data with topics that only have 1 or 2 questions).
* **Visuals:** The bars are color-coded (**Red-Yellow-Green**) based on the accuracy percentage, allowing you to quickly spot critical areas.

> **Example:** "Reinforcement Learning & Benefits" might appear as a lower accuracy area relative to others.

---

### **3. Topic Mastery (Stacked Bar Chart)**


[Image of stacked bar chart data visualization]


* **Goal:** Understanding your volume of practice and outcomes per topic.
* **What it shows:** A breakdown of every identified topic on the X-axis.
* **The Bars:** Each bar is stacked to show:
    * **Green:** Questions answered correctly.
    * **Red:** Questions answered incorrectly.
    * **Grey:** Questions you haven't attempted yet.
* **Insight:** This helps you differentiate between topics you are **bad at** (lots of red) vs. topics you simply **haven't practiced enough** (lots of grey).

---

### **4. Detailed Breakdown (Table)**

* **Goal:** Granular data access.
* **What it shows:** A sortable table containing the raw numbers for every topic.

| Column | Description |
| :--- | :--- |
| **Topic** | The name of the category. |
| **Status Counts** | The exact counts for **Total**, **Correct**, **Wrong**, and **Unattempted**. |
| **Accuracy** | Your percentage score for that specific topic. |

> **Visual Aid:** The "Accuracy" column utilizes a color gradient background (**Red to Green**) to make high and low scores stand out visually while scrolling.

Here is the text converted into a clean, structured Markdown format.

## **System Architecture & Logic Review**

### **1. What do we actually send to the LLM?**
* **Current State:** We send **ONLY the Tags**, not the questions.
* **Why?** Cost and Speed.
    * Sending 50 full questions (approx. 10,000 tokens) is expensive.
    * Sending 50 tags (approx. 200 tokens) is cheap.
* **The Assumption:** We assume the tags (like `latency`, `transformer`, `s3-bucket`) are descriptive enough for the LLM to guess the topic.

### **2. How do we currently handle "New Questions"?**
* **Current State:** We use a **"Diffing" (Difference)** approach, which is very similar to your "Flagging" idea, but done in real-time.
    1.  **Load Cache:** We load your `topic_analysis_cache_nvidia.json` (which contains all tags we've ever seen).
    2.  **Scan Files:** We read your question files and gather all current tags.
    3.  **The Diff:** We calculate `New Tags = Current Tags - Cached Tags`.
* **The Trigger:**
    * If you add 50 questions, and they all use tags we've seen before (e.g., `python`), **Zero LLM calls happen**. It's instant.
    * We **only** call the LLM if we find a tag we have never seen before.
* **Verdict on your "JSON Log" idea:** You don't actually need a separate "unprocessed log" file because the **Cache File itself acts as the log**. If a tag is in the cache, it's "processed." If it's not, it's "new." This is simpler and less prone to sync errors.

### **3. The Missing Piece: "Context / History" (Your Great Idea)**
* **Current State (Weakness identified):** Currently, when we find new tags, we say to the LLM: *"Here are 5 new tags. Group them into topics."*
* **The Problem:** The LLM doesn't know what topics you **already** have.
    * *Scenario:* You already have a topic called **"Neural Networks"**.
    * *New Tag:* You add a question with the tag `perceptrons`.
    * *LLM Decision:* Without context, the LLM might create a **new** topic called **"Deep Learning"**.
    * *Result:* You now have two topics (*Neural Networks* and *Deep Learning*) splitting your data.
* **Your Solution:** We should absolutely change the prompt to be:
    > "Here are 5 new tags. Here are my **Existing Topics** (Neural Networks, Hardware, Security). Please fit these new tags into the Existing Topics if they fit. Only create a NEW topic if absolutely necessary."

---

### **Summary of the Refined Architecture**

If we implement your brainstorming, the flow becomes:

1.  **Scan:** Identify tags not in Cache.
2.  **Read History:** Extract the list of unique **Existing Topics** from the Cache.
3.  **Prompt LLM (Enhanced):**
    * **Input:** New Tags + List of Existing Topics.
    * **Instruction:** "Classify new tags into Existing Topics first."
4.  **Result:** Your dashboard stays clean, and `perceptrons` correctly lands in **Neural Networks** instead of creating a duplicate category.

---

**Shall we proceed with upgrading the `TopicAnalyzer` to include this "History-Aware" prompting?**

Here is the text converted into a clean, structured Markdown format.

## **System Efficiency & Caching Logic**

### **1. Logic Confirmation: No New Tags = No LLM Call**

> **"If there are no new tags... LLM will not be called at all, right?"**

**Yes, exactly.**

* **The Logic:** The system calculates `New Tags = All Tags - Cached Tags`.
* **The Result:** If `New Tags` is empty (0 items), the code skips the LLM call entirely.
* **The Benefit:** It prints a log message (visible in the terminal) and immediately returns the cached data. It is **100% free and instant**.



[Image of software cache flow chart]


### **2. Cache File Strategy**

> **"The cache file will have the tag information related to each exam right?"**

**Yes.** You now have specific files for each exam suite, for example:
`logs/attempts/topic_analysis_cache_nvidia-exam.json`

* This file acts as the **permanent database** for that exam suite.
* It contains the map of `tag -> topic` for every tag ever encountered in that folder.

---

### **3. Summary of Smart Behavior**

Here is how the system handles different scenarios:

* **Phase 1: First Run**
    It bootstraps from your old global cache (so you don't have to start from zero).

* **Phase 2: Adding New Questions (e.g., 5 new questions)**
    1.  It finds the specific new tags (e.g., 3 tags).
    2.  It sends **only** those 3 tags to the LLM.
    3.  **Prompt Instruction:** "Please try to fit these into my *existing topics* (e.g., 'Optimization') first."
    4.  Updates the Cache $\rightarrow$ Updates the Dashboard.

* **Phase 3: Daily Practice**
    **No LLM calls.** Just instant statistical updates based on the existing cache.

---

**Would you like to move on to implementing the "History-Aware" prompt in the Python code now?**


Rank,Model Name,User Experience,Inference Speed (ms/pair),Results Rating
1,all-MiniLM-L6-v2,Excellent (simple Sentence Transformers API),~2 (fast bi-encoder),Good (86% STS-B)
2,BAAI/bge-small-en-v1.5,Excellent (HF/Sentence Transformers),~3 (efficient 384-dim),Very Good (89% STS-B)
3,jinaai/jina-embeddings-v2-small-en,Very Good (HF optimized),~3 (compact design),Very Good (88% STS-B)
4,all-mpnet-base-v2,Excellent (mature ecosystem),~5 (balanced bi-encoder),Very Good (88% STS-B)
5,microsoft/Multilingual-MiniLM-L12-v2,Very Good (multilingual bonus),~4 (slightly deeper),Good (85% STS-B)
6,cross-encoder/quora-distilbert-base,Good (pairwise direct),~15 (per-pair compute),Good (87% Quora/STS)
7,Phi-3-mini,Good (prompt engineering needed),~200 (prompted generation),"Very Good (strong reasoning, ~88% equiv. acc.)"
8,cross-encoder/stsb-roberta-large,Fair (heavier setup),~25 (large per-pair),Excellent (91% STS-B)
9,TinyLlama,Fair (basic prompting),~150 (smaller SLM),Fair (80% equiv. acc.)


Script usage:
To remove duplicates from the specific file you mentioned:

bash
python utils/remove_duplicates.py questions/nvidia-exam/Exam10/nca_genl_questions.json
To scan and clean an entire folder (recursive):

bash
python utils/remove_duplicates.py questions/nvidia-exam

---

## 🛠️ Development

### Run the tests
```bash
cd exam-taker
python -m pytest -q                  # everything (about 40 s)
python -m pytest -q -m smoke         # every page loads
python -m pytest -q -m flow          # user-flow contracts
python -m pytest -q tests/test_ui_exam.py   # one file; each file also passes on its own
```
- Use `python -m pytest`, not the bare `pytest` script: `pytest.ini` loads the plugin
  `tests.plugins.isolation`, which only imports when the project folder is on `sys.path`.
- Tests run on a temporary copy of `tests/fixtures/workspace`; they never touch `questions/`, `logs/`,
  `bookmarks/`, `archives/` or `user_data/`. No test calls an LLM or the network (they are mocked).
- Test layout: `test_logic_*` (scoring, SRS, files, daily session), `test_exam_flow`, `test_review_flow`,
  `test_insights_flow` (frozen behaviour contracts), `test_ui_*` (look and feel), `test_navigation*`,
  `test_page_chrome`, `test_isolation`.
- Install the dev tools once: `pip install -r requirements-dev.txt` (pytest, playwright), then
  `python -m playwright install chromium`.

### Take screenshots
```bash
python tests/visual/shoot.py release   # label = output folder name
```
Starts the app (`main.py`) on a temporary copy of the fixture workspace, opens every page through its
navigation URL plus the main flows (answering, review cards, filters, topic analysis, duplicates...), and saves
PNGs to `tests/.artifacts/screens/<label>/`. The Targeted drill page is shot through a tiny wrapper entry
that seeds a drill session. Nothing here uses your real data or calls an LLM.

### Where the design system lives
- `design-system/DESIGN_SYSTEM.md` - principles, colour tokens, type, icons. `tokens.json` and
  `reference-components.css` hold the same values.
- `design-system/pages.md` - page-by-page UI plan; `design-system/IMPLEMENTATION_PLAN.md` - batches 0-8,
  status and known follow-ups.
- In code: `utils/ui_helpers.py` (`TOKENS`, global CSS, Plotly theme), `utils/ui_components.py` (pure HTML helpers),
  `utils/exam_view.py` (the exam card shared by the Exam and practice pages), `utils/navigation.py` (the nav).
- Rules for contributors: `CLAUDE.md` (keep widget keys, no logic changes in `utils/*` for UI work, colours only
  from `ui_helpers.TOKENS`, Material icons instead of emoji).
