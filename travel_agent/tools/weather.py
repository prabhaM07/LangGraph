import requests
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get weather for a city. Input should be the city name."""
    try:
        api_key = "85b1861ce63d879f3c852ee41f6c591b"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            temp_celsius = data['main']['temp']
            temp_fahrenheit = (temp_celsius * 9/5) + 32
            description = data['weather'][0]['description']
            humidity = data['main']['humidity']
            
            return f"Weather in {city}: {description.capitalize()}, Temperature: {temp_celsius:.1f}°C ({temp_fahrenheit:.1f}°F), Humidity: {humidity}%"
        else:
            return f"Could not fetch weather for {city}. Error: {data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Weather service error: {str(e)}"

