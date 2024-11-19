import datetime
import pandas as pd
from meteostat import Point, Hourly

# Define the location (latitude and longitude for Boston, Massachusetts)
latitude = 42.3601
longitude = -71.0589
location_name = "Boston"

# File path for the existing data
file_path = 'deliverable_2/historical_weather_data.csv'

# Load the existing data if the file exists
try:
    existing_data = pd.read_csv(file_path, parse_dates=['time'], index_col='time')
    print("Existing data loaded successfully.")
except FileNotFoundError:
    existing_data = pd.DataFrame()
    print("No existing data found. Starting fresh.")

# Define the start and end times for the new data to fetch
start_time = datetime.datetime(2023, 10, 27)
end_time = datetime.datetime(2024, 10, 17)

# Fetch hourly data for the missing range
point = Point(latitude, longitude)
new_data = Hourly(point, start_time, end_time)
new_data = new_data.fetch()

# Add location name to the new data
new_data['location'] = location_name

# Rename columns to match the database schema
new_data = new_data.rename(columns={
    'temp': 'temperature',
    'rhum': 'humidity',
    'prcp': 'precipitation',
    'wspd': 'windspeed',
    'coco': 'cloudcover'
})

# Combine existing and new data
if not existing_data.empty:
    combined_data = pd.concat([existing_data, new_data])
else:
    combined_data = new_data

# Drop duplicate rows based on the index (time)
combined_data = combined_data[~combined_data.index.duplicated(keep='first')]

# Save the updated data back to the CSV file
combined_data.to_csv(file_path, index_label='time')

print(f"Historical weather data updated successfully. Data saved to '{file_path}'.")
