import os
import requests
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from typing import List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
load_dotenv()
# ============================================================================
# PDF EXTRACTION TOOL
# ============================================================================

@tool
async def get_travel_recommendations(pdf_path: str, user_query: str) -> str:
    """
    Analyze travel brochure PDF and provide personalized recommendations.
    """
    try:
        from rag.app import initialize_travel_pipeline

        generator = await initialize_travel_pipeline(pdf_path)
        response = await generator.generate_response(user_query)

        return response

    except FileNotFoundError:
        return f"Error: PDF file not found at {pdf_path}"
    except asyncio.TimeoutError:
        return "Error: PDF processing timed out"
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================================
# WEB SEARCH TOOL
# ============================================================================

@tool
def search_travel_destinations(query: str) -> str:
    """
    Search web for travel information.
    
    Args:
        query: Search query about destinations, activities, or travel tips
    
    Returns:
        Web search results with travel information
    """
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return "Error: Search API not configured"
        
        search = TavilySearch(max_results=4, api_key=tavily_key)
        results = search.invoke(query)
        
        if not results:
            return f"No results found for '{query}'"
        
        output = f"**Search Results for '{query}'**\n\n"
        
        if isinstance(results, dict) and 'results' in results:
            for i, item in enumerate(results['results'][:4], 1):
                title = item.get('title', f'Result {i}')
                content = item.get('content', '')[:300]
                output += f"{i}. **{title}**\n   {content}...\n\n"
        
        elif isinstance(results, list):
            for i, item in enumerate(results[:4], 1):
                if isinstance(item, dict):
                    title = item.get('title', f'Result {i}')
                    content = item.get('content', '')[:300]
                    output += f"{i}. **{title}**\n   {content}...\n\n"
        
        return output
        
    except Exception as e:
        return f"Search error: {str(e)}"

# ============================================================================
# WEATHER TOOL
# ============================================================================

@tool
def get_weather(city: str) -> str:
    """
    Get current weather for a city.
    
    Args:
        city: Name of the city (e.g., 'Paris', 'Tokyo', 'Shimla')
    
    Returns:
        Current weather information including temperature, conditions, and humidity
    """
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY") or "85b1861ce63d879f3c852ee41f6c591b"
        if not api_key:
            return "OPENWEATHER_API_KEY is not set in environment variables."

        url = (
            "http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=metric"
        )

        response = requests.get(url, timeout=10)
        data = response.json()

        if response.status_code == 200:
            temp_c = data["main"]["temp"]
            temp_f = (temp_c * 9 / 5) + 32
            description = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]

            return (
                f"Weather in {city}\n"
                f"{description.capitalize()}\n"
                f"Temperature: {temp_c:.1f}°C ({temp_f:.1f}°F)\n"
                f"Humidity: {humidity}%"
            )
        else:
            return (
                f"Could not fetch weather for {city}. "
                f"Error: {data.get('message', 'Unknown error')}"
            )

    except Exception as e:
        return f"Weather service error: {str(e)}"

# ============================================================================
# Location Images TOOLS
# ============================================================================

import os
import requests
from langchain_core.tools import tool

# ============================================================================
# Location Images TOOL - FIXED WITH DOCSTRING
# ============================================================================

