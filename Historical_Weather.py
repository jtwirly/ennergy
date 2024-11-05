import os
import sqlite3
import requests
from datetime import datetime, timedelta

# Retrieve API key from environment variables
api_key = os.getenv("TOMORROW_API_KEY")
lat, lon = (34.0522, -118.2437)  # Latitude and longitude for Los Angeles

# Connect to SQLite database
conn = sqlite3.connect("historical_weather.db")
cursor = conn.cursor()

# Create WeatherData table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS WeatherData (
    weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    temperature REAL,
    humidity REAL,
    wind_speed REAL,
    cloud_cover REAL
);
""")
conn.commit()

# Function to fetch and store historical weather data from Tomorrow.io
def get_historical_weather(lat, lon, start, end, api_key):
    # Tomorrow.io historical weather data API endpoint
    url = f"https://api.tomorrow.io/v4/timelines?location={lat},{lon}&fields=temperature,humidity,windSpeed,cloudCover&startTime={start}&endTime={end}&units=metric&timezone=America/Los_Angeles&apikey={api_key}"

    # Send GET request
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse JSON data
        historical_data = response.json()
        
        # Iterate over each hourly data entry
        for entry in historical_data['data']['timelines'][0]['intervals']:
            # Extract date and time from the entry
            timestamp = entry['startTime']
            weather_date = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d')
            weather_hour = datetime.fromisoformat(timestamp).hour
            
            # Extract weather data
            temp = entry['values']['temperature']
            humidity = entry['values']['humidity']
            wind_speed = entry['values']['windSpeed']
            cloud_cover = entry['values']['cloudCover']
            
            # Insert data into WeatherData table
            cursor.execute("""
            INSERT INTO WeatherData (date, hour, temperature, humidity, wind_speed, cloud_cover)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (weather_date, weather_hour, temp, humidity, wind_speed, cloud_cover))
        
        # Commit the transaction to save all entries
        conn.commit()
        print("Historical weather data stored successfully.")
    else:
        # Print error message if something goes wrong
        print("Error fetching data. Please check the coordinates and API key.")

# Define the time range for historical data (in ISO 8601 format)
# Example: Getting data from 1 day ago to now
end_time = datetime.now().isoformat()
start_time = (datetime.now() - timedelta(days=1)).isoformat()

# Fetch and store historical weather data
get_historical_weather(lat, lon, start_time, end_time, api_key)

# Close the database connection
conn.close()
