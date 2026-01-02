from langchain_core.messages import HumanMessage
from travelState import TravelState

def get_user_query(state: TravelState) -> str:
    """
    Extract user query from state, handling both direct query and messages format
    """
    # First check if user_query exists directly
    if "user_query" in state and state["user_query"]:
        return state["user_query"]
    
    # Otherwise extract from messages (for LangGraph Studio)
    messages = state.get("messages", [])
    if messages:
        # Get the last human message
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
    
    # Fallback
    return "No query provided"