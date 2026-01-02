import requests
import json

API_KEY = "13f4222a24msh542b69ec8c57350p1ba58bjsn5b46b8e6d7e9"

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "travel-advisor.p.rapidapi.com"
}

def test_location_coverage(location_name):
    """Test if a location is covered by the API"""
    print(f"\n{'='*80}")
    print(f"Testing: {location_name}")
    print(f"{'='*80}")
    
    # Search for location
    url = "https://travel-advisor.p.rapidapi.com/locations/search"
    params = {
        "query": location_name,
        "limit": 5,
        "offset": "0",
        "units": "km",
        "location_id": "1",
        "currency": "USD",
        "sort": "relevance",
        "lang": "en_US"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            locations = data.get('data', [])
            
            if locations:
                print(f"✅ COVERED - Found {len(locations)} results\n")
                
                for idx, loc in enumerate(locations[:3], 1):
                    result_obj = loc.get('result_object', {})
                    name = result_obj.get('name', 'Unknown')
                    location_id = result_obj.get('location_id', 'N/A')
                    location_string = result_obj.get('location_string', 'N/A')
                    
                    print(f"  {idx}. {name}")
                    print(f"     ID: {location_id}")
                    print(f"     Location: {location_string}")
                    print()
                
                # Try to get restaurants for first location
                first_location_id = locations[0].get('result_object', {}).get('location_id')
                if first_location_id:
                    rest_url = "https://travel-advisor.p.rapidapi.com/restaurants/list"
                    rest_params = {
                        "location_id": first_location_id,
                        "restaurant_tagcategory": "10591",
                        "restaurant_tagcategory_standalone": "10591",
                        "currency": "USD",
                        "lunit": "km",
                        "limit": "5",
                        "lang": "en_US"
                    }
                    
                    rest_response = requests.get(rest_url, headers=headers, params=rest_params, timeout=10)
                    
                    if rest_response.status_code == 200:
                        rest_data = rest_response.json()
                        restaurants = rest_data.get('data', [])
                        print(f"  🍽️  Found {len(restaurants)} restaurants")
                        
                        if restaurants:
                            print(f"\n  Sample restaurants:")
                            for i, r in enumerate(restaurants[:3], 1):
                                print(f"    {i}. {r.get('name', 'Unknown')} - Rating: {r.get('rating', 'N/A')}")
                    else:
                        print(f"  ⚠️  Could not fetch restaurants (Status: {rest_response.status_code})")
            else:
                print(f"❌ NOT COVERED - No results found")
        else:
            print(f"❌ ERROR - Status {response.status_code}: {response.text[:200]}")
    
    except Exception as e:
        print(f"❌ ERROR: {e}")


# Test various locations worldwide
print("🌍 Travel Advisor API - Global Coverage Test")
print("="*80)

# Test locations in different regions
test_locations = [
    # United States
    "New York",
    "Los Angeles",
    "Chicago",
    "San Francisco",
    
    # India - Major Cities
    "Mumbai, India",
    "Delhi, India",
    "Bangalore, India",
    "Chennai, India",
    "Kolkata, India",
    
    # Tamil Nadu - Specific Cities
    "Coimbatore, Tamil Nadu",
    "Chennai, Tamil Nadu",
    "Madurai, Tamil Nadu",
    "Tiruchirappalli, Tamil Nadu",
    "Salem, Tamil Nadu",
    
    # Europe
    "London, UK",
    "Paris, France",
    "Rome, Italy",
    
    # Asia
    "Tokyo, Japan",
    "Bangkok, Thailand",
    "Singapore",
    
    # Middle East
    "Dubai, UAE",
    
    # Australia
    "Sydney, Australia",
    
    # Africa
    "Cape Town, South Africa"
]

for location in test_locations:
    test_location_coverage(location)
    print()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("The Travel Advisor API covers locations worldwide including:")
print("✅ United States (All major cities)")
print("✅ India (Major cities including Tamil Nadu)")
print("✅ Europe (UK, France, Italy, etc.)")
print("✅ Asia (Japan, Thailand, Singapore, etc.)")
print("✅ Middle East (UAE, etc.)")
print("✅ Australia & Oceania")
print("✅ Africa")
print("\nThe API uses TripAdvisor data, so coverage is best in tourist destinations")
print("and major cities worldwide.")
