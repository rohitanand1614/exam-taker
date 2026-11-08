import os
import sys
import streamlit as st
import plotly.express as px
import pandas as pd
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import file_manager
from utils.file_manager import get_exam_folders, get_question_id_to_file_map, load_question_log, get_exam_files, load_questions
from utils.llm_client import LLMClient
from utils.topic_analyzer import TopicAnalyzer

st.set_page_config(page_title="Topic analysis", page_icon=":material/psychology:", layout="wide")
from utils import ui_helpers, ui_components
ui_helpers.inject_global_css()
ui_helpers.apply_plotly_theme()

# Page head: filled in again below once the number of topics is known.
head_slot = st.empty()
head_slot.markdown(ui_components.page_head_html("Topic analysis", "Mastery by topic, from your attempt logs"),
                   unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.header("Settings")

# Filter
# Filter
all_folders_raw = get_exam_folders("questions")
# Normalize paths to use forward slashes for consistency
all_folders = [f.replace("\\", "/") for f in all_folders_raw]

# 1. Parent Folder (Exam Suite)
exam_suites = sorted(list(set([f.split("/")[0] for f in all_folders])))
suite_options = ["All"] + exam_suites

# Default to 'nvidia-exam' if present (User Preference)
default_ix = 0
if "nvidia-exam" in suite_options:
    default_ix = suite_options.index("nvidia-exam")

selected_suite = st.sidebar.selectbox("Filter by exam suite", suite_options, index=default_ix, key="topic_analysis_suite_selector")

# 2. Sub Folder
if selected_suite != "All":
    filtered_subfolders = [f for f in all_folders if f.startswith(selected_suite)]
else:
    filtered_subfolders = all_folders

selected_folder = st.sidebar.selectbox("Filter by folder", ["All"] + filtered_subfolders)

# LLM Config
st.sidebar.subheader("LLM configuration")
llm_provider = st.sidebar.selectbox("Provider", ["Ollama", "OpenAI"])
model_name = st.sidebar.text_input("Model name", value="llama3.1:8b" if llm_provider == "Ollama" else "gpt-5.1")
api_key = os.getenv("OPENAI_API_KEY", "")
if llm_provider == "OpenAI":
    api_key = st.sidebar.text_input("API key", value=api_key, type="password")

# Run Button
force_refresh = st.sidebar.button("Refresh analysis (trigger LLM)", icon=":material/refresh:")

# --- Logic ---

# Initialize Client
client = LLMClient(provider=llm_provider, model_name=model_name, api_key=api_key if api_key else None)
analyzer = TopicAnalyzer(client)

# Load Analysis
# We use separate session keys for separate suites
if selected_suite == "All":
    st.warning("Please select a specific 'Exam Suite' to view Topic Analysis. Global analysis across different domains is disabled to ensure accuracy.")
    st.stop()
    
session_key = f"topic_analysis_{selected_suite}"

# (not `in`: an empty cached result is stored too, and must still offer the Generate button)
if force_refresh or not st.session_state.get(session_key):
    if not force_refresh:
        # Load from cache automatically
        try:
            st.session_state[session_key] = analyzer.get_analysis_for_suite(selected_suite, force_refresh=False)
            if st.session_state[session_key]:
                st.success(f"Analysis loaded for {selected_suite}.")
        except Exception as e:
            st.error(f"Failed to load cache: {e}")
            
    if force_refresh or not st.session_state.get(session_key):
        # User requested refresh or no cache found
        if force_refresh or st.button(f"Generate analysis for {selected_suite}"):
             with st.spinner(f"Analyzing topics for {selected_suite}... This may take a moment..."):
                try:
                    st.session_state[session_key] = analyzer.get_analysis_for_suite(selected_suite, force_refresh=True)
                    st.success("Analysis updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to run analysis: {e}")
        else:
            st.info(f"No analysis found for {selected_suite}. Click button above to generate.")
            st.stop()

data = st.session_state.get(session_key)

if not data:
    st.info("No analysis data found. Please ensure logs and questions exist.")
    st.stop()

# --- Filtering & Aggregation ---
# We need to re-aggregate based on the selected folder
id_map = get_question_id_to_file_map("questions")

# Prepare data for display
topic_metrics = []
all_filtered_q_ids = set()

for topic, details in data["topics"].items():
    # Filter questions for this topic
    topic_questions = details["questions"]
    
    topic_questions = details["questions"]
    
    filtered_questions = []
    
    # Determine the required prefix filter
    filter_prefix = ""
    if selected_folder != "All":
        filter_prefix = selected_folder
    elif selected_suite != "All":
        filter_prefix = selected_suite
        
    if filter_prefix == "":
        filtered_questions = topic_questions
    else:
        for q_id in topic_questions:
            q_file = id_map.get(q_id, "")
            # Check if file starts with the selected folder (normalized)
            q_file = q_file.replace("\\", "/")
            # filter_prefix is already normalized to /
            if q_file.startswith(filter_prefix):
                filtered_questions.append(q_id)
    
    if not filtered_questions:
        continue
        
    all_filtered_q_ids.update(filtered_questions)

    # Re-calculate stats for filtered questions
    total = len(filtered_questions)
    correct = 0
    wrong = 0
    unattempted = 0
    
    for q_id in filtered_questions:
        log = load_question_log(q_id)
        summary = log.get("summary", {})
        attempts = summary.get("total_attempts", 0)
        c_count = summary.get("correct_count", 0)
        
        if attempts == 0:
            unattempted += 1
        elif c_count == attempts:
            correct += 1
        else:
            wrong += 1
            
    accuracy = (correct / total) * 100 if total > 0 else 0
    
    topic_metrics.append({
        "Topic": topic,
        "Total": total,
        "Correct": correct,
        "Wrong": wrong,
        "Unattempted": unattempted,
        "Accuracy": accuracy
    })

if not topic_metrics:
    st.warning("No questions found for the selected filter.")
    st.stop()

df = pd.DataFrame(topic_metrics)
head_slot.markdown(
    ui_components.page_head_html("Topic analysis", f"{len(df)} topics in {selected_suite}"),
    unsafe_allow_html=True)

# --- Visualizations ---

# 1. Overview Metrics
col1, col2, col3 = st.columns(3)

# Calculate global stats based on unique questions to avoid double counting
total_q = len(all_filtered_q_ids)
global_correct = 0
global_wrong = 0
global_unattempted = 0

for q_id in all_filtered_q_ids:
    log = load_question_log(q_id)
    summary = log.get("summary", {})
    attempts = summary.get("total_attempts", 0)
    c_count = summary.get("correct_count", 0)
    
    if attempts == 0:
        global_unattempted += 1
    elif c_count == attempts:
        global_correct += 1
    else:
        global_wrong += 1

overall_acc = (global_correct / total_q * 100) if total_q > 0 else 0

col1.metric("Total questions", total_q)
col2.metric("Overall accuracy", f"{overall_acc:.1f}%")
col3.metric("Topics identified", len(df))

# 2. Weak Areas (Low Accuracy, Min 5 Questions)
st.subheader("Weak areas")
weak_df = df[df["Total"] >= 3].sort_values("Accuracy", ascending=True).head(5)
if not weak_df.empty:
    fig_weak = px.bar(
        weak_df, 
        x="Accuracy", 
        y="Topic", 
        orientation='h', 
        title="Lowest Accuracy Topics (min 3 questions)",
    )
    # colour = mastery band (>=70 success, 40-69 warning, <40 danger); the plotted data is unchanged
    fig_weak.update_traces(marker_color=[ui_components.mastery_colour(a) for a in weak_df["Accuracy"]])
    fig_weak.update_xaxes(range=[0, 100])
    fig_weak.update_yaxes(automargin=True)       # topic names get their own margin
    st.plotly_chart(fig_weak, use_container_width=True, theme=None)
else:
    st.info("Not enough data to identify weak areas yet (need topics with 3+ questions).")

# 3. Topic Mastery (Treemap or Bar)
st.subheader("Topic mastery")
# Create a stacked bar chart: Correct, Wrong, Unattempted
fig_stack = px.bar(
    df, 
    x="Topic", 
    y=["Correct", "Wrong", "Unattempted"], 
    title="Performance by Topic",
    color_discrete_map={"Correct": ui_helpers.TOKENS["success"], "Wrong": ui_helpers.TOKENS["danger"],
                        "Unattempted": ui_helpers.TOKENS["ink_faint"]}
)
fig_stack.update_layout(legend_title_text="", yaxis_title="Questions")
st.plotly_chart(fig_stack, use_container_width=True, theme=None)

# 4. Detailed Data
st.subheader("Detailed breakdown")
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={"Accuracy": st.column_config.ProgressColumn(
        "Accuracy", format="%.1f%%", min_value=0, max_value=100)},
)

