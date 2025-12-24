from langgraph.graph import END
from travelState import TravelState


def router(state: TravelState):
    """Route to next agent based on state"""
    
    next_agent = state.get("next_agent", "end")
    
    if next_agent == "end" or state.get("task_complete"):
        return END
    
    valid_agents = ["supervisor", "extractor", "analyst", "search", "weather"]
    
    if next_agent in valid_agents:
        return next_agent
    
    return "supervisor"
  