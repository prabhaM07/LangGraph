from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages

class TravelState(TypedDict):
    """State for the travel planning workflow"""
    messages: Annotated[list, add_messages]
    user_query: str
    agent_messages: List[str]
    task_complete: bool
    
    # Data storage
    pdf_path: Optional[str]
    
    # Routing
    next_agent: Optional[str]
    
    # Location tracking
    travel_location: Optional[str]
    
    # Flag to track if trip_planner was called
    trip_planner_called: Optional[bool]
    
    # Final output
    final_result: Optional[str]