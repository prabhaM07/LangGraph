"""
Wrapper to make your existing travel agent work with LangGraph Studio
Place this file in: D:/materials/LANGGRAPH/projects/studio_wrapper.py
"""

import sys
import os
from pathlib import Path

# Add multi_ai_agent to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "multi_ai_agent"))

# Import your existing workflow
from multi_ai_agent.workflow import create_travel_workflow

# Create the graph - LangGraph Studio will use this
graph = create_travel_workflow()

print("✅ Travel Agent graph loaded for LangGraph Studio")
print("📊 Access Studio at: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024")