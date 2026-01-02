import os
import requests
from langchain_core.tools import tool
from typing import Optional

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
    Prioritize actual cities/regions over specific venues."""
    
    # Keywords that indicate a specific venue (not a city/region)
    venue_keywords = ['hotel', 'restaurant', 'temple', 'palace', 'museum', 
                      'resort', 'cafe', 'mall', 'airport', 'station',
                      'taj', 'regency', 'marriott', 'hilton', 'hyatt',
                      'radisson', 'andaz', 'oberoi', 'itc', 'leela']
    
    # First pass: Look for locations without venue keywords in the name
    for loc in locations:
        result_obj = loc.get('result_object', {})
        name = result_obj.get('name', '').lower()
        
        # Check if name contains venue keywords
        is_venue = any(keyword in name for keyword in venue_keywords)
        
        # If it's not a venue, it's likely a city/region
        if not is_venue:
            return result_obj
    
    # Second pass: If all results contain venue keywords, 
    # look for the shortest name (usually the city name)
    shortest_name_obj = None
    shortest_length = float('inf')
    
    for loc in locations:
        result_obj = loc.get('result_object', {})
        name = result_obj.get('name', '')
        
        if len(name) < shortest_length:
            shortest_length = len(name)
            shortest_name_obj = result_obj
    
    if shortest_name_obj:
        return shortest_name_obj
    
    # Last resort: return first result
    if locations:
        return locations[0].get('result_object', {})
    
    return None

@tool
def search_location(location_name: str) -> str:
    """Search for a location and get its details.
    
    Args:
        location_name: Name of the location to search (e.g., 'Coimbatore', 'Paris', 'New York')
    
    Returns:
        Location information including name, ID, and location string
    """
    try:
        url = "https://travel-advisor.p.rapidapi.com/locations/search"
        params = {
            "query": location_name,
            "limit": 10,
            "offset": "0",
            "units": "km",
            "location_id": "1",
            "currency": "INR",
            "sort": "relevance",
            "lang": "en_US"
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            locations = data.get('data', [])
            
            if locations:
                result = f"Found {len(locations)} location(s) for '{location_name}':\n\n"
                
                # Show all locations
                for idx, loc in enumerate(locations[:10], 1):
                    result_obj = loc.get('result_object', {})
                    name = result_obj.get('name', 'Unknown')
                    location_id = result_obj.get('location_id', 'N/A')
                    location_string = result_obj.get('location_string', 'N/A')
                    
                    result += f"{idx}. {name}\n"
                    result += f"   Location ID: {location_id}\n"
                    result += f"   Full Location: {location_string}\n\n"
                
                return result
            else:
                return f"No locations found for '{location_name}'"
        else:
            return f"Error searching location. Status: {response.status_code}"
    
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_restaurants(location_name: str, limit: int = 10) -> str:
    """Get restaurants for a specific location with prices in Indian Rupees.
    
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
                result = f"Top {len(restaurants)} restaurants in {location_full_name}"
                if location_string:
                    result += f" ({location_string})"
                result += ":\n\n"
                
                for i, r in enumerate(restaurants, 1):
                    name = r.get('name', 'Unknown')
                    rating = r.get('rating', 'N/A')
                    cuisine = r.get('cuisine', [])
                    price_level = r.get('price_level', '')
                    price = r.get('price', 'N/A')
                    ranking = r.get('ranking_string', '')
                    address = r.get('address', 'N/A')
                    
                    result += f"{i}. {name}\n"
                    result += f"   Rating: {rating}/5\n"
                    
                    if cuisine:
                        cuisine_str = ', '.join([c.get('name', '') for c in cuisine[:3]])
                        result += f"   Cuisine: {cuisine_str}\n"
                    
                    # Convert price_level to descriptive text
                    if price_level:
                        price_description = convert_price_level(price_level)
                        result += f"   Price Range: {price_description}\n"
                    
                    # Show price if available
                    if price != 'N/A' and price:
                        result += f"   Average Cost: {price}\n"
                    
                    if ranking:
                        result += f"   Ranking: {ranking}\n"
                    
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
    """Get tourist attractions and things to do in a specific location with prices in Indian Rupees.
    
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
                result = f"Top {len(attractions)} attractions in {location_full_name}"
                if location_string:
                    result += f" ({location_string})"
                result += ":\n\n"
                
                for i, a in enumerate(attractions, 1):
                    name = a.get('name', 'Unknown')
                    rating = a.get('rating', 'N/A')
                    ranking = a.get('ranking_string', '')
                    description = a.get('description', '')
                    address = a.get('address', 'N/A')
                    
                    result += f"{i}. {name}\n"
                    result += f"   Rating: {rating}/5\n"
                    
                    if ranking:
                        result += f"   Ranking: {ranking}\n"
                    
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