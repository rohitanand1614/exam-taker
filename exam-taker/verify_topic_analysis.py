import sys
import os
import json
from unittest.mock import MagicMock

# Add current dir to path
sys.path.append(os.getcwd())

from utils.llm_client import LLMClient
from utils.topic_analyzer import TopicAnalyzer

def test_analysis():
    print("Testing Topic Analysis...")
    
    # Mock LLM Client
    mock_llm = MagicMock(spec=LLMClient)
    # Return a fake JSON response for clustering
    mock_llm.generate_response.return_value = json.dumps({
        "neural networks": "Deep Learning",
        "attention": "Deep Learning",
        "python": "Programming",
        "pandas": "Data Science"
    })
    
    analyzer = TopicAnalyzer(mock_llm)
    
    print("Running analysis (mocked LLM)...")
    # Force refresh to trigger "LLM"
    result = analyzer.get_analysis(force_refresh=True)
    
    print("Analysis Result Keys:", result.keys())
    print("Topics Found:", list(result["topics"].keys()))
    
    if "topics" in result and result["topics"]:
        print("SUCCESS: Analysis generated topics.")
    else:
        print("WARNING: No topics generated (might be empty questions).")

if __name__ == "__main__":
    test_analysis()
