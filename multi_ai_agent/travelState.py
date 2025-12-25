from typing import Dict, List, Optional, Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class TravelState(TypedDict):
    """State for travel agent workflow"""
    messages: Annotated[list, add_messages]
    user_query: str
    pdf_path: Optional[str]
    extracted_data: Optional[str]
    web_results: Optional[str]
    weather_results: Optional[str]
    news_results: Optional[str]
    final_result: Optional[str]
    agent_messages: List[str]
    next_agent: Optional[str]
    task_complete: bool