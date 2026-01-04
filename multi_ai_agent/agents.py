from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from utils.user_query import get_user_query
from travelState import TravelState
from langgraph.types import interrupt, Command
from typing import Literal
import re
import json

# ============================================================================
# AGENT PROMPTS
# ============================================================================

COORDINATOR_PROMPT = """You are an intelligent travel planning coordinator.

Your job: Analyze the query and extract TWO things:
1. **next_agent**: Which agent should handle this query
2. **location**: The destination/location (if any)

Available agents:
- research_agent: For ALL trip planning queries (ALWAYS FIRST for any trip planning)
- weather_analyst: Weather/climate information only
- accommodation_specialist: Hotel recommendations only
- route_planner: Directions/routes only
- restaurant_suggester: Restaurant recommendations only

CRITICAL ROUTING RULES:
1. ANY trip planning query (plan, itinerary, visit, tour, package) → research_agent
2. Trip planner is called AFTER research_agent completes (you never call it directly)
3. Single-purpose queries (just weather/hotels/routes/restaurants) → specific agent

LOCATION EXTRACTION:
- Extract the destination city/place from the query
- If no specific location mentioned → return "Not specified"
- Be smart: "Kashmir trip" → location is "Kashmir"
- "Plan my honeymoon" → location is "Not specified" (user hasn't said where)

Respond in JSON format:
{
  "next_agent": "agent_name",
  "location": "extracted location or 'Not specified'",
  "reasoning": "brief explanation"
}

Examples:
Query: "Plan a 5 day trip to Manali"
Response: {"next_agent": "research_agent", "location": "Manali", "reasoning": "Trip planning query with specified destination"}

Query: "What's the weather in Tokyo?"
Response: {"next_agent": "weather_analyst", "location": "Tokyo", "reasoning": "Weather-specific query"}

Query: "Suggest restaurants in Ooty"
Response: {"next_agent": "restaurant_suggester", "location": "Ooty", "reasoning": "Restaurant query for Ooty"}

Query: "I want to visit Kerala beaches"
Response: {"next_agent": "research_agent", "location": "Kerala", "reasoning": "Trip planning query about Kerala"}"""

RESEARCH_AGENT_PROMPT = """Travel Research Specialist.

Process:
1. If PDF: Call get_travel_recommendations
2. No PDF: Call search_travel_destinations
3. Extract key info about destination

AFTER research complete, you MUST indicate trip_planner as next agent for trip planning queries.

Tools: get_travel_recommendations, search_travel_destinations"""

TRIP_PLANNER_PROMPT = """Trip Planning Agent.

CRITICAL RULES:
1. Check research data from previous agent (in messages)
2. Location is already extracted by coordinator
3. Determine if days specified
4. Call get_weather ONLY if location is known
5. Create plan using research data

PLANNING:
- Days specified → Day-wise (Day 1, Day 2...)
- No days → General plan (NO Day 1, Day 2)

IMPORTANT LOOP PREVENTION:
- If location is None/empty → DO NOT call get_weather, skip to planning
- If get_weather already failed → DO NOT retry, use research data only
- NEVER call same tool twice in a row
- Maximum 1 tool call, then create plan

Tools: get_weather (optional, only if location known)"""

WEATHER_ANALYST_PROMPT = """Weather Analyst.

Provide weather and climate information.

Tools: get_weather"""

ACCOMMODATION_SPECIALIST_PROMPT = """Accommodation Expert.

Provide hotel recommendations.

Tools: search_travel_destinations"""

ROUTE_PLANNER_PROMPT = """Route Planner.

Plan routes between locations.

Tools: plan_route"""

RESTAURANT_SUGGESTER_PROMPT = """Restaurant Specialist.

CRITICAL: ALWAYS call get_restaurants tool with the location from the user query.
NEVER use cached data. ALWAYS fetch fresh restaurant data.

Provide restaurant recommendations for the specified location.

Tools: get_restaurants"""

