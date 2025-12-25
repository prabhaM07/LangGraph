from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from travelState import TravelState
from typing import Literal

# System messages for different agents
COORDINATOR_PROMPT = """You are a travel planning coordinator. Analyze the user's query carefully and call ONLY ONE relevant tool.

Available tools:
- get_weather(city): Get weather for a specific city. Use when asked about weather/temperature/climate.
  Example: "weather in Paris" → call get_weather with city="Paris"
  
- get_travel_news(destination): Get travel news. Use when asked about news/updates/advisories.
  Example: "news about India" → call get_travel_news with destination="India"
  
- search_travel_destinations(query): Search web for travel info. Use for places, attractions, activities, recommendations.
  Example: "places in Finland" → call search_travel_destinations with query="best places to visit in Finland"
  
- get_travel_recommendations(pdf_path, user_query): Analyze PDF brochure. Use ONLY when PDF is provided.

CRITICAL RULES:
1. Extract the specific location/destination from the user query
2. For travel destination queries: Create ONE SIMPLE search query
3. NEVER call multiple tools for the same query
4. If user asks for travel destinations, use ONLY search_travel_destinations

Examples:
- "weather in Shimla" → get_weather(city="Shimla")
- "news of India" → get_travel_news(destination="India")
- "places to travel in India" → search_travel_destinations(query="best places to visit in India")
- "I want to travel within India" → search_travel_destinations(query="travel destinations in India")"""

SYNTHESIZER_PROMPT = """You are a travel planning synthesizer. Create a helpful response based ONLY on the tool results provided.

Guidelines:
1. Use ONLY information from the tool results - do not make up information
2. If tools returned errors or no results, acknowledge this clearly
3. Keep responses focused and relevant to the user's specific question
4. Format naturally - use paragraphs for narrative content, lists only when showing multiple items
5. If information is missing, suggest what the user could try instead"""


def coordinator_node(state: TravelState, llm_with_tools) -> TravelState:
    """Coordinator agent that determines which tools to call"""
    
    # Build context message
    context = f"User Query: {state['user_query']}"
    
    if state.get("pdf_path"):
        context += f"\nPDF Available at: {state['pdf_path']}"
    
    messages = [
        SystemMessage(content=COORDINATOR_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = llm_with_tools.invoke(messages)
    
    # Log which tools were called
    tool_calls_made = []
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_calls_made = [tc["name"] for tc in response.tool_calls]
    
    log_msg = f"Coordinator: Selected tools: {', '.join(tool_calls_made)}" if tool_calls_made else "Coordinator: No tools needed"
    
    return {
        "messages": [response],
        "agent_messages": state.get("agent_messages", []) + [log_msg]
    }


def synthesizer_node(state: TravelState, llm) -> TravelState:
    """Synthesizes tool results into final recommendation"""
    
    # Extract tool results from messages
    tool_results = []
    for msg in state["messages"]:
        if isinstance(msg, ToolMessage):
            tool_results.append(f"Tool: {msg.name}\nResult: {msg.content}")
    
    if not tool_results:
        # No tools were executed, likely no relevant tools for the query
        return {
            "messages": [AIMessage(content="I understand your query, but I don't have the right tools to answer it. Could you rephrase or provide more details?")],
            "final_result": "No relevant tools available for this query",
            "task_complete": True,
            "agent_messages": state.get("agent_messages", []) + ["Synthesizer: No tool results to synthesize"]
        }
    
    # Create synthesis prompt
    results_text = "\n\n".join(tool_results)
    
    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=f"""User asked: {state['user_query']}

Tool Results:
{results_text}

Create a helpful response using ONLY the information provided above. If the tools returned errors or no data, acknowledge this and suggest alternatives.""")
    ]
    
    response = llm.invoke(messages)
    
    return {
        "messages": [response],
        "final_result": response.content,
        "task_complete": True,
        "agent_messages": state.get("agent_messages", []) + ["Synthesizer: Created final response"]
    }


def should_continue(state: TravelState) -> Literal["tools", "synthesizer", "__end__"]:
    """Router function to determine next step"""
    
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
    
    last_message = messages[-1]
    
    # If task is complete, end
    if state.get("task_complete"):
        return "__end__"
    
    # If LLM called tools, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # If no tools called, go directly to synthesizer
    return "synthesizer"