from typing import Dict
from travelState import TravelState
from tools.web_weather_search import search_destination_weather
from langchain_core.messages import AIMessage


def weather_agent(state: TravelState) -> Dict:
    """
    Fetches weather information for recommended destinations
    Called by supervisor when weather context is needed
    """
    
    user_preferences = state.get("user_preferences", {})
    travel_month = user_preferences.travel_month or ""
    
    # Determine destination from user preferences
    destination = None
    if user_preferences.destination_state and len(user_preferences.destination_state) > 0:
        destination = user_preferences.destination_state[0]
    elif user_preferences.destination_country and len(user_preferences.destination_country) > 0:
        destination = user_preferences.destination_country[0]
    
    if not destination:
        return {
            "weather_results": {
                "success": False,
                "error": "No destination identified in query",
                "weather_info": {},
                "attempted": True
            },
            "messages": [AIMessage(content="Weather Agent: No destination specified for weather check")],
            "next_agent": "supervisor",
            "task_complete": False
        }
    
    
    try:
        weather_data = search_destination_weather.invoke({
            "destination": destination,
            "travel_month": travel_month
        })
        
        if weather_data.get("success"):
            weather_info = weather_data.get("weather_info", {})
            
            
            message = (
                f"Weather Agent: Retrieved climate info for {destination} - "
                f"{weather_info.get('temperature_range', 'N/A')}, "
                f"{weather_info.get('conditions', 'N/A')}"
            )
            
            recommendations_count = (
                len(state.get("database_results", [])) +
                len(state.get("web_search_results", [])) +
                len(state.get("pdf_results", []))
            )
            
            task_complete = recommendations_count == 0
            
        else:
            message = f"Weather Agent: Could not fetch weather for {destination}"
            task_complete = False
        
        return {
            "weather_results": weather_data,
            "messages": [AIMessage(content=message)],
            "next_agent": "supervisor",
            "task_complete": task_complete
        }
        
    except Exception as e:
        return {
            "weather_results": {
                "success": False,
                "error": str(e),
                "weather_info": {},
                "attempted": True
            },
            "messages": [AIMessage(content=f"Weather Agent: Error - {str(e)}")],
            "next_agent": "supervisor",
            "task_complete": False
        }