SYNTHESIZER_PROMPT = """Final Travel Plan Synthesizer.

CRITICAL: Create plan ONLY from tool results provided for THE CURRENT QUERY LOCATION.

Rules:
1. PDF data (get_travel_recommendations) → Use ONLY those packages/destinations
2. Web search → Use search results
3. Weather data → Include weather info
4. Restaurant data → Use ONLY restaurant tool results for THIS query's location
5. Days specified → Day-wise plan with "Day 1:", "Day 2:" format
6. No days → General plan (list packages/attractions, NO "Day 1, Day 2")

NEVER invent destinations not in tool results.
NEVER add generic information not from tools.
NEVER use cached data from previous queries about DIFFERENT locations.

Match query type:
- Restaurant only → Only restaurants FROM TOOL RESULTS for current location
- Weather only → Only weather  
- Trip with days → Day-wise plan
- Trip without days → List packages/attractions from PDF or search results
- route only -> only route
Be concise and factual."""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_days_from_query(query: str) -> int:
    """Extract days. Returns 0 if not specified."""
    patterns = [r'(\d+)\s*day', r'(\d+)-day', r'(\d+)d\s+trip']
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            return int(match.group(1))
    if 'week' in query.lower():
        return 7
    return 0

def is_trip_planning_query(query: str) -> bool:
    """Check if trip planning query"""
    keywords = ['plan', 'itinerary', 'schedule', 'trip', 'visit', 'travel to', 'package', 'tour']
    return any(kw in query.lower() for kw in keywords)

def get_current_query_index(state: TravelState) -> int:
    """Get index where current query starts in message history"""
    messages = state.get("messages", [])
    current_query = state.get("user_query", "")
    
    # Find the last occurrence of a HumanMessage with the current query
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            if current_query in messages[i].content:
                return i
    return 0

def get_tool_results_for_current_query(state: TravelState) -> dict:
    """Get ONLY tool results from current query (after current query started)"""
    messages = state.get("messages", [])
    current_location = state.get("travel_location") or ""
    current_location_lower = current_location.lower() if current_location else ""
    
    # Find where current query starts
    query_start_idx = get_current_query_index(state)
    
    # Get tool results ONLY after current query started
    current_results = {}
    
    for i in range(query_start_idx, len(messages)):
        msg = messages[i]
        if isinstance(msg, ToolMessage):
            tool_name = msg.name
            
            # For restaurant queries, verify location matches
            if tool_name == "get_restaurants":
                content_lower = msg.content.lower()
                # Check if the location in tool result matches current query location
                if current_location_lower and current_location_lower in content_lower:
                    current_results[tool_name] = msg.content
                # If no location specified, still use it but mark as potentially wrong
                elif not current_location_lower:
                    current_results[tool_name] = msg.content
            else:
                # For other tools, just use latest from current query
                current_results[tool_name] = msg.content
    
    return current_results

def has_tool_been_called(state: TravelState, tool_name: str) -> bool:
    """Check if a tool has already been called IN CURRENT QUERY"""
    query_start_idx = get_current_query_index(state)
    messages = state.get("messages", [])
    
    for i in range(query_start_idx, len(messages)):
        if isinstance(messages[i], ToolMessage) and messages[i].name == tool_name:
            return True
    return False

def get_research_data(state: TravelState) -> str:
    """Get research data from current query"""
    query_start_idx = get_current_query_index(state)
    messages = state.get("messages", [])
    
    data = []
    for i in range(query_start_idx, len(messages)):
        msg = messages[i]
        if isinstance(msg, ToolMessage):
            if msg.name == "get_travel_recommendations":
                data.append(f"PDF: {msg.content[:800]}")
            elif msg.name == "search_travel_destinations":
                data.append(f"Web: {msg.content[:600]}")
    return "\n".join(data) if data else "No research data"

def has_pdf_data(state: TravelState) -> bool:
    """Check if PDF recommendations exist in current query messages"""
    query_start_idx = get_current_query_index(state)
    messages = state.get("messages", [])
    
    for i in range(query_start_idx, len(messages)):
        if isinstance(messages[i], ToolMessage) and messages[i].name == "get_travel_recommendations":
            return True
    return False

