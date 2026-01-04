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

import os
import requests
from langchain_core.tools import tool
from typing import Optional
import time

# ============================================================================
# API CONFIGURATION
# ============================================================================

API_KEY = os.getenv("RAPIDAPI_KEY", "13f4222a24msh542b69ec8c57350p1ba58bjsn5b46b8e6d7e9")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "travel-advisor.p.rapidapi.com"
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def make_api_request_with_retry(url: str, headers: dict, params: dict, max_retries: int = 2, timeout: int = 20):
    """
    Make API request with retry logic and better timeout handling
    
    Args:
        url: API endpoint URL
        headers: Request headers
        params: Query parameters
        max_retries: Maximum number of retry attempts
        timeout: Timeout in seconds
    
    Returns:
        tuple: (success: bool, data: dict or error message)
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=timeout
            )
            
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 429:
                # Rate limit hit
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                    time.sleep(wait_time)
                    continue
                else:
                    return False, "API rate limit exceeded. Please try again later."
            else:
                return False, f"API returned status code {response.status_code}"
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            else:
                return False, f"Request timed out after {timeout} seconds. The API is not responding. This may be a temporary issue - please try again."
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                return False, f"Network error: {str(e)}"
    
    return False, f"Failed after {max_retries} attempts"


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


# ============================================================================
# TOOLS
# ============================================================================

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
        
        # Use retry mechanism for location search
        success, result = make_api_request_with_retry(search_url, HEADERS, search_params, max_retries=2, timeout=20)
        
        if not success:
            return f"Could not search for location '{location_name}': {result}"
        
        search_data = result
        locations = search_data.get('data', [])
        
        if not locations:
            return f"No location found for '{location_name}'. Please try a different location name or check the spelling."
        
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
        
        # Use retry mechanism for restaurant search
        success, result = make_api_request_with_retry(rest_url, HEADERS, rest_params, max_retries=2, timeout=20)
        
        if not success:
            return f"Could not fetch restaurants for '{location_full_name}': {result}"
        
        rest_data = result
        restaurants = rest_data.get('data', [])
        
        if restaurants:
            result_text = f"**Top {len(restaurants)} restaurants in {location_full_name}"
            if location_string:
                result_text += f" ({location_string})"
            result_text += "**\n\n"
            
            for i, r in enumerate(restaurants, 1):
                name = r.get('name', 'Unknown')
                rating = r.get('rating', 'N/A')
                num_reviews = r.get('num_reviews', '')
                cuisine = r.get('cuisine', [])
                price_level = r.get('price_level', '')
                ranking = r.get('ranking_string', '')
                address = r.get('address', 'N/A')
                
                result_text += f"{i}. **{name}**\n"
                result_text += f"   Rating: {rating}/5"
                if num_reviews:
                    result_text += f" ({num_reviews} reviews)"
                result_text += "\n"
                
                if cuisine:
                    cuisine_str = ', '.join([c.get('name', '') for c in cuisine[:3]])
                    result_text += f"   Cuisine: {cuisine_str}\n"
                
                if price_level:
                    price_description = convert_price_level(price_level)
                    result_text += f"   Price Range: {price_description}\n"
                
                if ranking:
                    result_text += f"   {ranking}\n"
                
                if address != 'N/A':
                    result_text += f"   Address: {address}\n"
                
                result_text += "\n"
            
            return result_text
        else:
            return f"No restaurants found for {location_full_name}. The Travel Advisor API might have limited data for this location."
    
    except Exception as e:
        return f"Unexpected error while fetching restaurants: {str(e)}"


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
        
        # Use retry mechanism for location search
        success, result = make_api_request_with_retry(search_url, HEADERS, search_params, max_retries=2, timeout=20)
        
        if not success:
            return f"Could not search for location '{location_name}': {result}"
        
        search_data = result
        locations = search_data.get('data', [])
        
        if not locations:
            return f"No location found for '{location_name}'. Please try a different location name or check the spelling."
        
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
        
        # Use retry mechanism for attractions search
        success, result = make_api_request_with_retry(attr_url, HEADERS, attr_params, max_retries=2, timeout=20)
        
        if not success:
            return f"Could not fetch attractions for '{location_full_name}': {result}"
        
        attr_data = result
        attractions = attr_data.get('data', [])
        
        if attractions:
            result_text = f"**Top {len(attractions)} attractions in {location_full_name}"
            if location_string:
                result_text += f" ({location_string})"
            result_text += "**\n\n"
            
            for i, a in enumerate(attractions, 1):
                name = a.get('name', 'Unknown')
                rating = a.get('rating', 'N/A')
                num_reviews = a.get('num_reviews', '')
                ranking = a.get('ranking_string', '')
                description = a.get('description', '')
                address = a.get('address', 'N/A')
                
                result_text += f"{i}. **{name}**\n"
                result_text += f"   Rating: {rating}/5"
                if num_reviews:
                    result_text += f" ({num_reviews} reviews)"
                result_text += "\n"
                
                if ranking:
                    result_text += f"   {ranking}\n"
                
                if description:
                    desc_short = description[:150] + "..." if len(description) > 150 else description
                    result_text += f"   Description: {desc_short}\n"
                
                if address != 'N/A':
                    result_text += f"   Address: {address}\n"
                
                result_text += "\n"
            
            return result_text
        else:
            return f"No attractions found for {location_full_name}. The Travel Advisor API might have limited data for this location."
    
    except Exception as e:
        return f"Unexpected error while fetching attractions: {str(e)}"



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
    
    
    