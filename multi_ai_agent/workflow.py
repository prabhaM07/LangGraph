from typing import Literal
from langgraph.graph import StateGraph, END
from agents.weather_agent import weather_agent
from router import router
from langgraph.checkpoint.memory import MemorySaver
from agents.analyst_agent import analyst_agent
from agents.extractor_agent import extractor_agent
from agents.search_agent import search_agent
from agents.supervisor_agent import supervisor_agent
from agents.query_agent import query_agent
from travelState import TravelState


def create_travel_workflow():

    memory = MemorySaver()
    workflow = StateGraph(TravelState)
    
    # Add nodes
    workflow.add_node("query", query_agent)
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("extractor", extractor_agent)
    workflow.add_node("analyst", analyst_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("weather", weather_agent)
    
    # Set entry point
    workflow.set_entry_point("query")
    
    # Query always goes to supervisor
    workflow.add_edge("query", "supervisor")
    
   
    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "extractor": "extractor",
            "analyst": "analyst", 
            "search": "search",
            "weather": "weather",
            END : END
        }
    )
    
    # All agents return to supervisor for re-evaluation
    workflow.add_edge("extractor", "supervisor")
    workflow.add_edge("analyst", "supervisor")
    workflow.add_edge("search", "supervisor")
    workflow.add_edge("weather", "supervisor")
    
    return workflow.compile()
  
  