def parse_coordinator_response(content: str) -> dict:
    """Parse coordinator's JSON response safely"""
    try:
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    # Fallback: parse manually
    result = {
        "next_agent": "research_agent",
        "location": "Not specified",
        "reasoning": "Default routing"
    }
    
    content_lower = content.lower()
    
    # Extract agent
    agent_keywords = {
        "research": "research_agent",
        "weather": "weather_analyst",
        "accommodation": "accommodation_specialist",
        "hotel": "accommodation_specialist",
        "route": "route_planner",
        "restaurant": "restaurant_suggester"
    }
    
    for keyword, agent in agent_keywords.items():
        if keyword in content_lower:
            result["next_agent"] = agent
            break
    
    # Try to extract location (look for quoted text or capitalized words)
    location_match = re.search(r'"location":\s*"([^"]+)"', content)
    if location_match:
        result["location"] = location_match.group(1)
    
    return result

# ============================================================================
# AGENT NODES
# ============================================================================

def coordinator_node(state: TravelState, llm) -> TravelState:
    """Smart coordinator that extracts location and routes to appropriate agent"""
    user_query = get_user_query(state)
    pdf_path = state.get("pdf_path", "")
    
    # Build context for coordinator
    context = f"""User Query: "{user_query}"
PDF Available: {"Yes" if pdf_path else "No"}

Analyze this query and determine:
1. Which agent should handle it?
2. What is the destination/location (if any)?"""
    
    messages = [
        SystemMessage(content=COORDINATOR_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = llm.invoke(messages)
    
    # Parse coordinator's decision
    decision = parse_coordinator_response(response.content)
    
    next_agent = decision.get("next_agent", "research_agent")
    location = decision.get("location", "Not specified")
    reasoning = decision.get("reasoning", "")
    
    # If location is generic, set to None
    if location in ["Not specified", "none", "unknown", ""]:
        location = None
    
    # IMPORTANT: Clear old cached data when starting new query
    return {
        "messages": [response],
        "next_agent": next_agent,
        "travel_location": location,
        "restaurant_results": None,
        "attraction_results": None,
        "weather_results": None,
        "trip_planner_called": False,  # NEW: Reset flag for each query
        "agent_messages": state.get("agent_messages", []) + [
            f"→ {next_agent} | Location: {location or 'Not specified'} | {reasoning[:50]}"
        ]
    }

def research_agent_node(state: TravelState, llm_with_tools) -> TravelState:
    """Research specialist"""
    user_query = get_user_query(state)
    pdf_path = state.get("pdf_path", "")
    location = state.get("travel_location")
    is_planning = is_trip_planning_query(user_query)
    
    # Concise prompt
    if pdf_path:
        content = f"Extract info: {user_query[:100]}\n"
        content += f"Location: {location or 'Check query'}\n"
        content += f"Call get_travel_recommendations(pdf_path='{pdf_path}', user_query='{user_query[:80]}')"
    else:
        content = f"Research: {user_query[:100]}\n"
        content += f"Location: {location or 'Extract from query'}\n"
        content += "Use search_travel_destinations"
    
    messages = [
        SystemMessage(content=RESEARCH_AGENT_PROMPT),
        HumanMessage(content=content)
    ]
    
    response = llm_with_tools.invoke(messages)
    
    # Set next_agent to trip_planner if trip planning
    next_agent = "trip_planner" if is_planning else None
    
    return {
        "messages": [response],
        "next_agent": next_agent,
        "agent_messages": state.get("agent_messages", []) + ["→ Research complete"]
    }

def trip_planner_node(state: TravelState, llm_with_tools) -> TravelState:
    """Plans trip - PREVENTS INFINITE LOOPS"""
    user_query = get_user_query(state)
    location = state.get("travel_location")  
    num_days = extract_days_from_query(user_query)
    
    # Get research data
    research_data = get_research_data(state)
    
    # Check if get_weather already failed in current query
    weather_failed = has_tool_been_called(state, "get_weather")
    
    # Determine if we should call get_weather
    should_call_weather = (
        location is not None 
        and location != "None"
        and location != "Not specified"
        and not weather_failed
    )
    
    # Planning instruction
    if num_days > 0:
        plan_type = f"{num_days}-day itinerary with Day 1, Day 2 structure"
    else:
        plan_type = "General plan (attractions by category, NO Day 1, Day 2)"
    
    # Build concise content
    content = f"""Plan trip: {user_query[:80]}
Location: {location or "Not specified"}
Days: {num_days if num_days > 0 else "Not specified"}

Research Data:
{research_data[:800]}

Create: {plan_type}

CRITICAL LOOP PREVENTION:
"""
    
    if should_call_weather:
        content += f"- Call get_weather(city='{location}') ONCE only\n"
    else:
        content += f"- SKIP get_weather (location={'missing' if not location else 'weather already attempted'})\n"
    
    content += """- Then create plan immediately
- DO NOT retry failed tools
- Maximum 1 tool call total"""
    
    messages = [
        SystemMessage(content=TRIP_PLANNER_PROMPT),
        HumanMessage(content=content)
    ]
    
    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "trip_planner_called": True, 
        "agent_messages": state.get("agent_messages", []) + [f"→ Planning ({plan_type[:30]})"]
    }

def weather_analyst_node(state: TravelState, llm_with_tools) -> TravelState:
    """Weather analysis"""
    user_query = get_user_query(state)
    location = state.get("travel_location") 
    
    content = f"Weather for: {user_query[:80]}\nLocation: {location or 'Extract from query'}\n\nCALL get_weather tool now."
    
    messages = [
        SystemMessage(content=WEATHER_ANALYST_PROMPT),
        HumanMessage(content=content)
    ]
    
    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "agent_messages": state.get("agent_messages", []) + ["→ Weather"]
    }

