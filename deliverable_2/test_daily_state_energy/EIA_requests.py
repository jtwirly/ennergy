import requests
import os
import pandas as pd

api_key = os.getenv("EIA_API_KEY")

def fetch_energy_data(start_time, end_time, fuel_type, grid_operator="NE", frequency="hourly"):
    url = f"https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/?frequency={frequency}&data[0]=value&facets[fueltype][]={fuel_type}&facets[respondent][]={grid_operator}&start={start_time}&end={end_time}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={api_key}"
    response = requests.get(url)
    data = response.json()

    # Check if 'response' and 'data' keys exist in the response
    if 'response' not in data or 'data' not in data['response']:
        print("No 'data' key in the response or it's in an unexpected structure.")
        return  # Early exit if there's no 'data' key

    # Extract the actual list of records
    records = data['response']['data']

    # Check if we have data to iterate over
    if not records:
        print(f"No records found for the given parameters.")
        return

    # List to store structured records for saving to CSV
    processed_records = []

    for item in records:

        if grid_operator is not None:
            if isinstance(grid_operator, str) and item['respondent'] != grid_operator:
                continue
            elif isinstance(grid_operator, list) and item['respondent'] not in grid_operator:
                continue
        
        # Define the record with key information extracted
        record = {
            'datetime': item['period'],
            'respondent_code': item['respondent'],
            'respondent_name': item['respondent-name'],
            'fuel_type': item['fueltype'],
            'type_name': item['type-name'],
            'value': float(item['value']),
            'units': item['value-units']
        }
        processed_records.append(record)

    # Check if records list is empty
    if not processed_records:
        print(f"No valid data found for specified grid operator(s): {grid_operator}")
        return

    # Convert to DataFrame
    df = pd.DataFrame(processed_records)

    # Convert 'datetime' column to datetime objects for sorting and filtering
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Sort by 'datetime' and 'fuel_type' for easier analysis
    df = df.sort_values(['datetime', 'fuel_type'])

    # Ensure the directory exists before saving the file
    output_directory = 'deliverable_2'
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)  # Create the directory if it doesn't exist

    # Define the file path
    file_path = os.path.join(output_directory, 'renewable_energy_Data.csv')

    # Save the DataFrame to CSV
    try:
        df.to_csv(file_path, index=False)
        print(f"Data successfully saved to {file_path}")
    except Exception as e:
        print(f"Error saving data: {e}")

fetch_energy_data("2023-10-25T00", "2024-11-01T00", 'WND')
