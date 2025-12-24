from langgraph.graph import MessagesState
from typing import Dict,List,Optional

from travel_preference import TravelPreference

class TravelState(MessagesState):
    
    next_agent: Optional[str] = None
    task_complete: bool = False
    user_query: Optional[str] = None
    pdf_path: Optional[str] = None
    extracted_data: Optional[Dict] = None
    db_results: Optional[Dict] = None
    web_results: Optional[Dict] = None
    weather_results:Optional[Dict] = None
    final_result: Optional[Dict] = None
    user_preferences: Optional[TravelPreference] = None 
    agent_messages: List[str] = []
    
    
    