def accommodation_specialist_node(state: TravelState, llm_with_tools) -> TravelState:
    """Accommodation"""
    user_query = get_user_query(state)
    location = state.get("travel_location")
    
    content = f"Hotels: {user_query[:80]}\nLocation: {location or 'Check query'}"
    
    messages = [
        SystemMessage(content=ACCOMMODATION_SPECIALIST_PROMPT),
        HumanMessage(content=content)
    ]
    
    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "agent_messages": state.get("agent_messages", []) + ["→ Hotels"]
    }

def route_planner_node(state: TravelState, llm_with_tools) -> TravelState:
    """
    Route planning - SEPARATE FLOW that goes directly to END
    Displays route info immediately without going through synthesizer
    
    CRITICAL FIX: More explicit prompt to force correct tool call format
    """
    user_query = get_user_query(state)
    
    # Extract origin and destination with regex as backup
    import re
    
    # Try to extract from patterns like "from X to Y"
    from_to_pattern = r'from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s|$|,|\.)'
    match = re.search(from_to_pattern, user_query.lower())
    
    if match:
        origin = match.group(1).strip().title()
        destination = match.group(2).strip().title()
        
        content = f"""User wants route information.

EXTRACTED DATA:
- Origin: {origin}
- Destination: {destination}

TASK: Call the plan_route tool with these EXACT parameters:
- origin: "{origin}"
- destination: "{destination}"

Call it NOW using proper tool format."""
    else:
        # If pattern doesn't match, let LLM extract
        content = f"""Extract route information from this query: "{user_query}"

INSTRUCTIONS:
1. Identify the ORIGIN (starting point)
2. Identify the DESTINATION (ending point)
3. Call plan_route tool with:
   - origin parameter = starting location
   - destination parameter = ending location

Example tool calls:
- Query: "route from Paris to Rome" 
  → Call: plan_route(origin="Paris", destination="Rome")
  
- Query: "how to get from Mumbai to Goa"
  → Call: plan_route(origin="Mumbai", destination="Goa")

Now extract the locations from the user query and call plan_route tool."""
    
    messages = [
        SystemMessage(content=ROUTE_PLANNER_PROMPT),
        HumanMessage(content=content)
    ]
    
    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "task_complete": True,
        "agent_messages": state.get("agent_messages", []) + ["→ Route Planning (direct flow)"]
    }   
    
