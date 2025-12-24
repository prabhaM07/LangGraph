from typing import Dict, List
from travelState import TravelState
from langchain_core.messages import AIMessage, SystemMessage
from utils import generate_final_result
from llm import get_llm
import json

def supervisor_agent(state: TravelState) -> Dict:
    """
    TRUE SUPERVISOR: Intelligently dispatches to agents based on needs
    Makes parallel decisions and re-evaluates after each completion
    """
    
    user_query = state.get("user_query")
    user_preferences = state.get("user_preferences")
    pdf_results = state.get("extracted_data", {})
    db_results = state.get("db_results", {})
    web_results = state.get("web_results", {})
    weather_results = state.get("weather_results", {})
    
    # Count results from each source
    pdf_count = len(pdf_results.get("packages", [])) if pdf_results else 0
    db_count = db_results.get("count", 0) if db_results and db_results.get("success") else 0
    web_count = len(web_results.get("destinations", [])) if web_results and web_results.get("success") else 0
    has_weather = bool(weather_results and weather_results.get("success"))
    
    total_results = pdf_count + db_count + web_count
    
    print(f"\n{'='*70}")
    print(f" SUPERVISOR RE-EVALUATION")
    print(f"{'='*70}")
    print(f"Query: '{user_query}'")
    print(f"Results Summary:")
    print(f"  • PDF Packages: {pdf_count}")
    print(f"  • Database: {db_count}")
    print(f"  • Web Search: {web_count}")
    print(f"  • Weather: {'✓' if has_weather else '✗'}")
    print(f"  • TOTAL: {total_results} destinations")
    
    agents_completed = []
    if state.get("extracted_data"):
        agents_completed.append("extractor")
    if state.get("db_results"):
        agents_completed.append("analyst")
    if state.get("web_results"):
        agents_completed.append("search")
    if state.get("weather_results"):
        agents_completed.append("weather")
        
    print(f"\nCompleted Agents: {', '.join(agents_completed) if agents_completed else 'None'}")
    print(f"{'='*70}\n")
    
    # Check if this is a weather-only query
    is_weather_only_query = (
        user_preferences.weather and 
        has_weather and 
        total_results == 0 and
        'weather' in agents_completed
    )
    
    if is_weather_only_query:
        # Weather-only query completed
        final_result = generate_final_result(state)
        
        return {
            "messages": [AIMessage(content="Supervisor: Weather information retrieved successfully")],
            "final_result": final_result,
            "task_complete": True,
            "next_agent": "end"
        }
    
    decision = _supervisor_llm_decision(
        state=state,
        total_results=total_results,
        agents_completed=agents_completed
    )
    
    if decision['next_agent'] == 'finalize':
        final_result = generate_final_result(state)
        
        return {
            "messages": [AIMessage(content="Supervisor: All necessary data gathered, finalizing recommendations")],
            "final_result": final_result,
            "task_complete": True,
            "next_agent": "end"
        }
    
    return {
        "messages": [AIMessage(content=f"Supervisor: Dispatching to {decision['next_agent']}")],
        "next_agent": decision['next_agent'],
        "supervisor_notes": decision['reasoning']
    }
    
def _supervisor_llm_decision(
    state: TravelState,
    total_results: int,
    agents_completed: List[str]
) -> Dict:
    """
    Use LLM to intelligently decide the next best agent to call
    Key insight: Supervisor makes context-aware decisions, not sequential routing
    """
    try:
        llm = get_llm()
        user_preferences = state.get("user_preferences")
        
        available_agents = []
        
        if state.get('pdf_path') and 'extractor' not in agents_completed:
            available_agents.append("extractor")
        
        if 'analyst' not in agents_completed:
            available_agents.append("analyst")
        
        if 'search' not in agents_completed:
            available_agents.append("search")
        
        if user_preferences.weather and 'weather' not in agents_completed:
            available_agents.append("weather")
            
        if not available_agents:
            return {
                'next_agent': 'finalize',
                'reasoning': f'All agents completed. Total results: {total_results}'
            }
            
        # If we have weather data and no travel recommendations are needed, finalize
        has_weather = bool(state.get("weather_results", {}).get("success"))
        if has_weather and total_results == 0 and user_preferences.weather:
            return {
                'next_agent': 'finalize',
                'reasoning': 'Weather-only query completed'
            }
            
        if total_results >= 5 and (not user_preferences.weather or has_weather):
            return {
                'next_agent': 'finalize',
                'reasoning': f'Sufficient data: {total_results} destinations'
            }
        
        budget = user_preferences.budget_max
        activities = user_preferences.activities
        states = user_preferences.destination_state
        countries = user_preferences.destination_country
        month = user_preferences.travel_month
        user_query = state.get('user_query', '')
        
        decision_making_prompt = f"""You are a travel recommendation supervisor coordinating specialized agents.

        USER QUERY: "{user_query}"

        USER PREFERENCES:
        - Countries: {countries or 'Any'}
        - States: {states or 'Any'}
        - Month: {month or 'Any'}
        - Budget: ₹{budget if budget else 'Any'}
        - Activities: {activities or 'Any'}
        - Weather Info Requested: {user_preferences.weather}

        AGENTS COMPLETED: {agents_completed or 'None'}
        AVAILABLE AGENTS: {available_agents}

        CURRENT RESULTS:
        - PDF Catalog: {state.get('extracted_data', {}).get('total_packages', 0)} packages
        - Database: {state.get('db_results', {}).get('count', 0)} matches
        - Web Search: {len(state.get('web_results', {}).get('destinations', [])) if state.get('web_results') else 0} destinations
        - Weather Info: {'Available' if has_weather else 'Not fetched'}
        - TOTAL: {total_results} destinations

        YOUR TASK: Choose the BEST next agent to improve recommendation quality.

        AGENT CAPABILITIES:
        1. "extractor" - Extracts curated packages from PDF catalog (high quality, limited quantity)
        2. "analyst" - Queries structured database (precise matches, validated data)
        3. "search" - Web search for destinations (broad coverage, current info)
        4. "weather" - Fetches weather/climate info for destination (essential for travel planning)
        5. "finalize" - Generate final recommendations (call when sufficient data gathered)

        DECISION LOGIC:
        - If user ONLY asked about weather AND weather fetched: finalize immediately
        - If total_results >= 5 AND (weather fetched OR not needed): finalize
        - If PDF available and not extracted: prioritize extractor (high-quality curated data)
        - If need precise matches (specific countries/budget): call analyst
        - If results < 3: call search (broad coverage)
        - If user asks about weather/climate OR specific destinations found: call weather
        - If weather needed but not fetched AND have destinations: call weather
        - If all data agents done: finalize

        RESPOND WITH JSON ONLY (no markdown):
        {{"next_agent": "extractor"|"analyst"|"search"|"weather"|"finalize", "reasoning": "1-2 sentence explanation"}}"""

        response = llm.invoke([SystemMessage(content=decision_making_prompt)])
        content = response.content.strip()
        
        # Clean markdown blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        decision = json.loads(content)
        
        # Validate decision
        chosen_agent = decision['next_agent']
        
        if chosen_agent == 'finalize':
            return decision
        
        if chosen_agent not in available_agents:
            fallback = available_agents[0] if available_agents else 'finalize'
            return {
                'next_agent': fallback,
                'reasoning': f"LLM error: {chosen_agent} unavailable, using {fallback}"
            }
            
        return decision
        
    except Exception as e:        
        fallback = available_agents[0] if available_agents else 'finalize'
        return {
            'next_agent': fallback,
            'reasoning': f'LLM error, defaulting to {fallback}'
        }