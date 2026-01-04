from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from travelState import TravelState
from router import (
    route_after_coordinator,
    route_after_specialist,
    route_after_research_agent,
    route_after_route_planner,
    should_continue_after_tools,
    route_after_synthesizer,  # NEW: Add this router
)

from agents import (
    coordinator_node,
    trip_planner_node,
    research_agent_node,
    weather_analyst_node,
    accommodation_specialist_node,
    restaurant_suggester_node,
    route_planner_node,
    synthesizer_node,
    ask_for_images_node,
)

from tools import (
    get_travel_recommendations,
    search_travel_destinations,
    get_weather,
    get_restaurants,
    get_attractions,
    plan_route,
    search_images,
)

from llm_model import get_llm


def create_travel_workflow():
    llm = get_llm()

    tools = [
        get_travel_recommendations,
        search_travel_destinations,
        get_weather,
        get_restaurants,
        get_attractions,
    ]

    llm_tools = llm.bind_tools(tools)
    llm_route = llm.bind_tools(tools + [plan_route])

    workflow = StateGraph(TravelState)

    workflow.add_node("coordinator", lambda s: coordinator_node(s, llm))
    workflow.add_node("research_agent", lambda s: research_agent_node(s, llm_tools))
    workflow.add_node("trip_planner", lambda s: trip_planner_node(s, llm_tools))
    workflow.add_node("weather_analyst", lambda s: weather_analyst_node(s, llm_tools))
    workflow.add_node("accommodation_specialist", lambda s: accommodation_specialist_node(s, llm_tools))
    workflow.add_node("restaurant_suggester", lambda s: restaurant_suggester_node(s, llm_tools))
    workflow.add_node("route_planner", lambda s: route_planner_node(s, llm_route))

    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("route_tools", ToolNode(tools + [plan_route]))

    workflow.add_node("synthesizer", lambda s: synthesizer_node(s, llm))
    workflow.add_node("ask_for_images", ask_for_images_node)
    workflow.add_node("images", ToolNode([search_images]))

    workflow.add_edge(START, "coordinator")

    workflow.add_conditional_edges(
        "coordinator",
        route_after_coordinator,
        {
            "research_agent": "research_agent",
            "trip_planner": "trip_planner",
            "weather_analyst": "weather_analyst",
            "accommodation_specialist": "accommodation_specialist",
            "restaurant_suggester": "restaurant_suggester",
            "route_planner": "route_planner",
        },
    )

    workflow.add_conditional_edges(
        "route_planner",
        route_after_route_planner,
        {"route_tools": "route_tools", "__end__": END},
    )
    workflow.add_edge("route_tools", END)

    workflow.add_conditional_edges(
        "research_agent",
        route_after_research_agent,
        {"tools": "tools", "trip_planner": "trip_planner", "synthesizer": "synthesizer"},
    )

    for agent in [
        "trip_planner",
        "weather_analyst",
        "accommodation_specialist",
        "restaurant_suggester",
    ]:
        workflow.add_conditional_edges(
            agent,
            route_after_specialist,
            {"tools": "tools", "synthesizer": "synthesizer"},
        )

    workflow.add_conditional_edges(
        "tools",
        should_continue_after_tools,
        {"trip_planner": "trip_planner", "synthesizer": "synthesizer"},
    )

    # NEW: Conditional routing from synthesizer
    workflow.add_conditional_edges(
        "synthesizer",
        route_after_synthesizer,
        {"ask_for_images": "ask_for_images", "__end__": END},
    )
    
    workflow.add_edge("images", END)

    memory = MemorySaver()
    return workflow.compile(
        # checkpointer=memory,
        interrupt_before=["ask_for_images"],
    )