def restaurant_suggester_node(state: TravelState, llm_with_tools) -> TravelState:
    """Restaurant suggestions - ALWAYS calls tool with fresh location"""
    user_query = get_user_query(state)
    location = state.get("travel_location")
    
    # CRITICAL: Make it clear the tool MUST be called
    if location:
        content = f"""User wants restaurants in: {location}

CRITICAL INSTRUCTION: You MUST call get_restaurants(location_name="{location}", limit=10) tool NOW.

DO NOT use any cached data. DO NOT skip calling the tool. CALL IT NOW."""
    else:
        content = f"""User query: {user_query}

CRITICAL INSTRUCTION: Extract location from query and call get_restaurants tool NOW.

DO NOT use any cached data. ALWAYS call the tool with the extracted location."""
    
    messages = [
        SystemMessage(content=RESTAURANT_SUGGESTER_PROMPT),
        HumanMessage(content=content)
    ]
    
    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "agent_messages": state.get("agent_messages", []) + ["→ Restaurants"]
    }


def ask_for_images_node(state: TravelState) -> Command[Literal["images", "__end__"]]:
    """
    Human-in-the-loop node that asks user if they want to see images
    This node is ONLY called when trip_planner was executed
    Uses LangGraph's interrupt() to pause execution and wait for user response
    """
    # Get location from state
    location = state.get("travel_location", "the destinations")
    
    # Create user-friendly question
    if location and location != "Not specified":
        question = f"Would you like to see photos of {location}?"
    else:
        question = "Would you like to see photos of the destinations?"
    
    # Use interrupt to pause and ask user
    user_response = interrupt({
        "question": question,
        "location": location,
        "options": ["yes", "no"],
        "note": "Travel plan has been generated above"
    })
    
    # Parse user response
    if user_response:
        response_lower = str(user_response).lower().strip()
        
        # Check for affirmative responses
        if any(word in response_lower for word in ["yes", "y", "sure", "ok", "okay", "please", "yep", "yeah"]):
            # User wants images - create AIMessage with tool_calls
            search_query = location if (location and location != "Not specified") else "India travel destinations"
            
            tool_call = {
                "name": "search_images",
                "args": {"location": search_query, "per_page": 10},
                "id": "image_search_001",
                "type": "tool_call"
            }
            
            ai_message = AIMessage(
                content=f"Searching for images of {search_query}...",
                tool_calls=[tool_call]
            )
            
            return Command(
                goto="images",
                update={
                    "messages": [ai_message],
                    "agent_messages": state.get("agent_messages", []) + ["✓ User approved images - fetching..."]
                }
            )
    
    # User said no or didn't respond properly - go to end
    return Command(
        goto="__end__",
        update={
            "agent_messages": state.get("agent_messages", []) + ["✓ User declined images or no response"]
        }
    )

       
