import json
import re
from typing import Dict
from llm import get_llm
from travel_preference import TravelPreference
from utils import content_correction
from travelState import TravelState


def query_agent(state: TravelState) -> Dict:
    """Extract structured travel preferences from user query"""
    
    llm = get_llm()
    
    if state.get("user_query"):
        query = state["user_query"]
        
        weather_keywords = ['weather', 'climate', 'temperature', 'forecast', 'rainfall', 
                           'sunny', 'rainy', 'humid', 'conditions']
        
        query_lower = query.lower()
        
        contains_weather = any(keyword in query_lower for keyword in weather_keywords)
            
        parse_prompt = f"""Extract travel information from this query and return ONLY a JSON object.

Query: "{query}"

Return JSON with these exact fields:
{{
  "budget_max": number or null,
  "activities": list of strings,
  "travel_month": string or null,
  "destination_state": list of strings,
  "destination_country": list of strings,
  "weather": boolean
}}

Rules for extraction:
1. WEATHER DETECTION:
   - If the query contains words like: weather, climate, temperature, forecast, rainfall → set weather to true
   - If the query is asking "what is the weather" or "how is the climate" → set weather to true
   - Examples: "weather of India" → weather: true, "climate in Paris" → weather: true
   
2. LOCATION DETECTION:
   - "Paris" → add "France" to destination_country
   - "London" → add "United Kingdom" to destination_country
   - "Tokyo" → add "Japan" to destination_country
   - "New York" → add "United States" to destination_country and "New York" to destination_state
   - "India" → add "India" to destination_country
   
3. OTHER FIELDS:
   - Extract any budget numbers mentioned
   - Extract activities (beach, hiking, shopping, cultural, adventure, etc.)
   - Extract months or seasons

CRITICAL: The "weather" field MUST be a boolean value (true or false), NOT a string.

For this specific query, weather should be: {str(contains_weather).lower()}

Output ONLY valid JSON, no explanation:"""
        
        response = llm.invoke(parse_prompt)
        
        content = response.content.strip()
        
        content = content_correction(content)
    
        raw_result = json.loads(content.strip())
        
        # Force weather flag if detected in pre-check (override LLM if needed)
        if contains_weather:
            raw_result["weather"] = True
        
        try:
            validated = TravelPreference.model_validate(raw_result)
            user_preferences = validated

            print(
                f"Parsed Successfully: "
                f"Budget={user_preferences.budget_max or 'Any'}, "
                f"Activities={user_preferences.activities}, "
                f"Month={user_preferences.travel_month}, "
                f"States={user_preferences.destination_state}, "
                f"Countries={user_preferences.destination_country}, "
                f"Weather={user_preferences.weather}"
            )
        except Exception as e:
            print(f"Validation error: {e}")
            user_preferences = TravelPreference()
                
    else:
        user_preferences = TravelPreference()
    
    return {
        "user_preferences": user_preferences,
        "messages": [
            {
                "role": "assistant",
                "content": f"Query Agent: Extracted preferences - Countries: {user_preferences.destination_country}, Budget: {user_preferences.budget_max}, Weather Query: {user_preferences.weather}"
            }
        ],
        "next_agent": "supervisor"
    }