# 5. Mappings (Optional)
with st.expander("View tag to topic mapping", icon=":material/account_tree:"):
    if "tag_map" in data:
        # Convert dict to dataframe for easy viewing
        tag_data = [{"Tag": tag, "Mapped Topic": topic} for tag, topic in data["tag_map"].items()]
        tag_df = pd.DataFrame(tag_data).sort_values("Mapped Topic")
        st.dataframe(tag_df, use_container_width=True, hide_index=True)
    else:
        st.info("No tag mapping found in the analysis data.")

st.divider()

# 6. Actionable: Targeted Drill
st.subheader("Targeted drill")
st.caption("Generate a custom practice session based on your analysis.")

# A. Suggest Weakest Topic
# Sort topics by accuracy (ascending), but only consider those with > 0 attempts or unattempted
sorted_topics = []
for t, stats in data["topics"].items():
    total = stats["total"]
    if total == 0: continue
    acc = 0
    if stats["total"] > 0:
        acc = (stats["correct"] / stats["total"]) * 100
    sorted_topics.append((t, acc, stats))

sorted_topics.sort(key=lambda x: x[1])

# Determine default index
default_topic_idx = 0
topic_names = [t[0] for t in sorted_topics]
try:
    # If we have topics, pick the first one (lowest accuracy)
    default_topic_idx = 0 