def synthesizer_node(state: TravelState, llm) -> TravelState:
    """
    Final plan synthesis - ONLY uses tool results from CURRENT query
    NOW this result will be displayed BEFORE asking about images
    """
    user_query = get_user_query(state)
    num_days = extract_days_from_query(user_query)
    pdf_data_exists = has_pdf_data(state)
    location = state.get("travel_location", "")
    
    # Detect query type
    query_lower = user_query.lower()
    if "restaurant" in query_lower or "food" in query_lower or "dining" in query_lower:
        query_type = "restaurant_only"
    elif "route" in query_lower or "direction" in query_lower or "how to get" in query_lower or "travel from" in query_lower:
        query_type = "route_only"
    elif "weather" in query_lower or "climate" in query_lower or "temperature" in query_lower:
        query_type = "weather_only"
    elif "hotel" in query_lower or "accommodation" in query_lower or "stay" in query_lower:
        query_type = "accommodation_only"
    elif num_days > 0:
        query_type = "trip_with_days"
    else:
        query_type = "trip_general"
    
    # Get ONLY tool results from CURRENT query
    current_tool_results = get_tool_results_for_current_query(state)
    
    # Build tool results section
    tool_results = []
    
    if "get_travel_recommendations" in current_tool_results:
        tool_results.append(f"=== PDF PACKAGES ===\n{current_tool_results['get_travel_recommendations']}")
    
    if "search_travel_destinations" in current_tool_results:
        tool_results.append(f"=== WEB SEARCH ===\n{current_tool_results['search_travel_destinations'][:800]}")
    
    if "get_weather" in current_tool_results:
        tool_results.append(f"=== WEATHER ===\n{current_tool_results['get_weather'][:400]}")
    
    if "get_restaurants" in current_tool_results:
        tool_results.append(f"=== RESTAURANTS ===\n{current_tool_results['get_restaurants'][:1000]}")
    
    if "get_attractions" in current_tool_results:
        tool_results.append(f"=== ATTRACTIONS ===\n{current_tool_results['get_attractions'][:800]}")
    
    if "plan_route" in current_tool_results:
        tool_results.append(f"=== ROUTE ===\n{current_tool_results['plan_route'][:600]}")
    
    # Build context
    context = f"""User Query: {user_query}
Location: {location or "Not specified"}
Query Type: {query_type}
Days Requested: {num_days if num_days > 0 else "Not specified"}

TOOL RESULTS FOR CURRENT QUERY ONLY (location: {location}):
{chr(10).join(tool_results) if tool_results else "No tool results found"}

CRITICAL INSTRUCTIONS:
- Use ONLY the tool results above that match the current query location: {location}
- IGNORE any data from different locations
"""
    
    # Query-type specific instructions
    if query_type == "restaurant_only":
        context += f"""
RESTAURANT-ONLY QUERY:
- Use ONLY the get_restaurants tool results above for {location}
- List restaurants with ratings, cuisine, price range
- DO NOT include weather, routes, or attractions
- DO NOT use old cached data
- If no restaurant data found for {location}, say so clearly"""
    
    elif query_type == "route_only":
        context += f"""
ROUTE-ONLY QUERY:
- Use ONLY the plan_route tool results above
- Provide ONLY route/direction information (distance, duration, transportation modes)
- DO NOT include weather, restaurants, or attractions
- DO NOT add travel tips or suggestions beyond the route
- If no route data found, say so clearly
- Format: Source → Destination, Distance, Duration, Mode"""
    
    elif query_type == "weather_only":
        context += f"""
WEATHER-ONLY QUERY:
- Use ONLY the get_weather tool results above for {location}
- Provide ONLY weather/climate information
- DO NOT include attractions, restaurants, or routes
- If no weather data found for {location}, say so clearly"""
    
    elif query_type == "accommodation_only":
        context += f"""
ACCOMMODATION-ONLY QUERY:
- Use ONLY hotel/accommodation results from search
- Provide ONLY hotel recommendations
- DO NOT include weather, restaurants, or routes
- If no accommodation data found for {location}, say so clearly"""
    
    elif pdf_data_exists:
        context += """
PDF-BASED TRIP PLANNING:
- PDF packages are YOUR ONLY SOURCE
- List packages from PDF that match the query
- Include package names, destinations, activities, pricing
- DO NOT add destinations not in the PDF"""
    
    else:
        context += """
GENERAL TRIP PLANNING:
- Use web search results provided above
- Create plan based on search results only"""
    
    # Day-wise formatting (only for trip planning queries)
    if num_days > 0 and query_type not in ["restaurant_only", "route_only", "weather_only", "accommodation_only"]:
        context += f"\n- Format as {num_days}-day plan with 'Day 1:', 'Day 2:' structure"
    elif query_type not in ["restaurant_only", "route_only", "weather_only", "accommodation_only"]:
        context += "\n- Format as general plan (list packages/attractions, NO 'Day 1, Day 2')"
    
    context += f"\n\nCreate the final response now using ONLY the tool results above for {location}."
    
    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = llm.invoke(messages)
    
    return {
        "messages": [response],
        "final_result": response.content,
        "task_complete": True,
        "agent_messages": state.get("agent_messages", []) + ["✓ Plan generated - ready to ask about images"]
    }