@tool
def search_images(location: str, per_page: int = 10):
    """
    Search for photos of a travel destination using Unsplash API.
    
    Args:
        location: Name of the location/destination to search photos for
        per_page: Number of photos to return (default: 10, max: 30)
    
    Returns:
        List of photo objects with URLs, descriptions, and photographer credits
    """
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {os.getenv('UNSPLASH_ACCESS_KEY','x3RkRGyFPnePlluc-l-wRwG53xXIJ08OqNohrTatDjs')}"}
    params = {
        "query": location,
        "per_page": per_page
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            photos = data.get("results", [])
            
            print(f"Found {len(photos)} images for '{location}':\n")
            
            result_text = f"Found {len(photos)} photos of {location}:\n\n"
            
            for i, photo in enumerate(photos, 1):
                description = photo.get('alt_description') or 'No description'
                photo_url = photo['urls']['regular']
                photographer = photo['user']['name']
                
                print(f"{i}. {description}")
                print(f"   URL: {photo_url}")
                print(f"   Photographer: {photographer}\n")
                
                result_text += f"{i}. {description}\n"
                result_text += f"   URL: {photo_url}\n"
                result_text += f"   Photographer: {photographer}\n\n"
            
            return result_text
        else:
            error_msg = f"Error fetching images: {response.status_code}"
            print(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error searching images: {str(e)}"
        print(error_msg)
        return error_msg

# ============================================================================
# RESTAURANT & ATTRACTION TOOLS
# ============================================================================

API_KEY = os.getenv("RAPIDAPI_KEY", "13f4222a24msh542b69ec8c57350p1ba58bjsn5b46b8e6d7e9")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "travel-advisor.p.rapidapi.com"
}

def convert_price_level(price_level):
    """Convert dollar symbols to descriptive text"""
    price_map = {
        '$': 'Budget',
        '$$ - $$$': 'Moderate',
        '$$$$': 'Expensive'
    }
    return price_map.get(price_level, price_level)

def find_best_location_match(locations, location_name):
    """Find the best matching location from search results.
    Prioritize actual cities/regions over specific venues.
    
    FIXED: Now correctly extracts data from result_object
    """
    
    # Keywords that indicate a specific venue (not a city/region)
    venue_keywords = ['hotel', 'restaurant', 'temple', 'palace', 'museum', 
                      'resort', 'cafe', 'mall', 'airport', 'station',
                      'taj', 'regency', 'marriott', 'hilton', 'hyatt',
                      'radisson', 'andaz', 'oberoi', 'itc', 'leela']
    
    # First pass: Look for geos type (cities/regions)
    for loc in locations:
        result_type = loc.get('result_type', '')
        result_obj = loc.get('result_object', {})
        name = result_obj.get('name', '').lower()
        
        # Prioritize 'geos' type which represents geographic locations
        if result_type == 'geos' and result_obj.get('location_id'):
            return result_obj
    
    # Second pass: Look for locations without venue keywords in the name
    for loc in locations:
        result_obj = loc.get('result_object', {})
        name = result_obj.get('name', '').lower()
        
        # Check if name contains venue keywords
        is_venue = any(keyword in name for keyword in venue_keywords)
        
        # If it's not a venue and has a location_id, use it
        if not is_venue and result_obj.get('location_id'):
            return result_obj
    
    # Third pass: If all results contain venue keywords, 
    # look for the shortest name (usually the city name)
    shortest_name_obj = None
    shortest_length = float('inf')
    
    for loc in locations:
        result_obj = loc.get('result_object', {})
        name = result_obj.get('name', '')
        
        if result_obj.get('location_id') and len(name) < shortest_length:
            shortest_length = len(name)
            shortest_name_obj = result_obj
    
    if shortest_name_obj:
        return shortest_name_obj
    
    # Last resort: return first result with location_id
    for loc in locations:
        result_obj = loc.get('result_object', {})
        if result_obj.get('location_id'):
            return result_obj
    
    return None

@tool
def get_restaurants(location_name: str, limit: int = 10) -> str:
    """Get restaurants for a specific location.
    
    Args:
        location_name: Name of the location (e.g., 'Coimbatore', 'Chennai', 'Paris')
        limit: Maximum number of restaurants to return (default: 10)
    
    Returns:
        List of restaurants with names, ratings, and details
    """
    try:
        # First, search for the location to get its ID
        search_url = "https://travel-advisor.p.rapidapi.com/locations/search"
        search_params = {
            "query": location_name,
            "limit": 10,
            "offset": "0",
            "units": "km",
            "location_id": "1",
            "currency": "INR",
            "sort": "relevance",
            "lang": "en_US"
        }
        
        search_response = requests.get(search_url, headers=HEADERS, params=search_params, timeout=10)
        
        if search_response.status_code != 200:
            return f"Could not find location: {location_name}"
        
        search_data = search_response.json()
        locations = search_data.get('data', [])
        
        if not locations:
            return f"No location found for '{location_name}'"
        
        # Find the best matching location (prefer cities over specific venues)
        best_match = find_best_location_match(locations, location_name)
        
        if not best_match:
            return f"Could not find a suitable location for '{location_name}'"
        
        location_id = best_match.get('location_id')
        location_full_name = best_match.get('name', location_name)
        location_string = best_match.get('location_string', '')
        
        if not location_id:
            return f"Could not get location ID for '{location_name}'"
        
        # Get restaurants for this location
        rest_url = "https://travel-advisor.p.rapidapi.com/restaurants/list"
        rest_params = {
            "location_id": location_id,
            "restaurant_tagcategory": "10591",
            "restaurant_tagcategory_standalone": "10591",
            "currency": "INR",
            "lunit": "km",
            "limit": str(limit),
            "lang": "en_US"
        }
        
        rest_response = requests.get(rest_url, headers=HEADERS, params=rest_params, timeout=10)
        
        if rest_response.status_code == 200:
            rest_data = rest_response.json()
            restaurants = rest_data.get('data', [])
            
            if restaurants:
                result = f"**Top {len(restaurants)} restaurants in {location_full_name}"
                if location_string:
                    result += f" ({location_string})"
                result += "**\n\n"
                
                for i, r in enumerate(restaurants, 1):
                    name = r.get('name', 'Unknown')
                    rating = r.get('rating', 'N/A')
                    num_reviews = r.get('num_reviews', '')
                    cuisine = r.get('cuisine', [])
                    price_level = r.get('price_level', '')
                    ranking = r.get('ranking_string', '')
                    address = r.get('address', 'N/A')
                    
                    result += f"{i}. **{name}**\n"
                    result += f"   Rating: {rating}/5"
                    if num_reviews:
                        result += f" ({num_reviews} reviews)"
                    result += "\n"
                    
                    if cuisine:
                        cuisine_str = ', '.join([c.get('name', '') for c in cuisine[:3]])
                        result += f"   Cuisine: {cuisine_str}\n"
                    
                    # Convert price_level to descriptive text
                    # NOTE: We skip displaying actual price amounts as they can be inflated
                    if price_level:
                        price_description = convert_price_level(price_level)
                        result += f"   Price Range: {price_description}\n"
                    
                    if ranking:
                        result += f"   {ranking}\n"
                    
                    if address != 'N/A':
                        result += f"   Address: {address}\n"
                    
                    result += "\n"
                
                return result
            else:
                return f"No restaurants found for {location_full_name}. The API might have limited data for this location."
        else:
            return f"Error fetching restaurants. Status: {rest_response.status_code}"
    
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_attractions(location_name: str, limit: int = 10) -> str:
    """Get tourist attractions and things to do in a specific location.
    
    Args:
        location_name: Name of the location (e.g., 'Coimbatore', 'Paris', 'Tokyo')
        limit: Maximum number of attractions to return (default: 10)
    
    Returns:
        List of attractions with names, ratings, and details
    """
    try:
        # First, search for the location to get its ID
        search_url = "https://travel-advisor.p.rapidapi.com/locations/search"
        search_params = {
            "query": location_name,
            "limit": 10,
            "offset": "0",
            "units": "km",
            "location_id": "1",
            "currency": "INR",
            "sort": "relevance",
            "lang": "en_US"
        }
        
        search_response = requests.get(search_url, headers=HEADERS, params=search_params, timeout=10)
        
        if search_response.status_code != 200:
            return f"Could not find location: {location_name}"
        
        search_data = search_response.json()
        locations = search_data.get('data', [])
        
        if not locations:
            return f"No location found for '{location_name}'"
        
        # Find the best matching location (prefer cities over specific venues)
        best_match = find_best_location_match(locations, location_name)
        
        if not best_match:
            return f"Could not find a suitable location for '{location_name}'"
        
        location_id = best_match.get('location_id')
        location_full_name = best_match.get('name', location_name)
        location_string = best_match.get('location_string', '')
        
        if not location_id:
            return f"Could not get location ID for '{location_name}'"
        
        # Get attractions for this location
        attr_url = "https://travel-advisor.p.rapidapi.com/attractions/list"
        attr_params = {
            "location_id": location_id,
            "currency": "INR",
            "lunit": "km",
            "limit": str(limit),
            "lang": "en_US"
        }
        
        attr_response = requests.get(attr_url, headers=HEADERS, params=attr_params, timeout=10)
        
        if attr_response.status_code == 200:
            attr_data = attr_response.json()
            attractions = attr_data.get('data', [])
            
            if attractions:
                result = f"**Top {len(attractions)} attractions in {location_full_name}"
                if location_string:
                    result += f" ({location_string})"
                result += "**\n\n"
                
                for i, a in enumerate(attractions, 1):
                    name = a.get('name', 'Unknown')
                    rating = a.get('rating', 'N/A')
                    num_reviews = a.get('num_reviews', '')
                    ranking = a.get('ranking_string', '')
                    description = a.get('description', '')
                    address = a.get('address', 'N/A')
                    
                    result += f"{i}. **{name}**\n"
                    result += f"   Rating: {rating}/5"
                    if num_reviews:
                        result += f" ({num_reviews} reviews)"
                    result += "\n"
                    
                    if ranking:
                        result += f"   {ranking}\n"
                    
                    if description:
                        desc_short = description[:150] + "..." if len(description) > 150 else description
                        result += f"   Description: {desc_short}\n"
                    
                    if address != 'N/A':
                        result += f"   Address: {address}\n"
                    
                    result += "\n"
                
                return result
            else:
                return f"No attractions found for {location_full_name}. The API might have limited data for this location."
        else:
            return f"Error fetching attractions. Status: {attr_response.status_code}"
    
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================================
# ROUTE PLANNING TOOL
# ============================================================================

@tool
def plan_route(origin: str, destination: str, waypoints: Optional[List[str]] = None) -> str:
    """
    Plan routes for all travel modes (drive, walk, bicycle, transit).
    
    Args:
        origin: Starting location
        destination: Ending location
        waypoints: Optional intermediate stops
    
    Returns:
        Comprehensive route analysis with all modes
    """
    try:
        from route_planner import plan_route as route_tool
        
        input_data = {
            "origin": origin,
            "destination": destination
        }
        if waypoints:
            input_data["waypoints"] = waypoints
        
        result = route_tool.invoke(input_data)
        return result
        
    except Exception as e:
        return f"Route planning error: {str(e)}"
    
    
    