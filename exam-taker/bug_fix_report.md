
# Bug Investigation Report: "Practice Incorrect" Pre-selected Answers

## Root Cause Analysis
The issue where questions appeared with pre-selected answers was caused by **Duplicate Question IDs** across different exam batch files. 

The Streamlit application uses the Question ID to store user answers in `st.session_state`. When multiple questions share the same ID, they share the same answer state. If a user answers one, the other (duplicate) question immediately reflects that answer when loaded.

## Findings
1. **ID Collisions**:
   - `regressive_test_batch3.json` contained IDs duplicated from `regressive_test_batch2.json` (e.g., `Batch_2_revision_3`).
   - `regressive_test_batch4.json` contained IDs duplicate from `Batch_2` series as well.
   - `regressive_test_batch4.json` also contained a corrupted object merging two questions (`revision_7` and `revision_10`).

## Actions Taken
1. **Deduplication**:
   - Renamed duplicate IDs in `regressive_test_batch3.json` by appending `_batch3`.
   - Renamed duplicate IDs in `regressive_test_batch4.json` by appending `_batch4`.
   - This ensures every question has a unique ID, preventing state collisions.

2. **Corruption Fix**:
   - Removed a malformed/corrupted question object in `regressive_test_batch4.json` that contained duplicate keys and mixed content.

## Recommendations
- **Verify Fix**: Please browse the "Practice Incorrect" page again. The issue should be resolved.
- **Data Integrity**: Consider running the `deduplicate_ids.py` script periodically if you manually add more questions, to catch duplicates early.
- **Clean State**: You may want to clear your browser cache or reset the exam session (e.g., via "Reset" if available) to clear out any old invalid state usage, although new IDs will automatically start fresh.

