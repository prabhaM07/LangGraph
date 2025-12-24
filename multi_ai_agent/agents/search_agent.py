from typing import Dict
from tools.web_search import search_travel_destinations
from travelState import TravelState
from langchain_core.messages import AIMessage


def search_agent(state: TravelState) -> Dict:
    """Search web for destinations or weather"""
    
    db_result = state.get("db_results", {})
    
    if len(db_result) != 0:
        
        user_preferences = state.get("user_preferences")
        
        result = search_travel_destinations.invoke({"user_preferences": user_preferences})
        
        msg = f"Search: Retrieved weather for {len(result)} destinations"
        
        return {
            "messages": [AIMessage(content=f"{msg}")],
            "web_results": result,
            "next_agent": "supervisor",
            "agent_messages": state.get("agent_messages", []) + [msg]
        }
        
        
        