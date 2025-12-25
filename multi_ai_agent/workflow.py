from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from llm_model import get_llm
from tools.news import get_travel_news
from tools.pdf_extractor import get_travel_recommendations
from tools.web_search import search_travel_destinations
from tools.weather import get_weather
from agents import (
    coordinator_node,
    synthesizer_node,
    should_continue
)
from travelState import TravelState

def create_travel_workflow():
    """Creates the complete multi-agent travel planning workflow"""
    
    llm = get_llm()
    
    # Define tools
    tools = [
        get_weather,
        get_travel_news,
        search_travel_destinations,
        get_travel_recommendations
    ]
    
    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)
    
    # Create graph
    workflow = StateGraph(TravelState)
    
    # Add nodes - simplified architecture
    workflow.add_node("coordinator", lambda state: coordinator_node(state, llm_with_tools))
    workflow.add_node("tools", ToolNode(tools=tools))
    workflow.add_node("synthesizer", lambda state: synthesizer_node(state, llm))
    
    # Add edges
    workflow.add_edge(START, "coordinator")
    
    # Conditional routing from coordinator
    workflow.add_conditional_edges(
        "coordinator",
        should_continue,
        {
            "tools": "tools",
            "synthesizer": "synthesizer",
            "__end__": END
        }
    )
    
    # After tools execute, go to synthesizer
    workflow.add_edge("tools", "synthesizer")
    
    # Synthesizer to end
    workflow.add_edge("synthesizer", END)
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)