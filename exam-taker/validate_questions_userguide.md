# validate_questions.py — User Guide

## Run Modes

```bash
# All files
python validate_questions.py

# All files in a specific subfolder
python validate_questions.py questions/CampusXDeepLearning-CNN-RNN/
python validate_questions.py --fix questions/CampusXDeepLearning-CNN-RNN/

# Specific file
python validate_questions.py questions/CampusXDeepLearning-CNN-RNN/60-problems-with-rnn.json

# Files modified since a date
python validate_questions.py --since 2026-03-20

# Summary only (no per-issue detail)
python validate_questions.py --summary

# Errors only, suppress warnings
python validate_questions.py --errors-only

# Reformat JSON in-place (4-space indent, UTF-8, LF)
python validate_questions.py --fix questions/my-new-file.json

# Combine flags
python validate_questions.py --since 2026-03-20 --errors-only
python validate_questions.py --fix --summary
```

## What It Checks

**Schema (errors):**
- Valid JSON, root is `[]` array
- All 8 required fields present: `id`, `question`, `type`, `options`, `correct_indices`, `tags`, `difficulty`, `explanation`
- `type` must be `"multiple_choice"`
- `difficulty` must be `easy`, `medium`, or `hard`
- `correct_indices` values are in bounds and non-negative
- No duplicate IDs within a file
- No empty string fields

**LaTeX (errors):**
- Even number of `$` signs (unmatched delimiter)
- No empty `$$`
- Balanced `{ }` inside each `$...$`
- No raw newlines inside `$...$`
- No control characters (`\t`, `\r`) inside LaTeX

**Warnings (non-blocking):**
- Empty placeholder files `{}`
- No tags provided
- Root is object `{}` instead of array `[]`

## Recommended Workflow for New Files

1. Add your `.json` file to the questions folder
2. Run: `python validate_questions.py --fix path/to/new-file.json`
3. Before committing a batch: `python validate_questions.py --since YYYY-MM-DD --errors-only`

Exit code `0` = clean, `1` = errors found (usable in pre-commit hooks or CI).
