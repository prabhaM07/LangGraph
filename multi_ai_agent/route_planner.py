import os
import requests
from langchain_core.tools import tool
from typing import List, Dict, Optional
import time
from math import radians, sin, cos, sqrt, atan2

# Continent coordinates for smart handling
CONTINENT_COORDS = {
    'africa': ('Africa', -1.2921, 36.8219, 'Nairobi, Kenya'),
    'europe': ('Europe', 48.8566, 2.3522, 'Paris, France'),
    'asia': ('Asia', 35.6762, 139.6503, 'Tokyo, Japan'),
    'north america': ('North America', 40.7128, -74.0060, 'New York, USA'),
    'south america': ('South America', -23.5505, -46.6333, 'São Paulo, Brazil'),
    'australia': ('Australia', -33.8688, 151.2093, 'Sydney, Australia'),
    'oceania': ('Oceania', -33.8688, 151.2093, 'Sydney, Australia'),
    'antarctica': ('Antarctica', -77.8467, 166.6686, 'McMurdo Station')
}

@tool
def plan_route(origin: str, destination: str, waypoints: List[str] = None) -> str:
    """
    Plan driving route with detailed turn-by-turn directions and travel analysis.
    
    Args:
        origin: Starting location (city, address, landmark, or continent)
        destination: Ending location (city, address, landmark, or continent)
        waypoints: Optional list of intermediate stops
    
    Returns:
        Comprehensive driving route analysis with:
        - Detailed turn-by-turn directions
        - Distance, duration, and efficiency metrics
        - Travel insights and recommendations
    """
    try:
        api_key = os.getenv("GEOAPIFY_API_KEY", "7a0403f3c0d54a3996071dfbd1d72f1a")
        if not api_key:
            return "ERROR: Geoapify API key not configured. Set GEOAPIFY_API_KEY environment variable."
        
        # Geocode locations
        origin_coords = _geocode_location(origin, api_key)
        dest_coords = _geocode_location(destination, api_key)
        
        if not origin_coords or not dest_coords:
            return "ERROR: Could not find one or both locations. Please provide more specific location names."
        
        # Process waypoints if provided
        waypoint_coords = []
        waypoint_names = []
        if waypoints:
            for wp in waypoints:
                coords = _geocode_location(wp, api_key)
                if coords:
                    waypoint_coords.append(coords)
                    waypoint_names.append(coords['display_name'])
        
        # Calculate straight-line distance
        straight_distance = _calculate_haversine_distance(origin_coords, dest_coords)
        
        # Get driving route only
        print(f"Planning driving route from {origin} to {destination}...")
        route_data = _get_route(origin_coords, dest_coords, waypoint_coords, "drive", api_key)
        
        if not route_data:
            return f"ERROR: Could not calculate driving route from {origin} to {destination}. The locations may be too far apart or on different continents."
        
        props = route_data.get('properties', {})
        distance_km = props.get('distance', 0) / 1000
        duration_s = props.get('time', 0)
        
        # Extract turn-by-turn directions
        legs = props.get('legs', [])
        steps_data = []
        if legs and len(legs) > 0:
            for leg in legs:
                steps = leg.get('steps', [])
                for step in steps:
                    instruction = step.get('instruction', {}).get('text', '')
                    if instruction:
                        steps_data.append({
                            'instruction': instruction,
                            'distance': step.get('distance', 0) / 1000,
                            'duration': step.get('time', 0)
                        })
        
        result = {
            'distance_km': distance_km,
            'distance_mi': distance_km * 0.621371,
            'duration_s': duration_s,
            'steps': steps_data
        }
        
        # Format output
        return _format_driving_output(
            result,
            origin_coords['display_name'],
            dest_coords['display_name'],
            waypoint_names,
            straight_distance
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"ERROR: {str(e)}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _geocode_location(location: str, api_key: str) -> Optional[Dict]:
    """Convert location name to coordinates with smart continent handling."""
    try:
        location_lower = location.lower().strip()
        
        # Check for continents
        for key, (name, lat, lon, city) in CONTINENT_COORDS.items():
            if location_lower == key or key in location_lower:
                print(f"Note: '{location}' is a continent. Using {city} as reference.")
                return {"lon": lon, "lat": lat, "display_name": f"{name} ({city})"}
        
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            "text": location,
            "apiKey": api_key,
            "limit": 5,
            "lang": "en"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            if features:
                best_feature = None
                for feature in features:
                    props = feature.get('properties', {})
                    result_type = props.get('result_type', '')
                    formatted = props.get('formatted', '')
                    
                    # Skip inappropriate results
                    if location_lower in ['africa', 'asia', 'europe'] and 'United States' in formatted:
                        continue
                    
                    if result_type in ['country', 'city', 'state']:
                        best_feature = feature
                        break
                    
                    if not best_feature:
                        best_feature = feature
                
                if best_feature:
                    coords = best_feature['geometry']['coordinates']
                    props = best_feature.get('properties', {})
                    return {
                        "lon": coords[0],
                        "lat": coords[1],
                        "display_name": props.get('formatted', location)
                    }
        return None
    except Exception as e:
        print(f"Geocoding error: {str(e)}")
        return None


def _get_route(origin: Dict, destination: Dict, waypoints: List[Dict], 
               mode: str, api_key: str) -> Optional[Dict]:
    """Get route from Geoapify API."""
    try:
        all_points = [origin] + waypoints + [destination]
        waypoints_str = "|".join([f"{p['lat']},{p['lon']}" for p in all_points])
        
        url = "https://api.geoapify.com/v1/routing"
        params = {
            "waypoints": waypoints_str,
            "mode": "drive",
            "apiKey": api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('features'):
                return data['features'][0]
        return None
    except:
        return None


def _calculate_haversine_distance(coords1: Dict, coords2: Dict) -> Dict:
    """Calculate great-circle distance between two coordinates."""
    lat1, lon1 = radians(coords1['lat']), radians(coords1['lon'])
    lat2, lon2 = radians(coords2['lat']), radians(coords2['lon'])
    
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance_km = 6371 * c
    return {'km': distance_km, 'miles': distance_km * 0.621371}


def _format_driving_output(result: Dict, origin: str, destination: str,
                           waypoints: List[str], straight_distance: Dict) -> str:
    """Format driving route output with detailed directions."""
    
    output = f"""
================================================================================
                        DRIVING ROUTE PLANNER
================================================================================

ORIGIN: {origin}
DESTINATION: {destination}
"""
    
    if waypoints:
        output += f"VIA: {' > '.join(waypoints)}\n"
    
    output += f"\nAIR DISTANCE: {straight_distance['km']:.2f} km ({straight_distance['miles']:.2f} miles)\n"
    
    # Route Summary
    h = int(result['duration_s'] // 3600)
    m = int((result['duration_s'] % 3600) // 60)
    
    output += f"\n{'='*80}\nROUTE SUMMARY\n{'='*80}\n\n"
    output += f"Total Distance: {result['distance_km']:.2f} km ({result['distance_mi']:.2f} mi)\n"
    output += f"Estimated Duration: {h}h {m}min\n" if h > 0 else f"Estimated Duration: {m} min\n"
    
    if result['duration_s'] > 0:
        avg_speed = result['distance_km'] / (result['duration_s'] / 3600)
        output += f"Average Speed: {avg_speed:.1f} km/h ({avg_speed*0.621371:.1f} mph)\n"
    
    efficiency = (straight_distance['km'] / result['distance_km']) * 100 if result['distance_km'] > 0 else 0
    output += f"Route Efficiency: {efficiency:.1f}%\n"
    
    # Turn-by-turn directions
    if result['steps']:
        output += f"\n{'='*80}\nTURN-BY-TURN DIRECTIONS\n{'='*80}\n"
        for i, step in enumerate(result['steps'], 1):
            step_m = int(step['duration'] // 60)
            output += f"\n{i}. {step['instruction']}\n"
            if step['distance'] > 0.01:
                output += f"   Distance: {step['distance']:.2f} km"
                if step_m > 0:
                    output += f" | Time: ~{step_m} min"
                output += "\n"
        
        output += f"\nARRIVE AT DESTINATION\n"
    
    # Travel Insights
    output += f"\n{'='*80}\nTRAVEL INSIGHTS\n{'='*80}\n\n"
    
    fuel_cost = result['distance_km'] * 0.15
    output += f"Estimated Fuel Cost: ${fuel_cost:.2f} (at $0.15/km)\n"
    output += f"CO2 Emissions: ~{result['distance_km']*0.12:.1f} kg\n"
    
    # Calculate suggested breaks for long trips
    if h > 2:
        breaks = h // 2
        output += f"\nRECOMMENDED BREAKS: {breaks} break(s) (every ~2 hours)\n"
    
    # Recommendations
    output += f"\n{'='*80}\nRECOMMENDATIONS\n{'='*80}\n\n"
    
    dist = straight_distance['km']
    if dist < 100:
        output += "TRAVEL TIP: Consider checking traffic conditions before departure.\n"
    elif dist < 300:
        output += "TRAVEL TIP: Plan for rest stops every 2-3 hours. Check vehicle condition before departure.\n"
    else:
        output += "TRAVEL TIP: Long distance journey - ensure proper rest, check weather conditions, and plan overnight stops if needed.\n"
    
    output += f"\n{'='*80}\n"
    
    return output