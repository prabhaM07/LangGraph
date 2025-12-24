import json
import os
from typing import Any, Dict
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from llm import get_llm
from utils import content_correction

@tool
def search_destination_weather(destination: str, travel_month: str = "") -> Dict[str, Any]:
    """Search for weather information at a specific destination"""
    
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return {"error": "Tavily API key not found", "weather_info": {}, "success": False}
        
        tavily_search = TavilySearch(max_results=3, api_key=tavily_key)
        llm = get_llm()
        
        if travel_month and travel_month.strip():
            search_query = f"{destination} weather in {travel_month} temperature climate"
        else:
            search_query = f"{destination} current weather forecast temperature climate"
        
        # Perform search
        search_results = tavily_search.invoke({"query": search_query})
        
        # Extract weather info using LLM
        web_weather_search_prompt = f"""Extract weather information from these search results for {destination}.

        Travel Month: {travel_month or 'Current/General'}

        Search Results:
        {str(search_results)[:]}

        Return ONLY valid JSON:
        {{
            "destination": "{destination}",
            "temperature_range": "25-30°C",
            "conditions": "sunny/rainy/cloudy",
            "best_time_to_visit": "month/season",
            "rainfall": "low/medium/high",
            "humidity": "percentage or description",
            "travel_advisories": ["advisory1", "advisory2"],
            "summary": "brief weather summary"
        }}

        Rules:
        - Extract actual data from search results
        - Use null for missing information
        - Be specific and accurate
        - Return ONLY JSON

        JSON:"""
        
        response = llm.invoke(web_weather_search_prompt)
        content = response.content.strip()
        content = content_correction(content)
            
        result = json.loads(content.strip())
        
        return {
            "weather_info": result,
            "success": True,
            "source": "weather_search",
            "search_query": search_query
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "weather_info": {},
            "success": False,
            "source": "error"
        }
 