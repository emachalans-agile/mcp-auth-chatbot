from mcp.server.fastmcp import FastMCP         # v1: from mcp.server.fastmcp import FastMCP
import requests
from db import find_user_by_email

mcp = FastMCP("Auth MCP Server")        # v1: FastMCP("Auth MCP Server")

# ---------- TOOL: authenticate user ----------
@mcp.tool()
def authenticate_user(email: str) -> dict:
    """
    Authenticate a user by email.
    Returns user info if valid, else an error message.
    """
    user = find_user_by_email(email)
    if not user:
        return {
            "authenticated": False,
            "message": f"No account found for {email}. Please register first."
        }
    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        },
        "message": f"Welcome back, {user['name']}!"
    }

# ---------- RESOURCE: list of registered emails ----------
@mcp.resource("users://list")
def list_users() -> str:
    from db import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM users")
            return ", ".join([r["email"] for r in cur.fetchall()])

@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a given city."""
    
    # Step 1: Convert city name to latitude & longitude (Geocoding API)
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
    
    try:
        geo_res = requests.get(geo_url, params=geo_params, timeout=10)
        geo_res.raise_for_status()
        geo_data = geo_res.json()
        
        if not geo_data.get("results"):
            return f"Sorry, I couldn't find the city '{city}'."
            
        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        country = location.get("country", "")
        
        # Step 2: Fetch current weather using coordinates
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        weather_res = requests.get(weather_url, params=weather_params, timeout=10)
        weather_res.raise_for_status()
        weather_data = weather_res.json()
        
        current = weather_data["current"]
        temp = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind = current["wind_speed_10m"]
        
        # Step 3: Map weather code to a readable condition
        # Full list: https://open-meteo.com/en/docs (WMO Weather interpretation codes)
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        condition = weather_codes.get(current["weather_code"], "Unknown")
        
        return (
            f"Current weather in {city}, {country}: {condition}. "
            f"Temperature: {temp}°C. "
            f"Humidity: {humidity}%. "
            f"Wind speed: {wind} km/h."
        )
        
    except requests.exceptions.Timeout:
        return "The weather service timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"Unexpected response format from weather API: {str(e)}"

if __name__ == "__main__":
    mcp.run()   # stdio transport by default; or mcp.run(transport="stdio")