import os
api_key=os.getenv("WEATHER_API_KEY")
print(api_key)
lat, long=(42.360001, -71.092003)

import requests
from datetime import datetime, timedelta


def fetch_weather_data(lat, lon, start_date, end_date, timestep=1):
    """
    Fetches hourly weather data from OpenWeatherMap for a given latitude and longitude
    between the specified start and end dates.
    
    Parameters:
        lat (float): Latitude.
        lon (float): Longitude.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        timestep (int): Time step in hours (default is 1).
        
    Returns:
        list: A list of hourly weather data.
    """
    # Convert start and end dates to datetime objects
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Collect hourly weather data within date range
    all_data = []
    current = start

    # The One Call API has a limit of 5-day forecast/history per request
    while current < end:
        # Unix timestamp for the current date
        current_unix = int(current.timestamp())
        
        # OpenWeatherMap One Call API endpoint
        url = f"http://api.openweathermap.org/data/2.5/onecall/timemachine"
        params = {
            "lat": lat,
            "lon": lon,
            "dt": current_unix,
            "appid": api_key,
            "units": "metric"  # Use 'imperial' for Fahrenheit
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            # Append hourly data
            all_data.extend(data.get("hourly", []))
        else:
            print(f"Failed to fetch data for {current.strftime('%Y-%m-%d')}: {response.status_code}")
        
        # Move to the next day
        current += timedelta(days=1)

    # Filter data by time step
    filtered_data = [all_data[i] for i in range(0, len(all_data), timestep)]
    
    return filtered_data

# Example usage
latitude = 40.7128
longitude = -74.0060
start = "2023-01-01"
end = "2023-01-05"
# data = fetch_weather_data(latitude, longitude, start, end)
# print(data)


import requests

# Replace with your actual OpenWeatherMap API key

def test_openweathermap_connection(lat=40.7128, lon=-74.0060):
    """
    Tests the connection to OpenWeatherMap using the provided API key by fetching
    the current weather data for a given location (default is New York City).
    
    Parameters:
        lat (float): Latitude (default is New York City).
        lon (float): Longitude (default is New York City).
        
    Returns:
        None
    """
    # OpenWeatherMap Current Weather API endpoint
    url = "http://api.openweathermap.org/data/2.5/weather"
    
    # Request parameters
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"  # Use 'imperial' for Fahrenheit
    }
    
    # Send a GET request
    response = requests.get(url, params=params)
    
    # Check the response status
    if response.status_code == 200:
        print("API Key is valid. Connection successful!")
        # Print a portion of the response data for verification
        data = response.json()
        print("Current weather data:", data["weather"][0]["description"])
        print("Temperature:", data["main"]["temp"], "°C")
    elif response.status_code == 401:
        print("Invalid API Key. Please check your API key and try again.")
    else:
        print(f"Failed to connect. Status code: {response.status_code}")
        print("Response:", response.json())

# Test the connection
test_openweathermap_connection()
