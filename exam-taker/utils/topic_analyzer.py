import json
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from .llm_client import LLMClient
from .file_manager import load_questions, load_question_log, get_exam_files, QUESTIONS_ROOT, LOGS_ROOT

class TopicAnalyzer:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def get_analysis_for_suite(self, suite_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Retrieves analysis for a specific exam suite (e.g., 'nvidia-exam').
        1. Checks for suite-specific cache: `topic_analysis_cache_{suite_name}.json`
        2. If not found, tries to bootstrap from legacy global cache.
        3. Runs analysis (filtered to this suite).
        """
        # Sanitization for filename
        safe_suite = "".join(c for c in suite_name if c.isalnum() or c in ('-', '_')) if suite_name else "global"
        cache_filename = f"topic_analysis_cache_{safe_suite}.json"
        
        # If suite is "All" or not provided, we warn or handle differently. 
        # For compatibility with legacy calls, if suite is empty, we might default to global, 
        # but in the new UI flow we force selection.
        if suite_name == "All" or not suite_name:
            # We don't support "All" in the new segregated model for analysis creation
            return {}

        cache_path = LOGS_ROOT / cache_filename

        if not force_refresh and cache_path.exists():
            # We want to use the TAGS from the cache, but re-calculate the STATS (Correct/Wrong counts).
            # So we do NOT return the full object here. We just let run_analysis happen.
            # run_analysis will load this cache file to get the tag_map, preventing LLM calls.
            pass

        return self.run_analysis(suite_name, cache_path, force_llm=force_refresh)

    def run_analysis(self, suite_name: str, cache_path: Path, force_llm: bool = False) -> Dict[str, Any]:
        """
        Runs analysis for a specific suite.
        Bootstraps from legacy cache if available to save tokens.
        """
        # 1. Load questions (Filtered by Suite)
        all_questions = []
        all_files = get_exam_files(str(QUESTIONS_ROOT))
        
        # Filter files belonging to this suite
        suite_files = []
        if suite_name and suite_name != "All":
            norm_suite = suite_name.replace("\\", "/") + "/"
            for f in all_files:
                norm_f = f.replace("\\", "/")
                # Check if the file is inside the suite folder
                if norm_f.startswith(norm_suite):
                    suite_files.append(f)
        else:
            suite_files = [] # Should not happen if driven by UI correctly

        for file_path in suite_files:
            qs = load_questions(str(QUESTIONS_ROOT), file_path)
            all_questions.extend(qs) 
        
        # 2. Extract Tags
        all_tags = set()
        for q in all_questions:
            if "tags" in q:
                for tag in q["tags"]:
                    all_tags.add(tag)
        
        # 3. Cluster Tags (Bootstrap logic)
        tag_map = {}
        
        # A. Try loading current suite cache first (if we are just refreshing, we want old state to persist if we can)
        if cache_path.exists() and not force_llm:
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    tag_map = json.load(f).get("tag_map", {})
            except: pass
            
        # B. If tag_map is still empty (new suite), try loading LEGACY global cache to migrate data
        if not tag_map:
            legacy_path = LOGS_ROOT / "topic_analysis_cache.json"
            if legacy_path.exists():
                try:
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        print("Bootstrapping from legacy global cache...")
                        legacy_data = json.load(f)
                        legacy_map = legacy_data.get("tag_map", {})
                        # Only keep mappings relevant to our current tags
                        for t in all_tags:
                            if t in legacy_map:
                                tag_map[t] = legacy_map[t]
                except Exception as e:
                    print(f"Legacy bootstrap failed: {e}")

        # Identify new tags
        new_tags = [t for t in all_tags if t not in tag_map]
        
        if new_tags:
            print(f"Clustering {len(new_tags)} new tags for suite '{suite_name}'...")
            
            # Extract existing unique topics to provide context/history
            existing_topics = sorted(list(set(tag_map.values())))
            
            # Pass suite context and history to LLM
            new_map = self._cluster_tags_with_llm(new_tags, context=suite_name, existing_topics=existing_topics)
            tag_map.update(new_map)

        # 4. Compute Stats
        topics_stats = defaultdict(lambda: {"total": 0, "correct": 0, "wrong": 0, "unattempted": 0, "questions": []})
        
        for q in all_questions:
            q_id = q.get("id")
            q_tags = q.get("tags", [])
            
            # Determine Status
            log = load_question_log(q_id)
            summary = log.get("summary", {})
            attempts = summary.get("total_attempts", 0)
            correct = summary.get("correct_count", 0)
            
            status = "unattempted"
            if attempts > 0:
                if correct == attempts:
                    status = "correct"
                elif correct == 0:
                    status = "wrong"
                else:
                    status = "wrong" # Mixed counted as wrong

            # Assign to Topics
            assigned_topics = set()
            for tag in q_tags:
                topic = tag_map.get(tag, "Uncategorized")
                assigned_topics.add(topic)
            
            if not assigned_topics:
                assigned_topics.add("Uncategorized")
                
            for topic in assigned_topics:
                topics_stats[topic]["total"] += 1
                topics_stats[topic]["questions"].append(q_id)
                if status == "correct":
                    topics_stats[topic]["correct"] += 1
                elif status == "wrong":
                    topics_stats[topic]["wrong"] += 1
                else:
                    topics_stats[topic]["unattempted"] += 1

        result = {
            "tag_map": tag_map,
            "topics": dict(topics_stats),
            "suite": suite_name
        }
        
        # 5. Cache
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
            
        return result

    def _cluster_tags_with_llm(self, tags: List[str], context: str = "", existing_topics: List[str] = None) -> Dict[str, str]:
        if not tags:
            return {}
            
        context_str = f" for a '{context}' exam" if context else " for a technical exam"
        
        history_instruction = ""
        if existing_topics:
            topics_str = ", ".join([f'"{t}"' for t in existing_topics])
            history_instruction = f"""
        IMPORTANT: The user already has these existing topics: [{topics_str}].
        1. Try to fit the new tags into these EXISTING topics first if they are a good match.
        2. Only create a NEW topic name if the tag clearly does not fit any existing one.
        """
            
        # Batching could be needed if too many tags, but for now assume < 1000 tags.
        prompt = f"""
        I have a list of NEW tags{context_str}.
        Please group them into high-level "Topics" or "Themes" SPECIFIC to this domain.
        {history_instruction}
        Examples of Topics (if no history): "Neural Networks", "NLP", "Optimization", "Computer Vision".
        
        Return ONLY a JSON object mapping each tag to its Topic.
        Format: {{ "tag_name": "Topic Name", ... }}
        
        New Tags to group:
        {json.dumps(tags)}
        """
        
        response = self.llm.generate_response(prompt, system_prompt="You are a helpful classifier. Return only valid JSON.")
        
        # Clean response (remove markdown code blocks if present)
        clean_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            mapping = json.loads(clean_response)
            return mapping
        except json.JSONDecodeError:
            print(f"LLM failed to return JSON. Raw response: {response}")
            # Fallback: map all to "Uncategorized"
            return {t: "Uncategorized" for t in tags}