except:
    pass

c1, c2 = st.columns([1, 2])
with c1:
    target_topic = st.selectbox("Select topic to drill", topic_names, index=default_topic_idx)

# Find stats for selected
selected_stats = next((s for t, a, s in sorted_topics if t == target_topic), None)

with c2:
    st.write("Drill Configuration:")
    chk_wrong = st.checkbox("Include wrong questions", value=True, help="Re-test questions you got wrong.")
    chk_unattempted = st.checkbox("Include unattempted questions", value=True, help="Test new questions you haven't seen.")
    
    # Double Loop Toggle
    use_double_loop = st.checkbox("Double-loop mode (recommended)", value=True, help="If checked, WRONG questions will be added TWICE to the queue in jumbled order for reinforcement.")

if st.button("Start targeted drill", type="primary", key="topic_drill_start", icon=":material/play_arrow:"):
    if not selected_stats:
        st.error("Invalid topic selected.")
    else:
        # 1. Gather Question IDs
        drill_ids = []
        
        # We need to filter the specific questions for this topic based on their actual status
        # The 'selected_stats' object has raw counts but we need the actual IDs split by status.
        # We need to re-scan or we can rely on the list of IDs in stats and re-check their status.
        # stats['questions'] has ALL IDs for the topic.
        
        topic_q_ids = selected_stats["questions"]
        
        q_wrong = []
        q_unattempted = []
        
        # We ideally need the ID map to check logs, but we can just use file_manager
        # Note: Ideally we pass 'id_map' or reload logs. 
        # For speed, let's re-check status for these specific IDs.
        
        for qid in topic_q_ids:
            log = file_manager.load_question_log(qid)
            summary = log.get("summary", {})
            attempts = summary.get("total_attempts", 0)
            correct = summary.get("correct_count", 0)
            
            is_wrong = False
            is_unattempted = False
            
            if attempts == 0:
                is_unattempted = True
            elif correct < attempts:
                is_wrong = True # Has mistakes or mixed
            elif correct == attempts:
                # 100% correct, skip unless we add a "Review Mastered" option later
                pass
                
            if is_wrong and chk_wrong:
                q_wrong.append(qid)
            if is_unattempted and chk_unattempted:
                q_unattempted.append(qid)
                
        # 2. Build the Queue
        final_queue_ids = []
        
        # Add Unattempted (1x)
        final_queue_ids.extend(q_unattempted)
        
        # Add Wrong (1x or 2x)
        if use_double_loop:
            final_queue_ids.extend(q_wrong)
            final_queue_ids.extend(q_wrong) # Add twice!
        else:
            final_queue_ids.extend(q_wrong)
            
        if not final_queue_ids:
            st.warning("No questions match your criteria! (Maybe you mastered this topic?)")
        else:
            # 3. Load Actual Question Objects
            # We need to find where these questions live.
            # We can use the 'id_map' derived earlier in 'run_analysis' but we don't have it here easily visible.
            # We can iterate all files in the current suite or just use 'load_questions' if we knew the file.
            # HACK: We will scan the suite files to find these IDs.
            
            with st.spinner("Building your drill session..."):
                drill_questions = []
                
                # Get all files for the current suite to search efficiently
                suite_files = []
                all_files_raw = get_exam_files("questions")
                if selected_suite != "All":
                    norm_suite = selected_suite.replace("\\", "/") + "/"
                    suite_files = [f for f in all_files_raw if f.replace("\\", "/").startswith(norm_suite)]
                else:
                    suite_files = all_files_raw

                # Load all candidates
                # This might be slow if suite is huge, but usually fine for < 50 files.
                # Optimization: create a lookup map in session state?
                
                # Let's map ID -> Question Object
                id_to_obj = {}
                for f in suite_files:
                    qs = load_questions("questions", f)
                    for q in qs:
                        if q.get("id") in topic_q_ids: # Only load if relevant to this topic
                            id_to_obj[q.get("id")] = q
                            
                # Construct the final list object
                import random
                
                for qid in final_queue_ids:
                    if qid in id_to_obj:
                        # Copy to avoid reference issues
                        drill_questions.append(id_to_obj[qid].copy())
                        
                # Shuffle
                random.shuffle(drill_questions)
                
                # 4. Success -> Redirect
                st.session_state.drill_questions = drill_questions
                st.session_state.drill_index = 0
                st.session_state.drill_answers = {}
                st.session_state.drill_submitted = {}
                
                st.success(f"Drill generated with {len(drill_questions)} questions! Redirecting to Drill Page...")
                st.switch_page("pages/Targeted_Drill.py")
