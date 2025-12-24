import json
import os
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from llm import get_llm
from utils import content_correction
from travel_preference import TravelPreference

@tool
def search_travel_destinations(user_preferences : TravelPreference):
    """Search web for travel destinations based on preferences"""
    
    try:
        
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return {"error": "Tavily API key not found", "destinations": [], "success": False}
        
        tavily_search = TavilySearch(max_results=5, api_key=tavily_key)
        llm = get_llm()
        
        budget = user_preferences.budget_max
        activities = user_preferences.activities
        states = user_preferences.destination_state
        countries = user_preferences.destination_country
        month = user_preferences.travel_month
        
        
        query_parts = ["best travel destinations"]
        
        if states:
                query_parts.append(" ".join(states))
            
        if countries:
            query_parts.append(" ".join(countries))
        
        if month:
            query_parts.append(f"in {month}")
        
        if activities:
            query_parts.append(" ".join(activities[:])) 
        
        if budget:
            if budget < 50000:
                query_parts.append("budget friendly")
            elif budget < 100000:
                query_parts.append("moderate budget")
        
        search_query = " ".join(query_parts)
        
        # Perform search
        search_results = tavily_search.invoke({"query": search_query})
        
        web_search_prompt = f"""Extract travel destinations from these search results.

        User Preferences:
        - Budget: {budget or 'Any'} rupees
        - States: {', '.join(states) if states else 'Any'}
        - Countries: {', '.join(countries) if countries else 'Any'}
        - Activities: {', '.join(activities) if activities else 'Any'}
        - Month: {month or 'Any'}

        Search Results:
        {str(search_results)[:3000]}

        Return ONLY valid JSON with 5-7 destinations:
        {{
            "destinations": [
                {{
                    "name": "destination name",
                    "country": "country",
                    "estimated_cost": 50000,
                    "description": "brief description",
                    "activities": ["activity1", "activity2"],
                    "best_season": "season",
                    "source_url": "url"
                }}
            ]
        }}

        Rules:
        - Only include destinations from search results
        - Match user's region preference
        - Include realistic costs
        - Return ONLY JSON

        JSON:"""
            
            
        response = llm.invoke(web_search_prompt)
        content = response.content.strip()
        
        content = content_correction(content)
            
        result = json.loads(content.strip())
        
        return {
            "destinations": result.get("destinations", []),
            "success": True,
            "source": "web_search",
            "count": len(result.get("destinations", [])),
            "search_query": search_query
        }
            
    except Exception as e:
        return {
            "error": str(e),
            "destinations": [],
            "success": False,
            "source": "error"
        }
        
    
    
    
    