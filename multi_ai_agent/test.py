import requests

# Get free API key from: https://unsplash.com/developers
API_KEY = "x3RkRGyFPnePlluc-l-wRwG53xXIJ08OqNohrTatDjs"

def search_images(location, per_page=10):
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {API_KEY}"}
    params = {
        "query": location,
        "per_page": per_page
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        photos = data.get("results", [])
        
        print(f"Found {len(photos)} images for '{location}':\n")
        
        for i, photo in enumerate(photos, 1):
            print(f"{i}. {photo['alt_description'] or 'No description'}")
            print(f"   URL: {photo['urls']['regular']}")
            print(f"   Photographer: {photo['user']['name']}\n")
        
        return photos
    else:
        print(f"Error: {response.status_code}")
        return []

# Example usage
if __name__ == "__main__":
    location = input("Enter location: ")
    search_images(location)