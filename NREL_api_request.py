import os
import sqlite3
import requests
from datetime import datetime

# Retrieve API key from environment variables
NREL_API_KEY = os.getenv("NREL_API_KEY")  # Ensure this is set in your environment
print(NREL_API_KEY)

# Connect to SQLite database
conn = sqlite3.connect("energyproduction.pv")
cursor = conn.cursor()

# Create a table for storing historical energy production data
cursor.execute("""
CREATE TABLE IF NOT EXISTS EnergyProduction (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    state TEXT,
    technology TEXT,
    production REAL
);
""")
conn.commit()

# Function to fetch and store historical energy production data from NREL
def get_energy_production(state_code, api_key):
    # Endpoint for NREL's historical data (e.g., PV generation data)
    url = f"https://developer.nrel.gov/api/solar/solar_resource/v1.json?api_key={api_key}&lat=36.7783&lon=-119.4179"

    # Send GET request
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse JSON data
        data = response.json()

        # Assuming the response contains daily production data
        if 'outputs' in data and 'solrad_monthly' in data['outputs']:
            print("Storing energy production data for California:\n")
            
            # Store monthly data (example - adjust as needed for actual API structure)
            for month, production in data['outputs']['solrad_monthly'].items():
                production_date = datetime.strptime(month, "%B").strftime('%Y-%m-01')  # Convert month name to date format
                technology = "Solar PV"  # Assuming data is for solar; adapt as needed
                
                # Insert data into EnergyProduction table
                cursor.execute("""
                INSERT INTO EnergyProduction (date, state, technology, production)
                VALUES (?, ?, ?, ?)
                """, (production_date, state_code, technology, production))
                
                print(f"Date: {production_date}")
                print(f"State: {state_code}")
                print(f"Technology: {technology}")
                print(f"Production: {production} kWh")
                print("-" * 30)
        
            # Commit the transaction to save all entries
            conn.commit()
            print("Energy production data stored successfully.")
        else:
            print("No valid data found in the API response.")
    else:
        # Print error message if something goes wrong
        print(f"Error fetching data. Status code: {response.status_code}")

# Usage example
state_code = "CA"  # California
get_energy_production(state_code, NREL_API_KEY)

# Close the database connection
conn.close()
