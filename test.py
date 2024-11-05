import sqlite3
from datetime import datetime
import requests
import os

# Connect to SQLite database
conn = sqlite3.connect("weather.db")
cursor = conn.cursor()

# Function to insert location into Location table
def insert_location(cursor, latitude, longitude, elevation=None):
    cursor.execute(
        "INSERT INTO Location (latitude, longitude, elevation) VALUES (?, ?, ?)",
        (latitude, longitude, elevation),
    )
    return cursor.lastrowid

# Function to insert weather data
def insert_weather_data(cursor, location_id, date, hour, temperature, humidity, wind_speed, cloud_cover):
    cursor.execute(
        """INSERT INTO WeatherData (location_id, date, hour, temperature, humidity, wind_speed, cloud_cover)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (location_id, date, hour, temperature, humidity, wind_speed, cloud_cover),
    )

# Function to insert solar irradiance data
def insert_solar_irradiance(cursor, location_id, date, hour, GHI, DNI, DHI):
    cursor.execute(
        """INSERT INTO SolarIrradiance (location_id, date, hour, GHI, DNI, DHI)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (location_id, date, hour, GHI, DNI, DHI),
    )

# Function to insert energy production data
def insert_energy_production(cursor, location_id, date, hour, power_output):
    cursor.execute(
        """INSERT INTO EnergyProduction (location_id, date, hour, power_output)
           VALUES (?, ?, ?, ?)""",
        (location_id, date, hour, power_output),
    )

# Fetch and insert historical weather data
def fetch_and_store_weather_data(api_key, latitude, longitude):
    # Sample API call for historical data, replace with actual endpoint
    url = f"http://api.openweathermap.org/data/2.5/onecall/timemachine"
    
    # For simplicity, assume a single date in the past
    timestamp = int(datetime(2023, 1, 1).timestamp())  # Example date

    response = requests.get(url, params={
        "lat": latitude,
        "lon": longitude,
        "dt": timestamp,
        "appid": api_key
    })
    
    if response.status_code == 200:
        data = response.json()
        
        # Insert location (if not already added)
        location_id = insert_location(cursor, latitude, longitude)
        
        # Loop over hourly data and insert into database
        for hourly_data in data.get("hourly", []):
            dt = datetime.fromtimestamp(hourly_data["dt"])
            date = dt.strftime("%Y-%m-%d")
            hour = dt.hour
            temp = hourly_data.get("temp")
            humidity = hourly_data.get("humidity")
            wind_speed = hourly_data.get("wind_speed")
            cloud_cover = hourly_data.get("clouds")
            GHI = hourly_data.get("solar_irradiance", {}).get("GHI")  # Example values, may need actual keys
            DNI = hourly_data.get("solar_irradiance", {}).get("DNI")
            DHI = hourly_data.get("solar_irradiance", {}).get("DHI")
            power_output = hourly_data.get("power_output")  # Placeholder for actual power output data
            
            # Insert data into respective tables
            insert_weather_data(cursor, location_id, date, hour, temp, humidity, wind_speed, cloud_cover)
            insert_solar_irradiance(cursor, location_id, date, hour, GHI, DNI, DHI)
            insert_energy_production(cursor, location_id, date, hour, power_output)
            
        # Commit the transaction
        conn.commit()
    else:
        print("Error fetching data:", response.status_code)

# Example usage
api_key = os.getenv("WEATHER_API_KEY")  # Replace with your OpenWeatherMap API key
latitude = 55.7558  # Replace with desired latitude
longitude = 37.6173  # Replace with desired longitude
fetch_and_store_weather_data(api_key, latitude, longitude)

# Close the database connection
conn.close()