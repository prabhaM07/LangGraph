from langchain_core.messages import AIMessage, ToolMessage
from travelState import TravelState

def _has_tool_calls(msg):
    return isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None)

def route_after_coordinator(state: TravelState) -> str:
    return state.get("next_agent") or "research_agent"


def route_after_route_planner(state: TravelState) -> str:
    messages = state.get("messages", [])
    return "route_tools" if messages and _has_tool_calls(messages[-1]) else "__end__"


def route_after_research_agent(state: TravelState) -> str:
    messages = state.get("messages", [])
    last = messages[-1] if messages else None

    if _has_tool_calls(last):
        return "tools"

    if state.get("next_agent") == "trip_planner":
        return "trip_planner"

    return "synthesizer"


def route_after_specialist(state: TravelState) -> str:
    messages = state.get("messages", [])
    last = messages[-1] if messages else None

    if _has_tool_calls(last):
        tool_calls = sum(
            1 for m in messages if _has_tool_calls(m)
        )
        return "tools" if tool_calls <= 2 else "synthesizer"

    return "synthesizer"


def should_continue_after_tools(state: TravelState) -> str:
    messages = state.get("messages", [])

    if sum(isinstance(m, ToolMessage) for m in messages) > 5:
        return "synthesizer"

    if state.get("next_agent") == "trip_planner":
        state["next_agent"] = None
        return "trip_planner"

    return "synthesizer"
